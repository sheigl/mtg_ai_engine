# Research: Full Rules Engine Parity (018)

## Current State Analysis

### _apply_spell_effect() (stack.py:248–289)
- **Current**: Only 3 patterns handled — `_DAMAGE_RE` (deal N damage), `_PUMP_RE` (get +N/+N), `_COUNTER_RE` (counter target spell)
- **Gap**: All other oracle text patterns no-op silently
- **Decision**: Extend with priority-ordered regex pattern list; unrecognized patterns log warning and no-op

### GameState Model (models/game.py:176–207)
- **Has**: `pending_cascade`, `mulligan_phase_active`, `pending_triggers`
- **Missing**: `pending_scry_choice`, `pending_surveil_choice`, `pending_tutor_choice`, `pending_discard_choice`, `pending_ward_payment`
- **Decision**: Add all as `Optional[dict] = None` fields to GameState using Pydantic v2

### StackObject Model (models/game.py:93–102)
- **Has**: `modes_chosen: list[int]`, `alternative_cost: str | None`, `mana_payment: dict`
- **Missing**: `x_value`, `kicker_paid`, `jump_start_discard_id`
- **Decision**: Extend StackObject with these fields (all optional with defaults)

### CastRequest Model (models/actions.py:30–38)
- **Has**: `card_id`, `targets`, `mana_payment`, `alternative_cost`, `modes_chosen`, `dry_run`, `from_command_zone`, `from_graveyard`
- **Missing**: `x_value: int`, `kicker_paid: bool`, `jump_start_discard_id: str | None`
- **Decision**: Extend CastRequest with these optional fields

### Permanent Model (models/game.py:70–90)
- **Has**: `counters: dict`, `summoning_sick`, `is_token`, `power_bonus`, `toughness_bonus`
- **Missing**: `unearthed: bool`, `time_counters: int`, `foretold: bool`
- **Decision**: Add as optional fields with defaults

### _compute_legal_actions (routers/game.py:1003–1469)
- **Lines 1056–1167**: Cast spells section builds valid_targets but does NOT filter hexproof/shroud/protection
- **Lines 1194–1249**: Alternative costs (convoke, delve, emerge) already handled
- **Lines 1251–1278**: Graveyard casting (flashback, escape, unearth, disturb) already partially handled
- **Missing**: X spell variant actions, kicker, foretell, suspend, jump-start additional cost, hexproof/shroud filter, protection filter
- **Decision**: Add filters and new cast action variants inline in existing cast section

### combat.py declare_blockers() (lines 111–161)
- **Has**: Flying/reach evasion checks, cannot-block constraints, goad checks
- **Missing**: Menace minimum-2-blocker enforcement
- **Decision**: Add post-validation check: if attacker has Menace and len(blockers_for_attacker) == 1, raise ValueError

### compute_block_declarations (heuristic_player.py:133–234)
- **Has**: Single-blocker best-of selection, 2-blocker gang block logic (already exists!)
- **Missing**: Menace detection — AI currently may assign exactly 1 blocker to Menace creatures
- **Decision**: Add Menace detection in the single-blocker section; skip single-blocker assignment for Menace creatures; force gang-block or 0 blockers

### game_loop.py priority handling (lines 346–459)
- The game loop always calls `ai_player.decide()` for the current priority player
- It does NOT filter by "is it my turn?" — it already calls AI for non-active priority
- **Key gap**: The heuristic player's `_score_action` returns 0.0 for `pass` normally, but only checks `chosen_fog_effect` and `trick_attackers` to deviate from pass
- For instant-speed spells during opponent's turn, the AI would still score them via `_score_cast()` — but this may not account for stack context
- **Decision**:
  1. In `_score_action`, when priority is non-active player turn, add stack context bonus to counterspells and removal
  2. Add pump-as-save scoring when a friendly creature faces lethal combat damage

### AIMemory.revealed_cards (models.py:10–66)
- **Has**: `revealed_cards: dict[str, list]` defined but never populated
- **Decision**: Populate in game_loop after each state update when opponent hand cards are visible

### _select_modes() (heuristic_player.py:1667–1700)
- **Has**: Full implementation; scores each mode and returns top N indices
- **Missing**: Not called anywhere — no call site in the cast flow
- **Decision**: Call `_select_modes()` in `decide()` / `_score_cast()` when modal spell is detected, include in CastRequest

## Design Decisions

### Pattern Matching for Spell Effects
- **Decision**: Add regex patterns in priority order in `_apply_spell_effect()`:
  1. Draw cards: `r"draw (\d+) cards?"`
  2. Destroy: `r"destroy target ([\w\s]+)"`
  3. Exile permanent: `r"exile target (permanent|creature|artifact|enchantment|land|planeswalker)"`
  4. Return to hand: `r"return target ([\w\s]+) to (its owner'?s?|your) hand"`
  5. Create tokens: `r"create (a|an|one|two|three|\d+) (\d+)/(\d+) ([\w\s]+) creature tokens?"`
  6. Gain life: `r"(you |target player )?gains? (\d+) life"`
  7. Discard: `r"(target player |each opponent )?discards? (\d+) cards?"`
  8. Tutor: `r"search your library for (a|an) ([\w\s]+)"`
  9. Counters: `r"put (\d+) \+1/\+1 counters? on target creature"`
  10. Scry: `r"scry (\d+)"`
  11. Surveil: `r"surveil (\d+)"`
  12. Damage already handled (existing)
  13. Pump already handled (existing)
  14. Counter already handled (existing)

### Tutor Implementation
- On resolution, set `pending_tutor_choice` with: `{player: str, filter_type: str, destination: "hand" | "battlefield"}`
- For heuristic AI: immediately resolve by scoring all library cards and selecting the highest-value one matching the filter; clear `pending_tutor_choice`
- For human/LLM: emit `choice` legal action

### Discard Implementation
- Heuristic AI: immediately discard lowest-CMC card(s) in hand; no pending state needed (AI is deterministic)
- Human/LLM player: set `pending_discard_choice` and emit `choice` legal action

### Token Creation
- Tokens need a stable ID: use `f"token_{uuid4().hex[:8]}"`
- Token `Card` object constructed from parsed oracle text (e.g. "1/1 white Soldier creature token" → power=1, toughness=1, type_line="Token Creature — Soldier")
- ETB triggers fire for each token individually

### X Spell Scaling
- For each X value offered, the cast action includes `x_value` in `mana_options`
- StackObject stores `x_value` from the cast request
- `_apply_spell_effect()` reads `x_value` from stack entry before pattern matching
- Damage, draw, life patterns check for "X" in oracle text and substitute `x_value`

### Cascade Procedure
- `GameState.pending_cascade` already exists — check its current structure in GameState model
- `resolve_top()` checks `"cascade"` in stack object's card keywords list and oracle text
- Library manipulation: pop from `gs.players[caster].library` top, accumulate exiled
- `cascade_choice` legal action: `action_type="cascade_choice"`, `cascade_card_id=found_card.id`

### Suspend / Foretell
- Suspend: new `action_type="suspend"` in legal actions; exiled card gets `time_counters=N` in its exile zone representation; upkeep trigger decrements counter; at 0, cast for free
- Foretell: new `action_type="foretell"` in legal actions; exiled face-down card tracked in `PlayerState.exile` with `foretold=True`; subsequent turns: offer `alternative_cost="foretell"` cast action

### Ward Enforcement
- Ward cost detected in oracle text: `r"Ward (\{[^}]+\}|\d+)"`
- When targeting spell is cast targeting a ward permanent: immediately set `pending_ward_payment`
- If ward cost not paid (or ability declined): spell is countered for that target
- Implementation: checked in `cast_spell()` after target validation

### Non-Active Priority AI
- The game loop already routes AI decisions at any priority — the gap is in scoring
- Add `_in_opponent_turn(game_state, my_name)` helper to detect non-active priority
- When in opponent's turn with a stack entry from opponent: boost counterspell score by `top_stack_cmc * 15`
- When in combat damage step with my creature being lethal-damaged: boost pump spell targeting it

### Protection from Color
- `get_spell_colors(card)`: extract letters from `{W}`, `{U}`, `{B}`, `{R}`, `{G}` in mana_cost
- `get_protection_colors(permanent)`: regex `r"protection from (\w+)"` on oracle_text; map color names to letters
- Applied in `_compute_legal_actions` target filtering, same location as hexproof/shroud

### Double-Faced Cards / Transform
- Condition checking in upkeep trigger handler in `resolve_top()` or dedicated upkeep step handler
- Werewolf condition: check `gs.spells_cast_last_turn` (new field needed on GameState) count
- Transform: swap `permanent.card` between `permanent.card.card_faces[0]` and `[1]`
- Modal DFCs: front face is castable from hand normally; back face offered as alternate cast from hand using `alternative_cost="modal_dfc_back"`

# Implementation Plan: Full Rules Engine Parity

**Branch**: `018-rules-engine-full-parity` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)

## Summary

Close all MTG rules engine gaps identified in the Forge analysis. The critical gap is that `_apply_spell_effect()` in `stack.py` only handles 3 effect patterns (damage, pump, counter) — all other spell effects silently no-op. This plan extends the effect resolver to cover 9 new patterns, enforces targeting rules (hexproof, shroud, menace, ward, protection), implements X spells, wires modal mode selection, completes the cascade trigger, adds keyword mechanics (kicker, jump-start, suspend, foretell, unearth), integrates scry/surveil blocking choices, and fixes AI gaps in non-active priority, menace blocking, and revealed card memory.

**Approach**: Python 3.11 + FastAPI + Pydantic v2 (all existing). No new dependencies. All changes are backwards-compatible (new fields have defaults). Priority order matches spec: spell effects → targeting → X spells → modal modes → cascade → keyword mechanics → scry/surveil → AI gaps.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pydantic v2, httpx, openai (all existing — no new deps)
**Storage**: In-memory GameState (Pydantic models); no persistence changes
**Testing**: pytest (all existing tests must pass; new unit tests added per feature group)
**Target Platform**: Linux server
**Project Type**: REST API service + AI client
**Performance Goals**: ≤15ms per `_compute_legal_actions` call; spell resolution ≤5ms
**Constraints**: No new pip dependencies; all 376 existing tests must pass
**Scale/Scope**: ~10 source files modified; ~8 new test modules

## Constitution Check

- No new architectural layers introduced — all changes extend existing patterns
- No new dependencies
- All new fields are optional with defaults (backwards-compatible)
- Regex pattern matching extends an existing function (`_apply_spell_effect`) rather than replacing it
- No gate violations

## Project Structure

### Documentation (this feature)

```text
specs/018-rules-engine-full-parity/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── api-changes.md   # Phase 1 output
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (files modified by this feature)

```text
mtg_engine/
├── models/
│   ├── game.py          # GameState, StackObject, Permanent, PlayerState — new fields
│   └── actions.py       # CastRequest, LegalAction — new fields
├── engine/
│   ├── stack.py         # _apply_spell_effect (9 new patterns), resolve_top (cascade, modal modes)
│   └── combat.py        # declare_blockers (menace enforcement)
└── api/
    └── routers/
        └── game.py      # _compute_legal_actions (hexproof/shroud/protection/menace/X spells/kicker/foretell/suspend)

ai_client/
├── heuristic_player.py  # compute_block_declarations (menace-aware), non-active priority scoring, _select_modes wiring
├── game_loop.py         # revealed_cards population, non-active priority check
└── models.py            # (no changes expected — AIMemory.revealed_cards already defined)

tests/
└── test_018_*.py        # New test modules (one per section)
```

---

## Phase 1: Spell Effect Resolution

### Target file: `mtg_engine/engine/stack.py`

**Function**: `_apply_spell_effect(gs, stack_obj, game_state_dict)` (lines 248–289)

**Implementation approach**: Replace the current 3-pattern if/elif chain with a priority-ordered pattern list. Each pattern is tried in sequence; first match wins. Unrecognized oracle text logs a warning at `DEBUG` level and returns unchanged state (no crash).

**Pattern order** (most specific first):
1. `r"draw (\d+|x) cards?"` → draw_cards effect
2. `r"destroy target ([\w\s]+)"` → destroy_permanent effect
3. `r"exile target ([\w ]+)"` → exile_permanent effect
4. `r"return target ([\w ]+) to (its owner'?s?|your) hand"` → bounce_permanent effect
5. `r"create (a|an|one|two|three|\d+) (\d+)/(\d+) ([\w ]+) creature tokens?"` → create_tokens effect
6. `r"(you |target player )?gain(?:s)? (\d+|x) life"` → gain_life effect
7. `r"(target player |each opponent )?discard(?:s)? (\d+|x) cards?"` → discard_cards effect
8. `r"search your library for (a|an) ([\w ]+)"` → tutor effect
9. `r"put (\d+|x) \+1/\+1 counters? on target creature"` → add_counters effect
10. `r"scry (\d+|x)"` → scry effect (sets `pending_scry_choice`)
11. `r"surveil (\d+|x)"` → surveil effect (sets `pending_surveil_choice`)
12. Existing damage pattern (unchanged)
13. Existing pump pattern (unchanged)
14. Existing counter pattern (unchanged)

**X value substitution**: Before pattern matching, read `stack_obj.x_value`. In all patterns, `(\d+|x)` captures either a literal number or the letter X; when X is captured, substitute `stack_obj.x_value`.

**Helper functions to add**:
- `_draw_cards(gs, player_name, n)` → moves n cards from library top to hand; if library empty, player loses (mark `gs.winner = opponent`)
- `_destroy_permanent(gs, perm_id)` → check indestructible; if not, move to graveyard, fire dies trigger
- `_exile_permanent(gs, perm_id)` → move to exile zone; no dies trigger
- `_bounce_permanent(gs, perm_id)` → remove from battlefield, add card to owner's hand
- `_create_tokens(gs, controller, count, power, toughness, subtypes, keywords)` → create Permanent with `is_token=True`, fire ETB triggers
- `_gain_life(gs, player_name, n)` → add n to player.life
- `_discard_cards(gs, player_name, n)` → heuristic: discard lowest-CMC cards; human: set `pending_discard_choice`
- `_tutor(gs, player_name, filter_type, destination)` → set `pending_tutor_choice`; heuristic AI resolves immediately by scoring library cards
- `_add_counters(gs, perm_id, counter_type, n)` → update `permanent.counters[counter_type]`
- `_apply_scry(gs, player_name, n)` → set `pending_scry_choice` with top n cards revealed
- `_apply_surveil(gs, player_name, n)` → set `pending_surveil_choice` with top n cards revealed

**Token card construction**: Parse "1/1 white Soldier creature token" → `Card(name="Soldier Token", type_line="Token Creature — Soldier", power=1, toughness=1, colors=["W"], mana_cost="")`. Token ID: `f"token_{uuid4().hex[:8]}"`.

**ETB trigger integration**: After creating a token or resolving a bounce that lands a creature on the battlefield, check `_check_etb_triggers(gs, new_perm)`. This function already exists — call it for each new token.

**Dies trigger integration**: Call existing `_apply_sba_zone_move(gs, perm, "graveyard")` for destroy effects — this fires dies triggers already in the SBA framework.

---

## Phase 2: Targeting Rule Enforcement

### Target files: `mtg_engine/api/routers/game.py`, `mtg_engine/engine/combat.py`

### 2a: Hexproof and Shroud — game.py `_compute_legal_actions`

In the spell casting section (lines 1126–1159 where `valid_targets` is built):

Add `_is_targetable(perm, targeting_player_name, spell_controller_name) -> bool`:
```python
def _is_targetable(perm, targeting_player, spell_controller):
    card = perm.get("card", {})
    keywords = [k.lower() for k in (card.get("keywords") or [])]
    oracle = (card.get("oracle_text") or "").lower()
    controller = perm.get("controller", "")

    # Shroud: no player can target
    if "shroud" in keywords or "shroud" in oracle:
        return False

    # Hexproof: opponent cannot target
    if "hexproof" in keywords or "hexproof" in oracle:
        if targeting_player != controller:
            return False

    return True
```

Apply this filter to every `valid_targets` list built for cast and activate actions.

### 2b: Protection from Color — game.py `_compute_legal_actions`

Add helpers:
```python
def _get_spell_colors(card: dict) -> set[str]:
    """Extract color letters from mana cost symbols."""
    cost = card.get("mana_cost") or ""
    mapping = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
    return {color for sym, color in mapping.items() if f"{{{sym}}}" in cost or f"{{{sym}/" in cost}

def _get_protection_colors(perm: dict) -> set[str]:
    """Parse 'protection from [color]' from oracle text."""
    oracle = (perm.get("card", {}).get("oracle_text") or "").lower()
    colors = {"white", "blue", "black", "red", "green"}
    protected = set()
    for color in colors:
        if f"protection from {color}" in oracle:
            protected.add(color)
    return protected
```

In target filtering: exclude permanent if any spell color matches any protection color.

### 2c: Menace Enforcement — combat.py `declare_blockers`

After existing blocker legality checks, before finalizing `combat_state.blocker_assignments`:

```python
# Menace enforcement: attacker with menace requires 2+ blockers
for attacker_id, blocker_list in combat_state.blocker_assignments.items():
    attacker_perm = _get_perm(gs.battlefield, attacker_id)
    if _has_keyword(attacker_perm, "menace") and len(blocker_list) == 1:
        raise ValueError(
            f"Menace creature {attacker_id} requires 2 or more blockers, got 1"
        )
```

### 2d: Ward Trigger — stack.py `cast_spell`

After target validation, before moving card to stack:

```python
for target_id in stack_obj.targets:
    target_perm = _find_perm(gs.battlefield, target_id)
    if target_perm and target_perm.controller != caster:
        ward_cost = _get_ward_cost(target_perm)
        if ward_cost:
            gs.pending_ward_payment = {
                "player": caster,
                "ward_cost": ward_cost,
                "targeting_spell_id": stack_obj.id
            }
```

Ward choice endpoint: when player submits choice with `choice_id="ward"` and pays cost, clear `pending_ward_payment`. If declined, remove the targeting spell from the stack (counter it).

---

## Phase 3: X Spells

### Target file: `mtg_engine/api/routers/game.py`

In the spell casting loop, after existing mana checks:

```python
if "{X}" in card.get("mana_cost", ""):
    colored_pips = _count_colored_pips(card["mana_cost"])
    generic_pips = _count_generic_pips(card["mana_cost"])
    available_mana = _total_available_mana(gs, player)
    max_x = min(10, available_mana - colored_pips - generic_pips)
    for x_val in range(1, max_x + 1):
        actions.append(LegalAction(
            action_type="cast",
            card_id=card["id"],
            card_name=card["name"],
            x_value=x_val,
            mana_options=[{"mana_cost": card["mana_cost"], "x_value": x_val}],
            description=f"cast {card['name']} (X={x_val})"
        ))
    continue  # Don't also add the base 0-cost cast
```

### Target file: `mtg_engine/models/actions.py`

Add `x_value: int = 0` and `kicker_paid: bool = False` to `CastRequest` and `LegalAction`.

### Target file: `mtg_engine/engine/stack.py`

In `cast_spell()`: store `request.x_value` onto `StackObject.x_value`.

In `_apply_spell_effect()`: read `stack_obj.x_value` and substitute for `X` in patterns.

### Target file: `ai_client/heuristic_player.py`

In `_score_noncreature_spell()`, detect X spells and score at `x_val * per_unit_value`. The `x_val` comes from `action.get("x_value", 0)`.

---

## Phase 4: Modal Spell Mode Wiring

### Target file: `mtg_engine/engine/stack.py`

In `_apply_spell_effect()`, at the start:

```python
modes_chosen = stack_obj.modes_chosen  # list[int], already on StackObject
if modes_chosen:
    oracle = stack_obj.source_card.oracle_text or ""
    mode_texts = re.split(r'•|\bMode \d+:|(?<=\.) ', oracle)
    mode_texts = [m.strip() for m in mode_texts if len(m.strip()) > 5]
    # Apply only chosen modes
    for mode_idx in modes_chosen:
        if mode_idx < len(mode_texts):
            _apply_single_effect_text(gs, stack_obj, mode_texts[mode_idx])
    return gs  # Done — do not fall through to full oracle text
# else: continue with existing full oracle text processing
```

### Target file: `ai_client/heuristic_player.py`

In `decide()` or the cast action submission path, before returning a `cast` action:

```python
if self._is_modal_spell(card):
    modes_chosen = self._select_modes(card, game_state, my_name)
    action["modes_chosen"] = modes_chosen
```

`_is_modal_spell(card)` checks for `"•"` or `"choose one"` / `"choose two"` in oracle text.

---

## Phase 5: Cascade Trigger

### Target file: `mtg_engine/engine/stack.py`, function `resolve_top()`

After resolving the spell's effect and before returning:

```python
card = stack_obj.source_card
if "cascade" in (card.keywords or []) or "cascade" in (card.oracle_text or "").lower():
    gs = _trigger_cascade(gs, stack_obj.controller, card.cmc)
```

**`_trigger_cascade(gs, caster_name, cascade_cmc)` implementation**:
1. Find `caster` in `gs.players`
2. Exile cards from top of library one at a time until finding a non-land card with `cmc < cascade_cmc`
3. Track exiled-and-not-chosen list
4. Set `gs.pending_cascade = {"caster": caster_name, "found_card": card_data, "exiled_cards": [...], "cascade_cmc": cascade_cmc}`
5. The cascade_choice endpoint already exists — it clears `pending_cascade` and either casts the card for free or exiles it, putting remaining cards on library bottom

---

## Phase 6: Keyword Mechanics

### Kicker — game.py `_compute_legal_actions`

Detect kicker cost: `r"[Kk]icker (\{[^}]+\})"` in oracle text.

Emit base cast action + kicker cast action when player can afford base + kicker cost.

In `stack.py cast_spell()`: store `request.kicker_paid` on StackObject.

In `_apply_spell_effect()`: check `stack_obj.kicker_paid`; if true, also apply kicker mode effect (parse `"If [this card] was kicked"` clause from oracle text).

### Jump-start — game.py `_compute_legal_actions` (graveyard cast section)

Existing graveyard cast section (lines 1251–1278) already handles `jump-start` as a keyword. But the cast request must include a discard target.

Add: when `jump-start` is detected, emit `from_graveyard=True` cast action with a `jump_start_discard_id` field listing the first available hand card as the discard target. The actual discard happens in `cast_spell()` when `request.jump_start_discard_id` is set.

### Suspend — game.py + step handling

New legal action type: `suspend` emitted in main phase when card with `"Suspend N"` is in hand.

Handler in game.py: accept `SpecialActionRequest(action_type="suspend", card_id=...)`:
1. Remove card from hand
2. Add to `PlayerState.suspended_cards` with `time_counters=N`
3. Deduct suspend cost from mana pool

Upkeep trigger: In the beginning-of-turn / upkeep step handler, check each player's `suspended_cards`. Decrement `time_counters`. When `time_counters == 0`, cast the card for free (add to stack as if player cast it with no mana cost).

### Foretell — game.py + cast section

New legal action type: `foretell` emitted in main phase (any turn, pay {2}).

Handler: Remove card from hand, add to `PlayerState.foretold_cards` with `foretold=True`.

On subsequent turns: emit alternate cast action with `alternative_cost="foretell"` and the discounted foretell cost, `from_graveyard=False` (it's from exile).

### Unearth — game.py (graveyard cast section, already partial)

The graveyard cast section (lines 1251–1278) already checks for `"unearth"`. Extend:
- After successful unearth cast, set `permanent.unearthed = True`
- In end-of-turn cleanup SBA check: exile all permanents with `unearthed=True`

---

## Phase 7: Scry/Surveil Engine Integration

### Target file: `mtg_engine/engine/stack.py`

In `_apply_spell_effect()`, the scry/surveil patterns (items 10, 11 in the pattern list) call:
- `_apply_scry(gs, player_name, n)` → reveal top n cards, set `gs.pending_scry_choice = {"player": ..., "cards": [...], "n": n}`
- `_apply_surveil(gs, player_name, n)` → same but `gs.pending_surveil_choice`

### Target file: `mtg_engine/api/routers/game.py`

In `_compute_legal_actions()`, early-exit check:

```python
if gs.pending_scry_choice and gs.pending_scry_choice["player"] == priority_player:
    # Emit choice actions for each arrangement and return early
    ...
if gs.pending_surveil_choice and gs.pending_surveil_choice["player"] == priority_player:
    ...
```

### Target file: `ai_client/heuristic_player.py`

`_score_scry_choice()` and `_score_surveil_choice()` already implemented. These are called when `action_type == "choice"` and `choice_id` contains `"scry"` or `"surveil"`. No changes needed — the engine side just needs to emit these choices.

---

## Phase 8: Protection from Color Targeting

### Target file: `mtg_engine/api/routers/game.py`

Add `_get_spell_colors()` and `_get_protection_colors()` helpers (see Phase 2 design).

In target filtering: in the same location as hexproof/shroud filter, also filter protection.

---

## Phase 9: Double-Faced Cards / Transform

### Target file: `mtg_engine/models/game.py`

GameState: add `spells_cast_this_turn: int = 0`, `spells_cast_last_turn: int = 0`.

In `cast_spell()`: increment `gs.spells_cast_this_turn`.

In new-turn handler: `gs.spells_cast_last_turn = gs.spells_cast_this_turn; gs.spells_cast_this_turn = 0`.

### Transform trigger — stack.py or upkeep handler

In upkeep step handler, for each transform permanent on the battlefield:
- Check `card.layout == "transform"` and `card.card_faces` has 2 entries
- Evaluate transform condition (werewolf: compare `gs.spells_cast_last_turn`)
- If condition met: swap `permanent.card` with front/back face data

### Modal DFC back-face casting — game.py `_compute_legal_actions`

For cards in hand with `layout == "modal_dfc"` and `card_faces` length 2:
- Emit both a front-face cast action (existing behavior) AND a back-face cast action
- Back-face action: `alternative_cost="modal_dfc_back"`, uses back face mana cost

---

## Phase 10: AI Gaps

### 10a: Non-Active Priority Scoring

**Target**: `ai_client/heuristic_player.py`, `_score_action()` method

Add `_is_opponent_turn(game_state, my_name) -> bool`:
```python
return game_state.get("active_player") != my_name
```

When scoring `cast` during opponent's turn with a non-empty stack:
- If spell is a counterspell AND top stack entry belongs to opponent: apply multiplier based on opponent spell CMC
- If spell is a pump AND a friendly creature is in `combat_state.blocker_assignments` facing lethal: add `saved_creature_cmc * 12` bonus

### 10b: Menace-Aware AI Blocking

**Target**: `ai_client/heuristic_player.py`, `compute_block_declarations()`

In the single-blocker selection loop:
```python
if _card_has_kw(att_card, "menace"):
    # Skip single-blocker assignment; handle in gang-block section
    single_blocked.discard(att_id)
    continue
```

In the gang-block section: when attacker has Menace, force gang-block evaluation regardless of value threshold — because a single-blocker response would be illegal. If no 2-blocker combo is available, assign 0 blockers.

### 10c: Revealed Card Memory

**Target**: `ai_client/game_loop.py`

After receiving each game state update, scan opponent's hand in the state:
```python
opponent = next((p for p in state["players"] if p["name"] != my_name), None)
if opponent and opponent.get("hand"):
    visible_cards = [c for c in opponent["hand"] if c.get("id")]  # visible = non-null
    if visible_cards:
        memory.revealed_cards[opponent["name"]] = visible_cards
```

The AI scoring already reads `memory.revealed_cards` (confirmed by models.py definition) — no scoring changes needed.

---

## Test Plan

Each phase gets a dedicated test module:

| Module | Coverage |
|--------|----------|
| `tests/test_018_spell_effects.py` | draw, destroy, exile, bounce, tokens, life, tutor, discard, counters |
| `tests/test_018_targeting.py` | hexproof, shroud, menace engine validation, ward |
| `tests/test_018_x_spells.py` | X spell legal action generation, X resolution |
| `tests/test_018_modal_modes.py` | Mode parsing, single-mode application |
| `tests/test_018_cascade.py` | Cascade trigger, pending_cascade, cascade_choice |
| `tests/test_018_keywords.py` | Kicker, jump-start, suspend, foretell, unearth |
| `tests/test_018_scry_surveil.py` | Scry/surveil pending choice creation, AI choice scoring |
| `tests/test_018_protection.py` | Protection from color targeting filter |
| `tests/test_018_ai_gaps.py` | Non-active priority, menace blocking, revealed cards |

All tests use the existing `create_game()` fixture pattern from prior test modules.

# Tasks: Rules Engine Gap Closure (019)

## Status key
[ ] todo  [x] done  [~] in progress  [!] blocked  [s] skipped

---

## Phase 1 — Trigger System Extensions (US1, US2)

- [ ] TASK-019-001: Extend triggers.py with cast trigger detection
  - Add `CAST_TRIGGER_PATTERNS` constant with regex patterns for "whenever you cast" and "whenever a player casts" triggers
  - Implement `check_cast_triggers(game_state, caster, spell_type_line, spell_name)` function
  - Function should iterate all permanents and emblems looking for trigger patterns
  - Integration point: call from `cast_spell()` in stack.py after placing spell on stack

- [ ] TASK-019-002: Extend triggers.py with attack trigger detection
  - Add `ATTACK_TRIGGER_PATTERNS` constant with regex patterns for attack triggers
  - Implement `check_attack_triggers(game_state, attacker_ids)` function
  - Function should iterate permanents for "whenever [creature] attacks" patterns
  - Integration point: call from `declare_attackers()` in combat.py after validation

- [ ] TASK-019-003: Extend triggers.py with block trigger detection
  - Add `BLOCK_TRIGGER_PATTERNS` constant with regex patterns for block triggers
  - Implement `check_block_triggers(game_state, blocker_ids)` function
  - Function should iterate permanents for "whenever [creature] blocks" patterns
  - Integration point: call from `declare_blockers()` in combat.py after validation

- [ ] TASK-019-004: Implement exalted and battle cry triggers in attack triggers
  - In `check_attack_triggers()`, detect when only one attacker exists
  - For exalted: find all permanents with "exalted" keyword owned by that controller
  - For battle cry: for each battle-cry attacker, add trigger for other attacking creatures
  - Add pending triggers for both effects

---

## Phase 2 — Two-Step Combat Damage (US3)

- [ ] TASK-019-005: Modify combat.py to support two-step damage resolution
  - Add `first_strike_only` parameter to `assign_combat_damage()` function
  - When `first_strike_only=True`: only creatures with first strike or double strike deal damage
  - When `first_strike_only=False`: only creatures WITHOUT first-strike-only deal damage
  - Update `turn_manager.py` to handle step transitions for first-strike damage

- [ ] TASK-019-006: Implement first-strike damage step in turn manager
  - Add `FIRST_STRIKE_DAMAGE` step to step transitions
  - Call `assign_combat_damage(gs, first_strike_only=True)` during first-strike step
  - Run SBAs after first-strike damage resolution
  - Grant priority to active player

- [ ] TASK-019-007: Implement regular combat damage step in turn manager
  - Add `COMBAT_DAMAGE` step to step transitions
  - Call `assign_combat_damage(gs, first_strike_only=False)` during combat damage step
  - Run SBAs after regular damage resolution
  - Grant priority to active player

- [ ] TASK-019-008: Update combat declaration to handle step transitions
  - In `declare_attackers()`, check if `has_first_strike_combatants()` is true
  - If true, transition to `FIRST_STRIKE_DAMAGE` step instead of `COMBAT_DAMAGE`
  - If false, skip to `COMBAT_DAMAGE` step

---

## Phase 3 — Keyword Mana Cost Modifiers (US4)

- [ ] TASK-019-009: Add new fields to CastRequest model in actions.py
  - Add `convoke_creature_ids: list[str] = []`
  - Add `delve_card_ids: list[str] = []`
  - Add `improvise_artifact_ids: list[str] = []`
  - Add `emerge_sacrifice_id: str | None = None`

- [ ] TASK-019-010: Implement keyword cost reduction in mana.py
  - Add `apply_keyword_cost_reductions(base_cost, cast_request, game_state, player_name)` function
  - Implement Convoke logic: tap creatures to reduce cost
  - Implement Delve logic: exile graveyard cards to reduce generic cost
  - Implement Improvise logic: tap artifacts to reduce generic cost
  - Implement Affinity logic: reduce cost based on battlefield permanents
  - Implement Emerge logic: sacrifice creature to reduce cost by CMC

- [ ] TASK-019-011: Update API cast endpoint to use keyword cost reductions
  - Call `apply_keyword_cost_reductions()` before `can_pay_cost()` check
  - Pass required fields from CastRequest to the cost reduction function

---

## Phase 4 — Persist and Undying (US5)

- [ ] TASK-019-012: Intercept zone transitions in zones.py for persist/undying
  - Modify `move_permanent_to_zone()` function to intercept when `to_zone == "graveyard"` and permanent is a creature
  - Check persist condition: `"persist" in perm.keywords` AND `perm.counters.get("-1/-1", 0) == 0`
  - Check undying condition: `"undying" in perm.keywords` AND `perm.counters.get("+1/+1", 0) == 0`
  - Return to battlefield with appropriate counter instead of going to graveyard
  - Add pending choice for player selection if both apply

---

## Phase 5 — Storm (US6)

- [ ] TASK-019-013: Implement storm copy creation in stack.py
  - In `resolve_top()` function, before applying spell's effect
  - Check if spell has "storm" in card keywords
  - Calculate storm count from `game_state.spells_cast_this_turn - 1`
  - Create that many copies of the spell on the stack using `copy_spell_on_stack()`

- [ ] TASK-019-014: Ensure storm copies don't go to graveyard
  - Modify stack resolution logic to prevent storm copies from going to graveyard
  - Copies should cease to exist when they leave the stack (not go to graveyard)

---

## Phase 6 — Buyback and Replicate (US7)

- [ ] TASK-019-015: Add buyback and replicate fields to StackObject in game.py
  - Add `buyback_paid: bool = False`
  - Add `replicate_count: int = 0`

- [ ] TASK-019-016: Implement buyback logic in stack.py
  - Detect buyback via oracle_text regex in `cast_spell()`
  - Add `buyback_paid` to `StackObject` when detected
  - In `resolve_top()`, if `stack_obj.buyback_paid`, return card to hand instead of graveyard

- [ ] TASK-019-017: Implement replicate logic in stack.py
  - Detect replicate via oracle_text regex in `cast_spell()`
  - Add `replicate_count` to `StackObject` when detected
  - In `resolve_top()`, call `copy_spell_on_stack()` N times before resolving the original

---

## Phase 7 — Flashback and Escape (US8)

- [ ] TASK-019-018: Add flashback and escape fields to StackObject in game.py
  - Add `flashback: bool = False`
  - Add `escape: bool = False`

- [ ] TASK-019-019: Implement legal action generation for flashback/escape
  - In `_compute_legal_actions()` in stack.py, scan `player.graveyard` for flashback/escape patterns
  - Generate `cast_flashback` / `cast_escape` `LegalAction` entries

- [ ] TASK-019-020: Implement flashback/escape resolution logic
  - In `resolve_top()`, if `stack_obj.flashback or stack_obj.escape`, exile the card instead of sending to graveyard
  - Add card removal from graveyard when casting from graveyard

---

## Phase 8 — Cycling (US9)

- [ ] TASK-019-021: Add cycling action type to LegalAction in actions.py
  - Add `"cycle"` action type for cards with `Cycling {cost}` in oracle_text

- [ ] TASK-019-022: Implement cycling endpoint in API
  - Add `POST /game/{game_id}/cycle` endpoint
  - Implement logic to pay cycling cost, discard card, draw card

- [ ] TASK-019-023: Implement cycling trigger emission
  - After cycling, call `check_cycle_triggers(game_state, card_name, type_line)`
  - For "whenever you cycle" patterns

---

## Phase 9 — Dredge (US10)

- [ ] TASK-019-024: Implement draw hook for dredge in stack.py
  - In `draw_card()` function, check if player has dredge-able cards in graveyard
  - Present `LegalAction(action_type="dredge", ...)` before completing the draw

- [ ] TASK-019-025: Add dredge endpoint to API
  - Add `POST /game/{game_id}/dredge` endpoint
  - Implement logic to choose dredge card or pass to draw normally

---

## Phase 10 — Suspend Auto-Cast (US11)

- [ ] TASK-019-026: Implement suspend auto-cast in turn_manager.py
  - When suspended card reaches 0 time counters in upkeep handler
  - Call `cast_spell()` with empty `mana_payment` instead of moving card to hand
  - Mark the StackObject with `metadata["grant_haste"] = True` if the card is a creature

- [ ] TASK-019-027: Implement haste grant for suspended creatures
  - In `put_permanent_onto_battlefield()`, check for `grant_haste` flag
  - Add `"haste"` to keywords + schedule cleanup at end of turn

---

## Phase 11 — Command Tax (US12)

- [ ] TASK-019-028: Add utility function for cost modification in mana.py
  - Add `add_generic_to_cost(cost, amount) -> dict[str, int]` function

- [ ] TASK-019-029: Implement command tax in API cast endpoint
  - When `req.from_command_zone`, compute `tax = 2 * player.commander_cast_count`
  - Add to effective cost via `add_generic_to_cost()`
  - Validate payment, then increment `commander_cast_count` after successful cast

---

## Phase 12 — Proliferate (US13)

- [ ] TASK-019-030: Implement proliferate spell effect pattern in stack.py
  - In `_apply_spell_effect()`, detect `r"\bproliferate\b"`
  - Set pending proliferate choice

- [ ] TASK-019-031: Add proliferate endpoint to API
  - Add `POST /game/{game_id}/proliferate` endpoint
  - Implement logic to submit target list and add counters

---

## Phase 13 — Sagas (US14)

- [ ] TASK-019-032: Implement saga ETB logic in zones.py
  - In `put_permanent_onto_battlefield()`, detect Saga type
  - Set `counters["lore"] = 1`
  - Trigger chapter I

- [ ] TASK-019-033: Implement saga upkeep logic in turn_manager.py
  - Add saga upkeep counter increment
  - Trigger matching chapter abilities

- [ ] TASK-019-034: Implement saga sacrifice logic
  - After final chapter triggers and resolves, sacrifice the saga
  - Implement via delayed trigger or SBA check

---

## Phase 14 — World Enchantment SBA (US15)

- [ ] TASK-019-035: Add world enchantment SBA in sba.py
  - In `_check_once()`, find all permanents with "world" in type_line
  - If 2+ exist, keep the newest (by `entered_at` or `entered_turn`)
  - Move others to their owners' graveyards

---

## Phase 15 — Unearth SBA (US16)

- [ ] TASK-019-036: Implement unearth SBA in sba.py
  - In `_check_once()`, when `current_step == Step.END`, exile all `perm.unearthed == True` permanents

- [ ] TASK-019-037: Implement unearth replacement effect in zones.py
  - In `move_permanent_to_zone()`, if `perm.unearthed and to_zone != "exile"`, redirect `to_zone = "exile"`

- [ ] TASK-019-038: Implement unearth clear on bounce in zones.py
  - When `to_zone == "hand"` for an unearthed permanent (bounced), clear `unearthed = False`

---

## Phase 16 — Planeswalker Rules (US17)

- [ ] TASK-019-039: Add emblem model to game.py
  - Create `Emblem` class with `id`, `controller`, `source_name`, `abilities`

- [ ] TASK-019-040: Add emblems to GameState in game.py
  - Add `emblems: list[Emblem] = []` to GameState model

- [ ] TASK-019-041: Implement loyalty limit enforcement in turn_manager.py
  - In `_compute_legal_actions()`, filter out `activate_loyalty` for permanents with `loyalty_activated_this_turn == True`
  - Reset flag during untap step

- [ ] TASK-019-042: Add emblem trigger support in triggers.py
  - Iterate `game_state.emblems` in trigger detection functions
  - Support triggers from emblems alongside permanents

- [ ] TASK-019-043: Implement damage redirect in replacement.py
  - Add `redirect_to_planeswalker_id: str | None` to damage events
  - Allow routing in `apply_damage_event()`

---

## Phase 17 — Partner Commanders (US19)

- [ ] TASK-019-044: Update commander cast count in game.py
  - Change `PlayerState.commander_cast_count: int` to `commander_cast_counts: dict[str, int]` keyed by card name

- [ ] TASK-019-045: Implement partner commander validation in API
  - Add validation at game creation for partner commander combinations
  - Allow 2 commanders if both have Partner or matching "Partner with [Name]"

---

## Phase 18 — Multiplayer "Each Opponent" (US20)

- [ ] TASK-019-046: Add opponent utility function in stack.py
  - Implement `get_opponents(game_state, player_name) -> list[PlayerState]`

- [ ] TASK-019-047: Implement each opponent logic in stack.py
  - Replace single-opponent application with iteration over `get_opponents()` for "each opponent" patterns

- [ ] TASK-019-048: Add opponent target to CastRequest in actions.py
  - Add `opponent_target: str | None = None` for 3+ player "target opponent" disambiguation

---

## Testing and Validation

- [ ] TASK-019-049: Create test suite for each user story
  - Create `tests/test_019/` directory with dedicated test files
  - Implement tests following existing patterns
  - Ensure all 421 existing tests continue to pass (zero regressions)

- [ ] TASK-019-050: Implement comprehensive regression testing
  - Run full test suite after each phase
  - Verify no existing functionality is broken
  - Validate all new features work as specified

- [ ] TASK-019-051: Create integration tests for complex interactions
  - Test combinations of multiple features (e.g., storm + buyback)
  - Test edge cases and error conditions
  - Validate proper state transitions and game flow
# Research: Rules Engine Gap Closure (Feature 019)

**Feature**: 019-rules-engine-gap-closure
**Date**: 2026-03-29

---

## 1. Trigger System Extension

**Decision**: Extend `_on_zone_change()` and add new event hooks in `cast_spell()` and `declare_attackers()` / `declare_blockers()`.

**Rationale**: The existing trigger system already handles zone-change, phase-change, and combat-damage trigger patterns. Spell cast triggers and attack/block triggers follow the same `PendingTrigger` pattern — they just need new event sources and new `_matches_*` pattern functions.

**Key finding**: `_on_zone_change()` in `triggers.py` iterates all permanents and checks `TriggeredAbility` instances via `_matches_zone_change()`. A new `check_cast_triggers(game_state, spell_name, spell_type)` function following the same pattern will handle "whenever you cast a spell" detection. Similarly, `check_attack_triggers(game_state, attacker_ids)` handles attack triggers.

**Pattern to match for cast triggers**:
- `r"whenever you cast"` — controller-only filter
- `r"whenever a player casts"` — all players
- `r"whenever (?:an? )?(?:instant|sorcery|creature|spell)"` — typed spell triggers

**Pattern to match for attack triggers**:
- `r"whenever (?:this creature|[a-z\s]+ creature) attacks"` — creature attacks
- `r"whenever (?:a creature|creatures) you control attack"` — group attack

**Alternatives considered**: Creating a universal event bus. Rejected as over-engineering — the existing pattern-per-event approach is simpler and consistent with the existing code style.

---

## 2. Two-Step Combat Damage

**Decision**: Split combat damage into two passes driven by `has_first_strike_combatants()`. The turn_manager advances from `DECLARE_BLOCKERS` step through `FIRST_STRIKE_DAMAGE` step (existing enum value in `Step`) then `COMBAT_DAMAGE` step.

**Key finding**:
- `Step.FIRST_STRIKE_DAMAGE` and `Step.COMBAT_DAMAGE` already exist as separate steps in the turn sequence enum.
- `has_first_strike_combatants()` already correctly returns True when any attacker/blocker has first strike or double strike.
- `assign_combat_damage()` already accepts damage assignments — it just needs to be called twice, with filtering: first-strike pass only for creatures with first-strike/double-strike, second pass for all creatures that haven't resolved (first-strikers without double-strike skip the second pass).

**Parameter addition needed**: `assign_combat_damage(game_state, assignments, first_strike_only=False)` — the `first_strike_only` flag filters which creatures deal damage in that call.

**Alternatives considered**: A completely separate damage-assignment function for first strike. Rejected — the existing function covers all the logic; a boolean parameter is sufficient.

---

## 3. Keyword Mana Cost Modifiers

**Decision**: Add new fields to `CastRequest` for Convoke, Delve, Improvise, and Emerge; Affinity is auto-calculated from battlefield state.

**Key finding**: `CastRequest` already has `alternative_cost: str | None`. The API router already handles `"convoke"` and `"emerge"` as alternative cost types (lines 438-455 of game.py router). What's missing is the actual cost reduction math and the new request fields for specifying which creatures/cards/artifacts are being used.

**New CastRequest fields needed**:
- `convoke_creature_ids: list[str]` — creatures to tap for convoke
- `delve_card_ids: list[str]` — graveyard cards to exile for delve
- `improvise_artifact_ids: list[str]` — artifacts to tap for improvise
- `emerge_sacrifice_id: str | None` — creature to sacrifice for emerge

**Affinity calculation**: Count permanents of the relevant type on the player's battlefield at cast time; auto-reduce cost (no new field needed).

**Cost reduction math**: All these keywords reduce generic mana (`{N}` portion of cost). Each resource reduces generic cost by 1. Cannot reduce below 0.

**Alternatives considered**: Encoding all alternative payment in `mana_payment` dict. Rejected — semantic clarity is important; separate fields make the intent explicit and allow validation.

---

## 4. Persist and Undying as Replacement Effects

**Decision**: Implement as replacement effects registered on the `ReplacementEffect` list during ETB, checked in `_check_once()` in sba.py before sending to graveyard.

**Key finding**: The `process_event()` function in `replacement.py` handles `GameEvent(event_type="zone_change", from_zone="battlefield", to_zone="graveyard")`. Persist and Undying can be implemented as a pre-death check: when a creature would be destroyed/die, check for persist/undying keyword and counter conditions before completing the zone change.

**Implementation approach**: Rather than a formal `ReplacementEffect` registration (which requires persistent state), implement directly in `_check_once()` of `sba.py` and in `move_permanent_to_zone()` of `zones.py` by intercepting the battlefield→graveyard transition for creatures with persist/undying.

**Counter check logic**:
- Persist: check `perm.counters.get("-1/-1", 0) == 0`
- Undying: check `perm.counters.get("+1/+1", 0) == 0`

**Alternatives considered**: Full replacement effect registration at ETB. Rejected as more complex — direct interception in the zone-change function is simpler and less error-prone.

---

## 5. Storm Implementation

**Decision**: On storm spell resolution, read `game_state.spells_cast_this_turn` (already tracked on `GameState`) and use `copy_spell_on_stack()` to create N copies.

**Key finding**: `GameState.spells_cast_this_turn: int = 0` already exists and is reset each turn. It just needs to be incremented in `cast_spell()`. On resolution in `resolve_top()`, check if the resolving spell has the "storm" keyword; if so, call `copy_spell_on_stack()` `spells_cast_this_turn - 1` times (subtract 1 because the storm spell itself was already counted when cast).

**Copies must**: Not go to graveyard (existing behavior for `copy_spell_on_stack()` — copies already have `is_copy=True` which skips graveyard in `resolve_top()`).

**Alternatives considered**: Tracking storm count separately from `spells_cast_this_turn`. Rejected — they are the same value; no need for duplication.

---

## 6. Buyback and Replicate

**Decision**: Buyback adds `buyback_paid: bool` to `CastRequest`; Replicate adds `replicate_count: int`. Both detected via regex on oracle_text.

**Buyback oracle_text pattern**: `r"Buyback\s+(\{[^}]+\}(?:\{[^}]+\})*)"` — captures the buyback cost.

**Buyback resolution**: In `resolve_top()`, if `stack_obj.buyback_paid` is True, move to hand instead of graveyard.

**Replicate oracle_text pattern**: `r"Replicate\s+(\{[^}]+\}(?:\{[^}]+\})*)"` — captures the replicate cost.

**Replicate resolution**: In `resolve_top()`, before the spell resolves, create N copies where N = `stack_obj.replicate_count`. Copies use `copy_spell_on_stack()`.

---

## 7. Flashback and Escape Auto-Detection

**Decision**: Auto-detect in `_compute_legal_actions()` by scanning graveyard cards for flashback/escape patterns; add `cast_flashback` and `cast_escape` action types.

**Key finding**: `CastRequest.from_graveyard: bool` already exists but is not auto-detected. The `_compute_legal_actions()` function in `stack.py` needs to scan the player's graveyard for cards with Flashback or Escape in oracle_text and generate legal cast actions for them.

**Flashback detection pattern**: `r"Flashback\s+(\{[^}]+\}(?:\{[^}]+\})*)"` — cost override for casting.

**Escape detection pattern**: `r"Escape—\s*(\{[^}]+\}(?:\{[^}]+\})*),\s*Exile\s+(\d+)\s+other"` — cost + exile count.

**Resolution**: In `resolve_top()`, if `stack_obj.from_graveyard and stack_obj.alternative_cost in ("flashback", "escape")`, exile the card instead of sending to graveyard.

---

## 8. Cycling Implementation

**Decision**: Add Cycling as an `ActivatedAbility` on cards; action type `"cycle"` in `_compute_legal_actions()`.

**Cycling detection pattern**: `r"Cycling\s+(\{[^}]+\})"` in oracle_text.

**Action flow**: Player pays cycling cost → card is discarded to graveyard → player draws one card → `CyclingEvent` is emitted → triggers for "whenever you cycle" fire.

**New action type**: `"cycle"` with `card_id` and `mana_payment` fields. The cycle action is valid at instant speed from hand.

---

## 9. Dredge Implementation

**Decision**: Implement as a pending choice presented when a player would draw. A new `PendingChoice(choice_type="dredge")` is added to player state when dredge-able cards are in the graveyard.

**Key finding**: The existing pending choice system (used for scry, surveil) can be extended. When `draw_card()` is called, first check if any cards in the player's graveyard have the Dredge keyword. If so, add a `pending_dredge_choice` to the player that the player resolves before the draw completes.

**Dredge detection pattern**: `r"Dredge\s+(\d+)"` in oracle_text → N cards to mill.

**Alternative**: Auto-dredge if only one dredge card available. Rejected — dredge is always optional; player must choose.

---

## 10. Suspend Auto-Cast

**Decision**: In `turn_manager.py` upkeep handler, when a suspended card's time counter reaches 0, call `cast_spell()` with `mana_payment={}` (free cast) instead of adding to hand.

**Key finding**: The upkeep handler at lines 70-82 of `turn_manager.py` already moves the card to hand when time counters reach 0. This needs to instead call `cast_spell()` directly. The `haste` keyword must then be injected onto the resulting permanent's ETB (add to `entering_keywords` or handle in `put_permanent_onto_battlefield()`).

**Haste granting**: Add a temporary haste effect via `delayed_trigger` that expires at end of turn, or set `haste=True` on the Permanent during the ETB. The simplest approach: after `cast_spell()`, check if the top of stack is the suspended card, then add `"haste_until_eot"` to the StackObject's metadata so `put_permanent_onto_battlefield()` can include haste in the permanent's keyword list.

---

## 11. Command Tax

**Decision**: In the `cast` API endpoint (game.py router), when `from_command_zone=True`, add `2 * player.commander_cast_count` to the effective cost before calling `can_pay_cost()`.

**Key finding**: `PlayerState.commander_cast_count: int = 0` already exists. The `from_command_zone: bool` field already exists on `CastRequest`. The cost calculation in the router just needs to read `player.commander_cast_count` and add `{"generic": 2 * commander_cast_count}` to the required mana.

---

## 12. Proliferate

**Decision**: Add a new `ProliferateRequest` and `POST /game/{id}/proliferate` endpoint (or handle as a spell effect pattern in `_apply_spell_effect()`).

**Implementation approach**: Proliferate is best handled as a spell effect pattern. When `_apply_spell_effect()` encounters "proliferate" in oracle_text, it collects all permanents and players with at least one counter and presents a `PendingChoice(choice_type="proliferate_targets")` for the player to select targets.

---

## 13. Sagas

**Decision**: Detect Saga type at ETB, add one lore counter immediately and trigger chapter I; add upkeep trigger for lore counter increment; sacrifice when final chapter triggers.

**Saga detection**: `"Saga"` in `perm.card.type_line`.

**Chapter text parsing**: Oracle text follows pattern `"I — effect. II — effect. III — effect."` — split on roman numeral patterns to get chapter abilities.

**Lore counter tracking**: Use existing `perm.counters["lore"]` — the generic counter dict already supports this.

---

## 14. World Enchantment SBA

**Decision**: Add to `_check_once()` in `sba.py` — check for permanents with `"World"` in their type_line; if 2+ exist, keep the one with the highest `entered_turn` / `entered_at` timestamp.

**Timestamp tracking**: `Permanent.entered_turn: int` and `Permanent.entered_at: datetime` should be used. If `entered_at` is not on the model, `Permanent.tapped_at` pattern can be followed to add `entered_at: datetime | None`.

---

## 15. Unearth SBA

**Decision**: Add to `_check_once()` — check for permanents with `unearthed=True` during end step only, and add a replacement effect for unearthed creatures leaving the battlefield for non-exile reasons.

**Key finding**: `Permanent.unearthed: bool = False` already exists. The SBA just needs to fire during `Step.END` — add a phase gate check `if game_state.current_step == Step.END` inside the unearthed SBA.

---

## 16. Planeswalker Rules

**Decision (loyalty limit)**: Check `perm.loyalty_activated_this_turn` in `_compute_legal_actions()` before generating `activate_loyalty` actions. Reset flag during upkeep step.

**Key finding**: `Permanent.loyalty_activated_this_turn: bool = False` already exists. Only need to: (1) check it in `_compute_legal_actions()` and (2) reset it in the untap/upkeep step of `turn_manager.py`.

**Decision (damage redirect)**: Add `redirect_to_planeswalker_id: str | None` field to `DamageRequest`. When set, route damage to that planeswalker instead of the player.

**Decision (emblems)**: Add `Emblem` model to `models/game.py` and `emblems: list[Emblem]` to `GameState`. Emblem abilities are handled the same way as permanent triggered/static abilities by iterating emblems in trigger-checking loops.

---

## 17. Exalted and Battle Cry

**Decision**: Implement within the new `check_attack_triggers()` function. Exalted and Battle Cry are special-cased because they depend on the count of attackers.

**Exalted**: After `declare_attackers()`, if `len(attack_declarations) == 1`, find all permanents with "exalted" keyword on the attacker's controller's side and add one pending trigger per exalted instance.

**Battle Cry**: After `declare_attackers()`, for each attacker that has "battle cry", add a pending trigger that grants +1/+0 to all other attackers.

---

## 18. Partner Commanders

**Decision**: Validate at game creation (in the `POST /game` endpoint). If both commanders in `player.command_zone` have Partner, allow both. Validate "Partner with [Name]" against the other commander's name.

**Key finding**: `PlayerState.command_zone: list[Card]` supports multiple cards. The validation is purely at game-start.

---

## 19. Multiplayer "Each Opponent"

**Decision**: In `_apply_spell_effect()`, detect "each opponent" pattern and iterate all players except the controller. For "target opponent" in 3+ player games, add `opponent_target: str | None` to request models.

**Key finding**: `game_state.players` is a list — iterating all non-controller players is trivial. The current single-opponent pattern needs to be replaced with a loop.

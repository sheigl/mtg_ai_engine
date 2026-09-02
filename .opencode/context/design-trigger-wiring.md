# Design: Wire 13 Dead-Code Trigger Check Functions into Engine Event Flow

## Overview
Wire 13 existing pure-transform trigger check functions from `mtg_engine/engine/triggers.py` into the engine's event flow so they fire at the correct game moments. All 13 functions already exist with proper regex patterns, controller filtering, and self-referential guards -- they just need to be called from the right places.

## User Story Reference
TRG-20/TRG-B1: Wire all dead-code trigger check functions (Sacrifice, Life Gain/Lost, Fight, Transformed, Tutor, Becomes Target, Attach, Mana Spent, Draw, Discard, Token Created, Counter Placed, Mana Production)

## Architecture Decisions

### Decision 1: Centralized helpers for sacrifice, token creation, and counter placement
**Rationale**: These three trigger types have multiple code paths that perform the same underlying action. Creating centralized helpers eliminates duplication and ensures triggers fire consistently regardless of which path is taken.

- **Sacrifice**: 4+ code paths (evoke, SBA legend rule, fading, saga end). Create `_sacrifice_permanent(gs, perm_id)` in zones.py that all paths route through.
- **Token Creation**: ~16 token creation functions in stack.py. Create a single `_fire_token_created_trigger(gs, controller)` helper called from the 3 functions that actually create tokens (the rest are stubs).
- **Counter Placement**: `_add_counters()` already exists as a centralized function. Simply add trigger firing inside it.

**Trade-offs considered**: Direct wiring at each call site would avoid refactoring but risks inconsistency and missed paths. Centralized helpers follow the existing pattern used by `_emit_zone_change` for death triggers.

### Decision 2: Fight action as standalone function
**Rationale**: Create `_apply_fight(gs, attacker_id, defender_id)` as a new standalone function in stack.py, wired into both `_apply_single_effect_text()` and `_apply_spell_effect()` via regex patterns. This follows the existing pattern of `_gain_life`, `_lose_life`, etc.

### Decision 3: Becomes target during cast, not resolution
**Rationale**: Per CR 109.3, a permanent "becomes the target" when targets are chosen and validated -- this happens during casting (`_cast_spell`), before the spell goes on the stack. Wire into `_cast_spell()` after target validation (line ~242) but before creating the StackObject.

### Decision 4: Mana triggers at engine call sites only
**Rationale**: `pay_cost` and `add_mana` are pure ManaPool functions that do not have GameState context. Wiring triggers at their call sites in the engine layer is correct. The API router's many `can_pay_cost` calls are for legal actions computation (checking affordability), not actual mana spending, so they should NOT fire triggers.

**Engine pay_cost call sites**:
- `stack.py:160` -- `_cast_spell()` main path
- `morph.py:99` -- turning morph face up

**Engine add_mana call sites**:
- `mana.py:517` -- `resolve_land_mana_ability()`
- `mana.py:822` -- `resolve_mana_ability()` general resolver

### Decision 5: Draw trigger at `_draw_cards`, not just `draw_card`
**Rationale**: The engine's primary draw path is `_draw_cards()` in stack.py (called from effect resolution). `draw_card()` in zones.py is a lower-level helper used by turn manager for draw step. Wiring at both covers all cases.

## Files to Create/Modify

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/zones.py` | Add `_sacrifice_permanent(gs, perm_id)` helper + trigger call | Centralize sacrifice paths |
| `mtg_engine/engine/stack.py` | Wire 9 triggers: life, fight, tutor, discard, token, counter, draw, mana spent, becomes target | Main effect resolution hub |
| `mtg_engine/engine/mana.py` | Wire 2 triggers: mana production (2 call sites) | Mana ability resolution |
| `mtg_engine/engine/daynight.py` | Wire transformed trigger in `_transform_daybound_permanents()` | Day/night transition |
| `mtg_engine/engine/evoke.py` | Route through `_sacrifice_permanent()` helper | Sacrifice centralization |
| `mtg_engine/engine/sba.py` | Route legend rule sacrifice through helper | Sacrifice centralization |
| `mtg_engine/engine/turn_manager.py` | Route fading/saga sacrifices through helper | Sacrifice centralization |
| `mtg_engine/engine/morph.py` | Wire mana spent trigger at pay_cost call site | Mana spending |

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `tests/engine/test_trigger_wiring.py` | Integration tests for all 13 wired triggers | Verify each trigger fires at correct event |

## Task Breakdown (Ordered by Dependency)

### Phase 1: Centralized Helpers (Foundation)

#### Task 1.1: Create `_sacrifice_permanent()` helper in zones.py
- **Files**: `mtg_engine/engine/zones.py`
- **Description**: Create a new pure-transform function that moves a permanent from battlefield to graveyard and fires sacrifice triggers. This replaces inline sacrifice logic across multiple modules.
- **Signature**:
  ```python
  def _sacrifice_permanent(game_state: GameState, perm_id: str) -> tuple[GameState, Permanent | None]:
      """Sacrifice a permanent (move from battlefield to graveyard). Fires sacrifice triggers."""
  ```
- **Acceptance Criteria**: Function moves perm from battlefield to controller's graveyard; calls `check_sacrifice_triggers(gs, [perm_id], controller)` after move; emits zone change event with appropriate metadata; returns (new_gs, sacrificed_perm) tuple

#### Task 1.2: Create `_fire_token_created_trigger()` helper in stack.py
- **Files**: `mtg_engine/engine/stack.py`
- **Description**: Small helper that fires token triggers after a token is created. Called from all token creation functions.
- **Signature**:
  ```python
  def _fire_token_created_trigger(game_state: GameState, controller: str) -> GameState:
      """Fire 'whenever a token enters the battlefield' triggers."""
      from mtg_engine.engine.triggers import check_token_triggers
      return check_token_triggers(game_state, controller)
  ```

#### Task 1.3: Wire counter trigger into `_add_counters()` in stack.py
- **Files**: `mtg_engine/engine/stack.py` (line ~1309)
- **Description**: Add trigger firing to the existing `_add_counters()` function after counters are placed.
- **Changes**: After line 1318 (`perm.counters[counter_type] = ...`), add:
  ```python
  from mtg_engine.engine.triggers import check_counter_triggers
  game_state = check_counter_triggers(game_state, perm_id, perm.controller)
  ```

### Phase 2: Direct Wiring (No Refactoring Needed)

#### Task 2.1: Wire Life Gain/Lost triggers in stack.py
- **Files**: `mtg_engine/engine/stack.py` (lines ~1204, ~1214)
- **Description**: Add trigger calls to `_gain_life()` and `_lose_life()`.
- **Changes**: At end of both functions, before return:
  ```python
  from mtg_engine.engine.triggers import check_life_gain_lost_triggers
  game_state = check_life_gain_lost_triggers(game_state, player_name, n)  # positive for gain
  game_state = check_life_gain_lost_triggers(game_state, player_name, -n) # negative for loss
  ```

#### Task 2.2: Wire Discard triggers in stack.py
- **Files**: `mtg_engine/engine/stack.py` (line ~1240)
- **Description**: Add trigger call to `_discard_cards()` after cards move to graveyard.
- **Changes**: After line 1237 (`player.graveyard.extend(discarded)`), add:
  ```python
  if discarded:
      from mtg_engine.engine.triggers import check_discard_triggers
      game_state = check_discard_triggers(game_state, player_name)
  ```

#### Task 2.3: Wire Tutor/Search Library triggers in stack.py
- **Files**: `mtg_engine/engine/stack.py` (lines ~1243, ~1262)
- **Description**: Add trigger calls to `_tutor()` and `_tutor_to_top()`.
- **Changes**: At end of both functions, before return:
  ```python
  from mtg_engine.engine.triggers import check_tutor_triggers
  game_state = check_tutor_triggers(game_state, player_name)
  ```

#### Task 2.4: Wire Draw triggers in stack.py and zones.py
- **Files**: `mtg_engine/engine/stack.py` (line ~1097), `mtg_engine/engine/zones.py` (line ~800)
- **Description**: Add trigger calls to `_draw_cards()` and `draw_card()`.
- **Changes in stack.py** (`_draw_cards`): After line 1088, add:
  ```python
  if drawn_cards:
      from mtg_engine.engine.triggers import check_draw_triggers
      game_state = check_draw_triggers(game_state, player_name)
  ```

#### Task 2.5: Wire Token Created triggers in stack.py
- **Files**: `mtg_engine/engine/stack.py` (lines ~1197-1198, ~1743, ~1770)
- **Description**: Call `_fire_token_created_trigger()` from the 3 token creation functions that actually create tokens. The remaining ~13 functions are stubs (just log).
- **Functions to modify**: `_create_tokens()`, `_create_token_with_keywords()`, `_create_token_with_pt_and_keywords()`

#### Task 2.6: Wire Attach trigger in stack.py resolve_top()
- **Files**: `mtg_engine/engine/stack.py` (lines ~608-610)
- **Description**: Fire attach trigger after aura attaches to target during resolution.
- **Changes**: After line 610, add:
  ```python
  from mtg_engine.engine.triggers import check_attach_triggers
  game_state = check_attach_triggers(game_state, perm.id)
  ```

#### Task 2.7: Wire Transformed trigger in daynight.py
- **Files**: `mtg_engine/engine/daynight.py` (line ~50-76)
- **Description**: Collect perm IDs that transform and fire transformed triggers after the transformation loop. Change `_transform_daybound_permanents()` to return tuple `(battlefield, transformed_ids)`.

#### Task 2.8: Wire Mana Spent trigger in stack.py _cast_spell()
- **Files**: `mtg_engine/engine/stack.py` (line ~160)
- **Description**: Fire mana spent trigger after paying mana cost during casting.
- **Changes**: After line 160, add:
  ```python
  if mana_payment:
      from mtg_engine.engine.triggers import check_mana_spent_triggers
      game_state = check_mana_spent_triggers(game_state, player_name)
  ```

#### Task 2.9: Wire Mana Spent trigger in morph.py
- **Files**: `mtg_engine/engine/morph.py` (line ~99)
- **Description**: Fire mana spent trigger after paying morph cost to turn face up.

#### Task 2.10: Wire Mana Production trigger in mana.py
- **Files**: `mtg_engine/engine/mana.py` (lines ~517, ~822)
- **Description**: Fire mana production trigger after adding mana to pool from land abilities. In both `resolve_land_mana_ability()` and `resolve_mana_ability()`.

#### Task 2.11: Wire Becomes Target trigger in stack.py _cast_spell()
- **Files**: `mtg_engine/engine/stack.py` (line ~242)
- **Description**: Fire becomes target trigger for each permanent target during casting, after targets are validated but before StackObject is created.

### Phase 3: Fight Action (New Function + Wiring)

#### Task 3.1: Create `_apply_fight()` function in stack.py
- **Files**: `mtg_engine/engine/stack.py` (new function near line ~1280)
- **Description**: Implement the fight action per CR 701.6 -- each creature deals damage equal to its power to the other. Then fire fight triggers. Reuses `_deal_damage()` for keyword handling.

#### Task 3.2: Wire fight pattern into effect resolution
- **Files**: `mtg_engine/engine/stack.py` (both `_apply_single_effect_text()` and `_apply_spell_effect()`)
- **Description**: Add regex patterns to match "target creature fights target creature" in both effect resolution functions.

### Phase 4: Sacrifice Centralization (Refactoring)

#### Task 4.1: Implement `_sacrifice_permanent()` in zones.py
- See Task 1.1 for full details.

#### Task 4.2: Refactor evoke.py to use `_sacrifice_permanent()`
- **Files**: `mtg_engine/engine/evoke.py` (lines ~95-113)
- Replace inline sacrifice logic with call to centralized helper.

#### Task 4.3: Refactor SBA legend rule to use `_sacrifice_permanent()`
- **Files**: `mtg_engine/engine/sba.py` (lines ~247-249)
- Replace inline `_move_to_graveyard()` call with `_sacrifice_permanent()`.

#### Task 4.4: Refactor turn_manager.py fading/saga sacrifices to use `_sacrifice_permanent()`
- **Files**: `mtg_engine/engine/turn_manager.py` (lines ~230, ~276)

### Phase 5: Cast Triggers (Bonus -- Already Exists but Not Wired)

#### Task 5.1: Wire `check_cast_triggers` in stack.py _cast_spell()
- **Files**: `mtg_engine/engine/stack.py` (line ~278, after spells_cast_this_turn increment)
- The existing `check_cast_triggers()` function is also dead code. Wire it into `_cast_spell()`.

## Data Models / Interfaces

No new data models needed. All trigger functions use existing `GameState`, `PendingTrigger`, and `Permanent` models. The only signature change is `_transform_daybound_permanents()` which now returns a tuple instead of just the battlefield list.

```python
# New helper signatures (no model changes)
def _sacrifice_permanent(gs: GameState, perm_id: str) -> tuple[GameState, Permanent | None]: ...
def _fire_token_created_trigger(gs: GameState, controller: str) -> GameState: ...
def _apply_fight(gs: GameState, attacker_id: str, defender_id: str) -> GameState: ...

# Modified signature
def _transform_daybound_permanents(gs: GameState) -> tuple[list[Permanent], list[str]]: ...
```

## Testing Strategy

### Test File: `tests/engine/test_trigger_wiring.py`
One comprehensive test file with ~130 tests (8-10 per trigger type):

#### Sacrifice Trigger Tests (10 tests)
- `test_sacrifice_triggers_fire_on_evoke`: Cast evoke creature, resolve ETB, end step -- sacrifice triggers fire
- `test_sacrifice_triggers_fire_on_legend_rule`: Two legendary permanents with same name -- sacrifice trigger fires for sacrificed one
- `test_sacrifice_triggers_fire_on_fading`: Fading permanent loses last counter -- sacrifice trigger fires
- `test_sacrifice_triggers_noop_for_non_creature`: Sacrificing a land does NOT fire "whenever a creature is sacrificed" triggers
- `test_sacrifice_triggers_controller_filter`: "Whenever you sacrifice" only fires for controller's permanents
- `test_sacrifice_pure_transform`: `_sacrifice_permanent()` returns new GameState object

#### Life Gain/Lost Trigger Tests (10 tests)
- `test_life_gain_triggers_fire_on_gain`: Player gains life -- triggers fire
- `test_life_lost_triggers_fire_on_lose`: Player loses life -- triggers fire
- `test_life_trigger_amount_preserved`: Trigger data includes the amount gained/lost
- `test_life_trigger_controller_filter`: "Whenever you gain life" only fires for correct player

#### Fight Trigger Tests (10 tests)
- `test_fight_triggers_fire_on_fight_effect`: "Target creature fights target creature" -- both creatures fire triggers
- `test_fight_deals_damage_correctly`: Each creature deals power damage to the other
- `test_fight_this_trigger_guard`: "Whenever this creature fights" only fires for participating creatures
- `test_fight_pattern_in_spell_effect`: Fight pattern matches in `_apply_spell_effect()`

#### Transformed Trigger Tests (8 tests)
- `test_transformed_triggers_fire_on_day_night`: Day/night transition -- transformed permanents fire triggers
- `test_transformed_this_trigger_guard`: "Whenever this transforms" only fires for the transforming permanent
- `test_transformed_noop_when_no_faces`: Permanents without faces do not transform or trigger

#### Tutor Trigger Tests (8 tests)
- `test_tutor_triggers_fire_on_search`: Library search -- tutor triggers fire
- `test_tutor_triggers_fire_on_tutor_to_top`: Spree tutor-to-top also fires triggers
- `test_tutor_controller_filter`: "Whenever you search" only fires for correct player

#### Becomes Target Trigger Tests (8 tests)
- `test_becomes_target_fires_on_cast`: Casting spell targeting permanent -- trigger fires
- `test_becomes_target_noop_for_player_targets`: Targeting a player does NOT fire permanent triggers
- `test_becomes_target_multiple_targets`: Multiple targets each fire their own triggers

#### Attach Trigger Tests (8 tests)
- `test_attach_triggers_fire_on_aura_resolution`: Aura resolves and attaches -- trigger fires
- `test_attach_this_trigger_guard`: "Whenever this becomes attached" only fires for the aura itself

#### Mana Spent Trigger Tests (10 tests)
- `test_mana_spent_fires_on_cast`: Casting a spell -- mana spent triggers fire
- `test_mana_spent_fires_on_morph`: Turning morph face up -- mana spent triggers fire
- `test_mana_spent_noop_when_free_cast`: Alternative cost with no mana does not fire triggers

#### Draw Trigger Tests (8 tests)
- `test_draw_triggers_fire_on_draw_cards`: Drawing cards -- draw triggers fire
- `test_draw_triggers_fire_on_single_draw`: Single card draw also fires triggers
- `test_draw_controller_filter`: "Whenever you draw" only fires for correct player

#### Discard Trigger Tests (8 tests)
- `test_discard_triggers_fire_on_discard`: Discarding cards -- discard triggers fire
- `test_discard_noop_when_empty_hand`: Discarding with empty hand does not crash or trigger

#### Token Created Trigger Tests (10 tests)
- `test_token_triggers_fire_on_create_tokens`: Basic token creation fires triggers
- `test_token_triggers_fire_on_keyword_tokens`: Token with keywords also fires triggers
- `test_token_triggers_controller_filter`: "Whenever you create a token" only fires for controller

#### Counter Trigger Tests (8 tests)
- `test_counter_triggers_fire_on_add_counters`: Adding counters -- counter triggers fire
- `test_counter_triggers_in_effect_resolution`: Counter patterns in spell effects also fire triggers

#### Mana Production Trigger Tests (8 tests)
- `test_mana_production_fires_on_land_tap`: Tapping land for mana -- production trigger fires
- `test_mana_production_includes_source_info`: Trigger data includes source permanent ID and mana symbols

### Integration Test Pattern
Each test follows the established pattern from AGENTS.md:
```python
def test_trigger_fires_on_event():
    gs = _make_game()  # Standard game setup
    # ... set up card with trigger ability on battlefield ...
    # ... perform the triggering event ...

    # Verify trigger was queued
    sacrifice_triggers = [t for t in gs.pending_triggers if t.trigger_type == "sacrifice"]
    assert len(sacrifice_triggers) >= 1
    assert sacrifice_triggers[0].source_card_name == "Trigger Card Name"
```

## Potential Risks

### Risk 1: Sacrifice centralization breaks existing behavior
**Mitigation**: The `_sacrifice_permanent()` helper replicates the exact same logic as `resolve_evoke_sacrifice()` (move to graveyard, emit event). Unit tests verify identical output. The SBA legend rule already uses `_move_to_graveyard()` which is similar but does not emit events -- we need to ensure the zone change event is still emitted for death trigger compatibility.

### Risk 2: Fight action damage handling
**Mitigation**: Reuse existing `_deal_damage()` function which already handles deathtouch, lifelink, infect keywords correctly (per P0 Combat Modifiers refactoring). This ensures fight damage goes through the same keyword pipeline as combat damage.

### Risk 3: Becomes target timing -- triggers fire before spell resolves
**Mitigation**: Per CR 109.3 and CR 603.2, "becomes the target" is a state-based event that happens when targets are chosen. The trigger should indeed fire during casting, not resolution. This means the triggered ability goes on the stack BELOW the spell being cast (LIFO order), which is correct MTG rules behavior.

### Risk 4: Mana spent triggers at API layer
**Mitigation**: Explicitly scope mana spent wiring to engine-layer call sites only (`stack.py`, `morph.py`). The API router's `can_pay_cost` calls are for legal actions computation and should NOT fire triggers. Document this clearly in code comments.

### Risk 5: Circular imports between stack.py and triggers.py
**Mitigation**: All trigger functions use lazy imports (`from mtg_engine.engine.triggers import ...` inside the function body). This pattern is already used throughout the codebase (e.g., `_apply_venture` at line 1289) and avoids circular import issues.

### Risk 6: Transform signature change breaks callers
**Mitigation**: Only one caller of `_transform_daybound_permanents()` exists (`check_day_night_transition()` in daynight.py). Update the unpacking to handle the new tuple return value. No external callers exist.

## Migration Plan

1. **Phase 1** (helpers): Low risk, no behavior changes yet
2. **Phase 2** (direct wiring): Medium risk, each trigger wired independently -- run full test suite after each
3. **Phase 3** (fight action): Medium risk, new functionality with damage handling
4. **Phase 4** (sacrifice refactor): Higher risk due to refactoring existing paths -- verify evoke, SBA, fading, saga all still work
5. **Phase 5** (cast triggers): Low risk, bonus wiring

Run `pytest` after each phase. Current baseline: ~2776 tests pass, 3 skipped, 13 xfailed, 0 regressions.

---

## Handoff to Implementer

**Design Document**: Above
**User Story**: TRG-20/TRG-B1: Wire all dead-code trigger check functions
**Estimated Complexity**: **High** -- 13 triggers across 8 files, including new function creation and refactoring
**Key Files**:
1. `mtg_engine/engine/stack.py` (9 of 13 triggers wired here)
2. `mtg_engine/engine/zones.py` (_sacrifice_permanent helper + draw trigger)
3. `mtg_engine/engine/triggers.py` (all check functions already exist)
4. `tests/engine/test_trigger_wiring.py` (new test file, ~130 tests)

**Start With**: Phase 1 -- create the three centralized helpers (_sacrifice_permanent, _fire_token_created_trigger, counter wiring in _add_counters). These are foundation tasks with no behavioral changes that other phases depend on.

**Acceptance Criteria**: All 13 trigger check functions fire at their correct game events; full test suite passes with zero regressions; ~130 new integration tests verify each trigger type.

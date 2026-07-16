# Task Status: TRG-20 Trigger Bug Fixes & New Trigger Types (Sprint 3)

## Objective
- Implement TRG-20 trigger bug fixes (9 failing tests) and add 5 new trigger types for Sprint 3 of the MTG engine in `mtg_engine/engine/triggers.py`

## Important Details
- All B1 check functions must be pure transforms: return `GameState.model_copy(update={"pending_triggers": ...})`, never mutate directly
- "you" patterns (index 0) require controller filtering: only fire if `perm.controller == player_name`
- Self-referential triggers ("this creature", "this becomes attached") need identity guards matching the event target

## Work State
### Completed
- Added `_is_you_pattern(pattern_idx)` helper function near top of B1 section (~line 572)
- Fix 1: Added `r"whenever (?:a|an) .*? dies"` to `SACRIFICE_TRIGGER_PATTERNS`
- Fix 4: Updated `TRANSFORMED_TRIGGER_PATTERNS[0]` to match "this creature transforms" with `(?:\s+creature)?`
- Fix 9: Added `r"whenever a player spends mana"` to `MANA_PRODUCTION_TRIGGER_PATTERNS`
- Converted all B1 functions to pure transforms: `check_sacrifice_triggers`, `check_life_gain_lost_triggers`, `check_fight_triggers`, `check_proliferated_triggers`, `check_transformed_triggers`, `check_tutor_triggers`, `check_becomes_target_triggers`, `check_attach_triggers`, `check_day_night_change_triggers`, `check_completed_dungeon_triggers`, `check_mana_spent_triggers`, `check_mana_production_triggers`
- Fix 2: Added `_is_you_pattern` filter to `check_life_gain_lost_triggers`
- Fix 3: Added `_is_you_pattern` filter to `check_proliferated_triggers`
- Fix 5: Added `_is_you_pattern` filter to `check_tutor_triggers`
- Fix 6: Added self-referential guard for "whenever this becomes attached" in `check_attach_triggers` + fallback oracle text parsing when ability parser can't handle mixed static+triggered abilities
- Fix 7: Added `_is_you_pattern` filter to `check_completed_dungeon_triggers`
- Fix 8: Added `_is_you_pattern` filter to `check_mana_spent_triggers`
- Fixed conflicting test in `test_triggers_expanded.py`: renamed `test_no_trigger_opponent_life_change_does_not_affect_p1` to `test_a_player_pattern_fires_for_any_player` (correct MTG behavior: "a player" patterns watch ALL players)
- Updated all 25 tests in `test_b1_missing_triggers.py` to capture return values from pure transform functions
- Fixed wrong expectation in `test_proliferate_integration.py::TestTriggerFiring::test_trigger_not_fired_for_other_player`: "you proliferate" correctly does NOT fire for opponent

### Test Results
- 624 engine tests passed, 13 xfailed (expected), 0 regressions
- All TRG-20 related tests pass: test_triggers_expanded.py (33), test_b1_missing_triggers.py (25)

## Next Move
Part B: Implement 5 new trigger types (draw, discard, token, counter, planeswalk) with pure transforms and controller filtering

## Relevant Files
- `mtg_engine/engine/triggers.py`: Main file — all pattern fixes, helper function, B1 function conversions, attach fallback applied here
- `tests/engine/test_triggers_expanded.py`: 33 tests for TRG-20 bug fixes (all passing)
- `tests/engine/test_b1_missing_triggers.py`: 25 pre-existing tests updated to pure transform pattern (all passing)
- `tests/engine/test_proliferate_integration.py`: Fixed wrong test expectation in TestTriggerFiring class

# Story: Day/Night Cycle (CR 702.148) — DNG-01

## User Story
As a player, I want the Day/Night cycle fully implemented — automatic transitions based on spells cast, daybound/nightbound transformation — so that werewolf and daybound cards like Huntmaster of the Fells and Tovolar's Huntmaster work correctly.

## Context
**Status: ✅ Complete**

Implemented as DNG-01. Full CR 730 Day/Night Designation logic with pure transforms:

- **`check_daynight_transition(gs)`**: Core transition logic checked at each turn boundary.
  - Day → Night: Previous active player cast 0 spells last turn.
  - Night → Day: Previous active player cast 2+ spells last turn.
- **`set_day(gs)` / `set_night(gs)`**: Explicit day/night setters for cards that care.
- **`is_daytime(gs)`**: Query helper returning `True` (day), `False` (night), or `None` (neither).
- **`_transform_daybound_permanents(gs)`**: Transforms all permanents with daybound/nightbound keywords, flipping their `face_index` between 0 and 1.
- **Trigger integration**: `check_day_night_change_triggers()` in triggers.py fires for cards that care about day/night transitions (e.g., Tovolar's Huntmaster).
- **Game start**: `is_day = None` (neither day nor night) — first transition triggers when conditions are met.

## Acceptance Criteria
- [x] Game starts with neither day nor night (`is_day = None`)
- [x] Day → Night transition when previous active player cast 0 spells
- [x] Night → Day transition when previous active player cast 2+ spells
- [x] Daybound/nightbound permanents transform on transition (face_index flip)
- [x] `set_day()` and `set_night()` for explicit designation
- [x] `is_daytime()` query helper
- [x] Trigger integration for day/night change events
- [x] All state transforms use pure model_copy — no direct mutations
- [x] 40 tests covering transitions, transformation, triggers, edge cases

## Dependencies
- None (standalone module)

## Priority: High | Effort: Completed ✅

## Notes
- Key file: `mtg_engine/engine/daynight.py` (97 lines)
- Trigger wiring: `mtg_engine/engine/triggers.py` line 253 (pattern definitions), line 986 (check function)
- Turn manager hook: `mtg_engine/engine/turn_manager.py` line 161-162
- Test files: Various integration tests in `tests/engine/`
- Daybound creatures (e.g., Tovolar's Huntmaster) and nightbound creatures (e.g., Tovolar's Packleader) are DFCs with two faces
- Spells cast tracking uses `game_state.spells_cast_last_turn` updated at turn boundaries

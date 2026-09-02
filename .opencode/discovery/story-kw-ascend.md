# Story: Ascend (CR 702.130)

## User Story
As an MTG engine developer, I want a new ascend keyword module with real apply() and integration tests, so that cards with ascend and the city's blessing work correctly in the engine.

## Context
No file exists for ascend. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.130a**: "Ascend is a triggered ability. 'Ascend' means 'When you have ten or more permanents, you get the city's blessing for the rest of the game.'"
- **CR 702.130b**: "A player who has the city's blessing has 'the city's blessing' designation for the remainder of the game. Once gained, it cannot be lost."
- **Example card**: Legion's Landing — "Ascend (If you control ten or more permanents, you get the city's blessing for the rest of the game.)"
- **Rule source**: Permanent-count threshold tracker that grants a permanent designation

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/ascend.py` with `Ascend` class extending `PassiveKeyword`
- [ ] `check_ascend(game_state, player_name) -> bool` checks if player controls 10+ permanents
- [ ] `get_citys_blessing(game_state, player_name) -> bool` query helper
- [ ] `grant_citys_blessing(game_state, player_name)` pure transform granting the designation
- [ ] `cities_blessing: bool` field added to `PlayerState` or tracked via `GameState`
- [ ] Ascend checked during state-based actions and on each permanent entering the battlefield
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: threshold not met, threshold met, permanents count includes all types, blessing persists after permanent loss, multiple players with ascend
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- City's blessing is permanent once granted — never lost even if permanent count drops below 10
- Need to track `cities_blessing` per player (boolean on PlayerState)
- Check should happen as a state-based action and as a trigger on ETB
- Ixalan block mechanic, appears in supplementary sets (Jumpstart, Commander)

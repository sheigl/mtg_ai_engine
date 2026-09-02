# Story: Surge (CR 702.126)

## User Story
As an MTG engine developer, I want the surge keyword module to have a real `apply()` implementation with integration tests, so that cards with surge produce correct game state instead of silently no-op'ing.

## Context
The surge keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.126**: "Surge [cost] means 'You may cast this spell for its surge cost if you or a teammate has cast another spell this turn.'"
- **Example card**: Slip Through Space — "Surge {U}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
Alternative cost mechanic. Instead of the normal mana cost, player may pay the surge cost if another spell was cast by them or a teammate this turn. Check `spells_cast_this_turn` on GameState. Wires into the spell-casting cost calculation path.

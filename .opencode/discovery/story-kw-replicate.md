# Story: Replicate (CR 702.55)

## User Story
As an MTG engine developer, I want the replicate keyword module to have a real `apply()` implementation with integration tests, so that cards with replicate produce correct game state instead of silently no-op'ing.

## Context
The replicate keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.55**: "Replicate [cost] means 'When you cast this spell, you may pay an additional [cost] any number of times. If you do, copy it that many times.'"
- **Example card**: Izzet Guildmage — "Replicate {1}{U}{R}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: M

## Notes
Replicate triggers on-cast (like Storm). When the spell is on the stack, player may pay additional {cost} any number of times, creating that many copies on the stack. Requires `pending_replicate_choice` for human path. Copies inherit targets but may choose new ones (per CR 702.55c). LIFO ordering on stack.

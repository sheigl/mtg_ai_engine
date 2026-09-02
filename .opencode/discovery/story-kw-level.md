# Story: Level Up (CR 702.84)

## User Story
As an MTG engine developer, I want the level keyword module to have a real `apply()` implementation with integration tests, so that cards with level up produce correct game state instead of silently no-op'ing.

## Context
The level keyword module exists with detection/parsing logic and a `level_up()` method that mutates via `permanent.counters = ...` directly. `apply()` delegates to `level_up()` but both need pure-transform refactoring. No integration tests exist.

### Comprehensive Rules Grounding
- **CR 702.84**: "'Level up [cost]' means '[Cost]: Put a level counter on this permanent. Level up only as a sorcery.' Each level range defines a different power/toughness and set of abilities."
- **Example card**: Student of Warfare — "Level up {W}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: M

## Notes
Level Up puts level counters (not +1/+1 counters). Each level threshold grants new P/T and abilities. Requires `pending_level_up_choice` for human path (choose how many times to activate). AI auto-resolves based on available mana. Powers and toughnesses change at level thresholds — needs `get_active_abilities()` hook into combat resolution. Level creatures have three stat blocks (base/low/mid/high).

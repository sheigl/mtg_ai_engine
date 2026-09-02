# Story: Extort (CR 702.63b)

## User Story
As an MTG engine developer, I want the extort keyword module to have a real `apply()` implementation with integration tests, so that cards with extort produce correct game state instead of silently no-op'ing.

## Context
The extort keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.63b**: "Whenever you cast a spell, you may pay {W/B}. If you do, each opponent loses 1 life and you gain that much life."
- **Example card**: Crypt Ghast — "Extort"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: M

## Notes
Triggered ability that fires on-cast. Each permanent with extort independently triggers when its controller casts any spell. Human path queues `pending_extort_choice` per trigger. AI always pays if it has the hybrid {W/B} mana. Multiple extort permanents means multiple triggers (stack each independently).

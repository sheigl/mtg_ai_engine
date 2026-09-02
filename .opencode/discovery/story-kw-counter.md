# Story: Counter Spell (CR 701.5)

## User Story
As an MTG engine developer, I want the counter keyword module to have a real `apply()` implementation with integration tests, so that cards with counter effects produce correct game state instead of silently no-op'ing.

## Context
The counter keyword module exists with detection/parsing logic for counter placement/removal but its `apply()` method mutates directly via `permanent.counters = ...`. It needs refactoring to use pure transforms (`model_copy(update={...})`) and proper integration tests.

### Comprehensive Rules Grounding
- **CR 701.5**: "To counter a spell or ability means to cancel it, removing it from the stack. It doesn't resolve, and none of its effects occur."
- **Example card**: Cancel — "Counter target spell."

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
The counter.py module currently handles counter placement/removal (CR 704.5, not 701.5). It also directly mutates `permanent.counters` in `add_counters()`/`remove_counters()`. Must refactor to `model_copy(update=...)` pattern. The "Counter target spell" standalone spell effect (CR 701.5) may be better handled via existing stack.py `_counter_spell()`; this module should focus on counter placement/removal as a game action.

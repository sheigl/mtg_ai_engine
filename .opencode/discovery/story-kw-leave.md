# Story: Leave (Leaves-the-Battlefield Triggers)

## User Story
As an MTG engine developer, I want the leave keyword module to have a real `apply()` implementation with integration tests, so that cards with leaves-the-battlefield triggers produce correct game state instead of silently no-op'ing.

## Context
The leave keyword module exists with detection/parsing logic for LTB trigger patterns and a `create_trigger()` method. However, `apply()` only logs the event — it doesn't queue a `PendingTrigger` or modify game state. No integration tests exist.

### Comprehensive Rules Grounding
- **CR 603.2**: "A triggered ability begins with 'when,' 'whenever,' or 'at.' It triggers on an event and has an effect."
- **CR 700.4**: "'Dies' means 'is put into a graveyard from the battlefield.'"
- **Example card**: Angel of Renewal — "Leave — Draw a card"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
Leave/Leaves-the-Battlefield (LTB) triggers fire when a permanent moves from battlefield to any other zone (graveyard, exile, hand, library). Includes "dies" triggers (graveyard only). `apply()` should queue a `PendingTrigger` that the trigger engine resolves. Must integrate with zone-change hooks in zones.py. Self-referential ("when this leaves") vs. global ("whenever a creature dies") patterns.

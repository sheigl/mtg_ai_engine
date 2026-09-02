# Story: Unearth (CR 702.83)

## User Story
As an MTG engine developer, I want the unearth keyword module to have a real `apply()` implementation with integration tests, so that cards with unearth produce correct game state instead of silently no-op'ing.

## Context
The unearth keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.83**: "Unearth [cost] means '[Cost], Return this card from your graveyard to the battlefield. It gains haste. Exile it at the beginning of the next end step or if it would leave the battlefield. Unearth only as a sorcery.'"
- **Example card**: Shriekmaw — "Unearth {1}{B}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
Graveyard-to-battlefield return on a Permanent. Requires checking the card is in graveyard. Must add haste, track end-step exile via `pending_triggers`, and enforce sorcery-speed timing. Human path queues pending choice; AI auto-resolves if affordable. Follow the Kicker/Flashback pattern with `pending_unearth_choice` on GameState.

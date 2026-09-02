# Story: Suspend (CR 702.62)

## User Story
As an MTG engine developer, I want the suspend keyword module to have a real `apply()` implementation with integration tests, so that cards with suspend produce correct game state instead of silently no-op'ing.

## Context
The suspend keyword module exists with detection/parsing logic and a `create_trigger()` method, but `apply()` is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.62**: "Suspend N[cost] means 'You may exile this card from your hand with N time counters on it by paying [cost].' At the beginning of your upkeep, remove a time counter. When the last is removed, cast it without paying its mana cost."
- **Example card**: Lotus Bloom — "Suspend 3—{0}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: L

## Notes
Complex time-delayed mechanic. Three phases: (1) Suspend from hand — exile card with N time counters, pay cost. (2) Each upkeep — remove a time counter. (3) When last removed — cast without mana cost. Needs `suspended_cards` field on GameState tracking suspended cards with remaining counters. Upkeep hook in turn_manager.py. Exile zone tracking for suspended cards. Human path queues choices; AI suspends if card is uncastable normally.

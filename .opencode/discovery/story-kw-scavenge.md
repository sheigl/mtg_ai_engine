# Story: Scavenge (CR 702.96)

## User Story
As an MTG engine developer, I want the scavenge keyword module to have a real `apply()` implementation with integration tests, so that cards with scavenge produce correct game state instead of silently no-op'ing.

## Context
The scavenge keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.96**: "Scavenge [cost] means '[Cost], Exile this card from your graveyard: Put a number of +1/+1 counters equal to this card's power on target creature. Scavenge only as a sorcery.'"
- **Example card**: Deadbridge Goliath — "Scavenge {4}{G}{G}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
Activated ability from graveyard. Exile the card as part of cost, put N +1/+1 counters on target creature where N = exiled card's power. Requires target selection. Sorcery-speed timing. Human path queues choice; AI picks best target (with most benefit from counters).

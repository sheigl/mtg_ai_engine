# Story: Transmute (CR 702.95)

## User Story
As an MTG engine developer, I want the transmute keyword module to have a real `apply()` implementation with integration tests, so that cards with transmute produce correct game state instead of silently no-op'ing.

## Context
The transmute keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.95**: "Transmute [cost] means '[Cost], Discard this card: Search your library for a card with the same mana value as this card, reveal it, put it into your hand, then shuffle. Transmute only as a sorcery.'"
- **Example card**: Dimir House Guard — "Transmute {1}{U}{B}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
Activated ability from hand. Requires discarding the card as cost, searching library for same-CMV card, shuffling. Needs library search infrastructure (filter by cmc). Human path queues pending choice; AI picks first matching card. Mana payment from pool.

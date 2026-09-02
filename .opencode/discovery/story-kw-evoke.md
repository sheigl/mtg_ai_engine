# Story: Evoke (CR 702.74)

## User Story
As an MTG engine developer, I want the evoke keyword module to have a real `apply()` implementation with integration tests, so that cards with evoke produce correct game state instead of silently no-op'ing.

## Context
The evoke keyword module exists with detection/parsing logic and a `create_trigger()` method, but `apply()` is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.74**: "Evoke [cost] means 'You may cast this card for its evoke cost rather than its mana cost.' The creature enters with a triggered ability that says 'When this creature enters the battlefield, sacrifice it.'"
- **Example card**: Mulldrifter — "Evoke {2}{U}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: M

## Notes
Alternative cost mechanic during spell casting (like Kicker). When cast for evoke cost, the creature ETBs with a sacrifice trigger. Needs `pending_evoke_choice` for human path (pay evoke cost or normal mana cost). AI pays evoke cost if affordable and the ETB effect is positive. The sacrifice trigger fires on ETB (not on-cast), so must queue an ETB trigger via `_queue_etb_triggers()`.

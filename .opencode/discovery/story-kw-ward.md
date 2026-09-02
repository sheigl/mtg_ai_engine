# Story: Ward (CR 702.145)

## User Story
As an MTG engine developer, I want the Ward keyword module to have a real `apply()` implementation with integration tests, so that permanents with Ward counter opponent targeting unless a cost is paid.

## Context
The Ward keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.145a**: "Ward is a triggered ability. 'Ward {cost}' means 'Whenever this permanent becomes the target of a spell or ability an opponent controls, counter it unless that player pays {cost}.'"
- **CR 702.145b**: "If an object has multiple instances of ward, each triggers separately."
- **Example card**: Silver Scourge — "Ward {2}" (whenever this becomes the target of a spell or ability an opponent controls, counter it unless that player pays {2})

## Acceptance Criteria
- [ ] `Ward.apply(game_state, permanent)` implements full ward logic: detects when permanent becomes targeted by opponent's spell/ability; queues `pending_ward_payment` for human players (ward controller decides whether to enforce)
- [ ] Ward only triggers on targeting by opponents — self-targeting by controller bypasses ward (CR 702.145b)
- [ ] Ward cost is paid by the spell/ability's controller, not the ward's controller
- [ ] Multiple ward instances on same permanent: each triggers independently
- [ ] Integration tests in `tests/engine/test_ward_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **GS-363**: `pending_ward_payment: Optional[dict]` already exists on GameState (line 363) with format `{"player": str, "ward_cost": str, "targeting_spell_id": str}` — reuse this for human ward payment decisions.
- **Ward targeting integration**: Ward needs to hook into the targeting validation flow. When a spell/ability is cast and targets a permanent with ward by an opponent, trigger the ward. Reference how hexproof/shroud integrate with targeting in `hexproof.py` and `shroud.py`.
- **Counter interaction**: If ward cost is not paid, counter the targeting spell/ability — remove it from the stack (if a spell) or prevent its effect (if an ability). Wire into stack.py's resolution flow.
- **Ward is fundamentally a triggered ability** — it should fire as a PendingTrigger when targeting occurs, not via a direct apply() call.

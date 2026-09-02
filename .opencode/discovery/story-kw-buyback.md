# Story: Buyback (CR 702.27)

## User Story
As an MTG engine developer, I want the Buyback keyword module to have a real `apply()` implementation with integration tests, so that spells with Buyback can be paid for with additional mana to return to hand instead of going to graveyard.

## Context
The Buyback keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.27a**: "Buyback is an additional cost. 'Buyback {cost}' means 'You may pay an additional {cost} as you cast this spell. If you do, the spell returns to your hand instead of going to your graveyard as it resolves.'"
- **Rule source**: Additional casting cost modifier that returns the spell to hand on resolution
- **Example card**: Whispers of the Muse — "Buyback {4}" (pay {4} additional on cast; when it resolves, it goes back to your hand)

## Acceptance Criteria
- [ ] `BuybackKeyword.apply(game_state, permanent)` implements full buyback logic: detects buyback cost; queues `pending_buyback_choice` for human players with cost
- [ ] AI auto-resolves by paying if mana affordable (heuristic: pay if extra mana available after base cost)
- [ ] Buyback is an additional cost paid during spell declaration — affects mana payment flow in stack.py
- [ ] When buyback is paid, the spell goes to its owner's hand instead of graveyard on resolution (update `buyback_paid` flag on StackObject)
- [ ] Integration tests in `tests/engine/test_buyback_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
- **StackObject tracking**: `StackObject.buyback_paid: bool` already exists (game.py line 157). Set this flag when buyback cost is paid during casting. Check it during spell resolution to send spell to hand instead of graveyard.
- **Cost payment**: Buyback is an additional cost, not an alternative cost — the base cost must still be paid. Wire into stack.py's cost payment flow.
- **Human/AI pattern**: Follow the same pending choice pattern as Kicker (KW-16) — queue a choice for human players, auto-resolve for AI.

# Story: Overload (CR 702.95)

## User Story
As an MTG engine developer, I want the Overload keyword module to have a real `apply()` implementation with integration tests, so that spells with Overload can be cast for an alternative cost that replaces "target" with "each."

## Context
The Overload keyword module exists with partial parsing logic but its core `apply()` method is missing. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.95a**: "Overload is an alternative cost. 'Overload {cost}' means 'You may cast this spell for its overload cost. If you do, change its text by replacing all instances of "target" with "each."'"
- **CR 702.95b**: "If a spell is overloaded, it targets nothing and can't be countered for lacking targets."
- **Example card**: Cyclonic Rift — "Overload {6}{U}" (pay {6}{U} instead of {1}{U}; instead of returning one nonland permanent to hand, return each nonland permanent you don't control)

## Acceptance Criteria
- [ ] `OverloadKeyword.apply(game_state, permanent)` implements full overload logic: detects overload cost; queues `pending_overload_choice` for human players
- [ ] AI auto-resolves by paying if spell targets a single opponent (beneficial to mass-effect)
- [ ] Overload is an alternative cost (replaces base mana cost entirely, not additional) — wired into alternative cost payment flow
- [ ] When overload is paid, set `overload_paid=True` on StackObject and replace "target" with "each" in spell text at resolution
- [ ] Overloaded spells target nothing — bypass targeting validation for "each" versions
- [ ] Integration tests in `tests/engine/test_overload_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
- **StackObject tracking**: `StackObject.overload_paid: bool` already exists (game.py line 171). Set this flag when overload cost is selected during casting.
- **Alternative cost vs additional cost**: Unlike Kicker/Buyback, Overload replaces the base cost entirely. It follows the same pattern as Miracle — choose which cost to pay, pay only that cost.
- **Text replacement**: When resolving an overloaded spell, replace "target" with "each" in effect text. This affects targeting logic and effect application. Reference the existing overload module's `get_overload_targets()` for target expansion logic.
- **The overload module needs restructuring** — currently uses a standalone `OverloadModel` pattern instead of the standard KeywordAbility subclass pattern. Should be refactored to inherit from CostKeyword.

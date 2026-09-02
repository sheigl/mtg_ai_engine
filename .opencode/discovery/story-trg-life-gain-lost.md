# Story: Life Gain/Lost Trigger (CR 701.12 / CR 701.13)

## User Story
As an MTG engine developer, I want life gain and loss triggers wired into the engine event flow, so that cards with "whenever a player gains or loses life" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_life_gain_lost_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into stack.py's `_gain_life()` and `_lose_life()` helper functions.

### Comprehensive Rules Grounding
- **CR 701.12**: "To gain life, add the indicated amount to your current life total."
- **CR 701.13**: "To lose life, subtract the indicated amount from your current life total."
- Example card: *Geth's Grimoire* — "Whenever a player gains or loses life, you may put a charge counter on Geth's Grimoire equal to the amount of life gained or lost."

## Acceptance Criteria
- [ ] Call `check_life_gain_lost_triggers()` from stack.py's `_gain_life()` helper function with player name and positive amount
- [ ] Call `check_life_gain_lost_triggers()` from stack.py's `_lose_life()` helper function with player name and negative amount (or separate parameter for direction)
- [ ] Pass player name and amount to the check function
- [ ] Integration test: life gain fires trigger, life loss fires trigger, zero-life change does NOT fire

## Dependencies
- None (uses existing check function; only adds call sites)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- The check function should receive both the player name and the amount (positive for gain, negative or separate flag for loss). This allows triggers that distinguish between "gains life" vs "loses life".

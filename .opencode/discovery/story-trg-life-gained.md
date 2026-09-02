# Story: Life Gained Trigger (CR 701.12)

## User Story
As an MTG engine developer, I want a "life gained" trigger pattern with proper check function and wiring, so that cards with "whenever you gain life" triggered abilities fire correctly instead of silently no-op'ing.

## Context
A combined `LIFE_GAIN_LOST_TRIGGER_PATTERNS` and `check_life_gain_lost_triggers()` exist in triggers.py but are NOT wired into the engine's `_gain_life()` flow. This story covers specifically the "life gained" side (CR 701.12) — distinct from "life lost" (CR 701.13).

### Comprehensive Rules Grounding
- **CR 701.12**: "If an effect causes a player to gain life, the player puts that many cards from their library into their hand."
- **Game event**: A player's life total increases due to an effect
- **Example card**: *Ajani's Pridemate* — "Whenever you gain life, put a +1/+1 counter on ~."

## Acceptance Criteria
- [ ] Call `check_life_gain_lost_triggers(gs, player_name, "gain")` from stack.py's `_gain_life()` helper after life total is modified
- [ ] Capture return value (`gs = check_life_gain_lost_triggers(...)`)
- [ ] Integration tests: gaining life fires trigger, losing life fires separate Life Lost trigger, zero-net-gain mixed events fire both
- [ ] No regressions

## Dependencies
- None (wiring existing check function)

## Priority: High

## Estimated Effort: S

## Notes
- The existing combined check function handles both gain and loss — wire it in with a direction parameter
- Forge's trigger: `LifeGainedTrigger` (separate from `LifeLostTrigger`)

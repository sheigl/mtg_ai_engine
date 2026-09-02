# Story: Life Lost Trigger (CR 701.13)

## User Story
As an MTG engine developer, I want a "life lost" trigger pattern with proper check function and wiring, so that cards with "whenever an opponent loses life" triggered abilities fire correctly instead of silently no-op'ing.

## Context
A combined `LIFE_GAIN_LOST_TRIGGER_PATTERNS` and `check_life_gain_lost_triggers()` exist in triggers.py but are NOT wired into the engine's `_lose_life()` flow. This story covers specifically the "life lost" side (CR 701.13) — distinct from "life gained" (CR 701.12).

### Comprehensive Rules Grounding
- **CR 701.13**: "If an effect causes a player to lose life, that player loses that much life."
- **Game event**: A player's life total decreases due to an effect
- **Example card**: *Bloodcaster* — "Whenever an opponent loses life, put a blood counter on ~."

## Acceptance Criteria
- [ ] Call `check_life_gain_lost_triggers(gs, player_name, "lose")` from stack.py's `_lose_life()` helper after life total is modified
- [ ] Capture return value (`gs = check_life_gain_lost_triggers(...)`)
- [ ] Integration tests: losing life fires trigger, gaining life fires separate Life Gained trigger, zero-net events fire both
- [ ] No regressions

## Dependencies
- None (wiring existing check function)

## Priority: High

## Estimated Effort: S

## Notes
- The existing combined check function handles both gain and loss — wire it in with a direction parameter
- Forge's trigger: `LifeLostTrigger` (separate from `LifeGainedTrigger`)

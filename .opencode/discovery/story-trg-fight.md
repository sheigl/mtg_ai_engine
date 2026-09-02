# Story: Fight Trigger (CR 701.6)

## User Story
As an MTG engine developer, I want fight triggers wired into the engine event flow, so that cards with "whenever this creature fights" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_fight_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into stack.py's `_apply_fight()` after damage is dealt during fight resolution.

### Comprehensive Rules Grounding
- **CR 701.6a**: "When creatures fight, each deals damage equal to its power to the other."
- **CR 701.6b**: "Neither creature deals damage if both creatures are tapped or have first strike or double strike and the other doesn't."
- Example card: *Duress* — "Target creature fights target creature."

## Acceptance Criteria
- [ ] Call `check_fight_triggers()` from stack.py's `_apply_fight()` after damage is dealt between both creatures
- [ ] Pass both fighter perm IDs to the check function
- [ ] Integration test: fight fires trigger on both creatures, non-fight damage does NOT fire fight trigger

## Dependencies
- None (uses existing check function; only adds call site)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- **Fight resolution wiring**: Fight is already partially implemented in stack.py's `_apply_fight()`. The trigger just needs to be queued at the same point where damage is dealt during fight resolution. Both creatures should have their "whenever this fights" triggers checked.

# Story: Transformed Trigger (CR 711.3)

## User Story
As an MTG engine developer, I want transformed triggers wired into the engine event flow, so that MDFC cards with "whenever this transforms" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_transformed_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into zones.py's `_transform_mdfc()` after a permanent flips sides.

### Comprehensive Rules Grounding
- **CR 711.3**: "A player may transform a permanent they control any time they have priority when that permanent is on the battlefield."
- **CR 711.4**: "Transforming a permanent means to turn it over so that the other face of the card is up."
- Example card: *The Walking Ballista* → *The Siege-Gang Commander* — transforms based on damage threshold

## Acceptance Criteria
- [ ] Call `check_transformed_triggers()` from zones.py's `_transform_mdfc()` after permanent flips sides
- [ ] Pass transformed perm ID to the check function
- [ ] Integration test: MDFC transform fires trigger, non-MDFC effects do NOT fire transformed trigger

## Dependencies
- None (uses existing check function; only adds call site)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- **Transform trigger wiring**: MDFC transform logic already exists in zones.py's `_transform_mdfc()`. The trigger just needs to be queued at the same point where the permanent flips sides. Check for "whenever this transforms" patterns on both faces of the MDFC (front face triggers before flip, back face triggers after).

# Story: Sacrifice Trigger (CR 701.19)

## User Story
As an MTG engine developer, I want sacrifice triggers wired into the engine event flow, so that cards with "whenever a creature is sacrificed" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_sacrifice_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This is dead code that needs wiring into zones.py when a permanent is sacrificed per CR 701.19.

### Comprehensive Rules Grounding
- **CR 701.19**: "To sacrifice a permanent, its controller moves it from the battlefield directly to its owner's graveyard."
- Example card: *Zulaport Cutthroat* — "Whenever Zulaport Cutthroat attacks, target creature gets -1/-1 until end of turn. Activate only any time you could cast an instant. Sacrifice target creature: Draw a card."

## Acceptance Criteria
- [ ] Call `check_sacrifice_triggers()` from zones.py's sacrifice path (when a permanent moves to graveyard via sacrifice action per CR 701.19)
- [ ] Pass sacrificed perm IDs and controller name to the check function
- [ ] Verify existing tests in `tests/engine/test_b1_missing_triggers.py` for sacrifice pass with wiring
- [ ] Integration test: sacrifice fires trigger, non-sacrifice death (destroy, exile) does NOT fire sacrifice trigger, self-referential guard ("whenever this is sacrificed")

## Dependencies
- None (uses existing check function; only adds call site)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- **Sacrifice detection**: The key challenge is distinguishing sacrifice from other death events in zones.py. Reference how `_queue_death_triggers()` already handles this — the zone change event includes a `reason` field that can be "sacrifice", "destroy", etc. Add a parallel call to `check_sacrifice_triggers()` when reason="sacrifice".

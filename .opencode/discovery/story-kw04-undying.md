# Story: Undying Death Trigger (CR 702.51)

## User Story
As a player, I want creatures with undying to return from the graveyard with +1/+1 counters equal to their power and toughness when they die without any +1/+1 counters, so that undying creatures can come back stronger.

## Context
Undying is a triggered ability: "When a creature with undying dies, if it had no +1/+1 counters on it, return it to the battlefield under its owner's control with a number of +1/+1 counters on it equal to its power and toughness." Story #4b implemented as a stack-based death trigger, replacing the previous inline zone-replacement logic.

### Comprehensive Rules Grounding
- **CR 702.51b**: "When a creature with undying dies, if it had no +1/+1 counters on it, return it to the battlefield under its owner's control with a number of +1/+1 counters on it equal to its power and toughness."
- **Example card**: Geralf's Messenger — "Undying (When this creature dies, if it had no +1/+1 counters on it, return it to the battlefield under its owner's control with a +1/+1 counter on it.)"

## Acceptance Criteria
- [x] Inline undying logic removed from `zones.py` — undying is now a proper stack-based trigger
- [x] Triggers wired into `_on_zone_change()` in `triggers.py` via `create_trigger()`
- [x] Trigger only fires if dying creature had NO +1/+1 counters at time of death
- [x] `resolve_trigger()` returns card from graveyard to battlefield with counters via pure `model_copy`
- [x] Counter count = power + toughness of the original creature
- [x] Returned permanent has summoning sickness (newly entering battlefield)
- [x] Trigger does NOT fire when creature is exiled
- [x] Self-referential guard: only the dying permanent's undying fires
- [x] Non-numeric power/toughness defaults to 0 counters
- [x] 16 integration tests pass in `tests/engine/test_undying_integration.py`

## Dependencies
- None (independent death trigger keyword)

## Priority: High

## Status: ✅ Complete

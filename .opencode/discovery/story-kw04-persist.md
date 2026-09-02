# Story: Persist Death Trigger (CR 702.61)

## User Story
As a player, I want creatures with persist to return from the graveyard with a -1/-1 counter when they die without any -1/-1 counters, so that persist creatures get a second life at the cost of reduced stats.

## Context
Persist is a triggered ability: "When a creature with persist dies, if it had no -1/-1 counters on it, return it to the battlefield under its owner's control with a -1/-1 counter on it." Story #4c implemented as a stack-based death trigger, replacing the previous inline zone-replacement logic.

### Comprehensive Rules Grounding
- **CR 702.61c**: "When a creature with persist dies, if it had no -1/-1 counters on it, return it to the battlefield under its owner's control with a -1/-1 counter on it."
- **Example card**: Kitchen Finks — "Persist (When this creature dies, if it had no -1/-1 counters on it, return it to the battlefield under its owner's control with a -1/-1 counter on it.)"

## Acceptance Criteria
- [x] Inline persist logic removed from `zones.py` — persist is now a proper stack-based trigger
- [x] Triggers wired into `_on_zone_change()` in `triggers.py` via `create_trigger()`
- [x] Trigger only fires if dying creature had NO -1/-1 counters at time of death
- [x] `resolve_trigger()` returns card from graveyard to battlefield with a -1/-1 counter via pure `model_copy`
- [x] Returned permanent has summoning sickness (newly entering battlefield)
- [x] If creature's base toughness minus -1/-1 counter would be ≤ 0, it still returns (SBA destroys later)
- [x] Trigger does NOT fire when creature is exiled
- [x] Self-referential guard: only the dying permanent's persist fires
- [x] 11 integration tests pass in `tests/engine/test_persist_integration.py`

## Dependencies
- None (independent death trigger keyword)

## Priority: High

## Status: ✅ Complete

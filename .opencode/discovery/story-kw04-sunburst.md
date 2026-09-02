# Story: Sunburst ETB Counter Effect (CR 702.103)

## User Story
As a player, I want permanents with sunburst to enter with counters equal to the number of colored mana symbols in their mana cost, so that multi-colored sunburst cards get more powerful the more colors are used to cast them.

## Context
Sunburst is an ETB effect: "As this permanent enters the battlefield, if it was cast, put a +1/+1 counter on it for each color of mana spent to cast it." For creatures, creates +1/+1 counters; for non-creatures, creates charge counters. Story #4d implemented with `apply_sunburst_counters()` wired into `put_permanent_onto_battlefield()`.

### Comprehensive Rules Grounding
- **CR 702.103b**: "As this permanent enters the battlefield, if it was cast, put a +1/+1 counter on it for each color of mana spent to cast it. For noncreature permanents, put a charge counter on it for each color instead."
- **Example card**: Arcbound Wanderer — "Sunburst (This enters the battlefield with a +1/+1 counter on it for each color of mana spent to cast it. If it wasn't cast, it enters with no counters.)"

## Acceptance Criteria
- [x] `apply_sunburst_counters()` applies counters via pure `model_copy` transform
- [x] Count = number of colored mana symbols ({W}, {U}, {B}, {R}, {G}) in mana cost
- [x] Creatures get +1/+1 counters; non-creatures get charge counters
- [x] Wired into `zones.py` `put_permanent_onto_battlefield()` — fires when `from_zone=="stack"` and `not is_token`
- [x] Does NOT fire for tokens or permanents not cast
- [x] Cards with no colored mana cost enter with 0 counters from sunburst
- [x] Generic/hybrid mana symbols handled correctly
- [x] 18 integration tests pass in `tests/engine/test_sunburst_integration.py`

## Dependencies
- None (independent ETB keyword)

## Priority: Medium

## Status: ✅ Complete

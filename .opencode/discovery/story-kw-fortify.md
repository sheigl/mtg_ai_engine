# Story: Fortify (CR 702.54a)

## User Story
As an MTG engine developer, I want a new fortify keyword module with real apply() and integration tests, so that Fortification cards work correctly in the engine.

## Context
No file exists for fortify. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.54a**: "Fortify is an activated ability. '{cost}: Attach this Fortification to target land you control. Fortify only as a sorcery.'"
- **CR 702.54b**: "A Fortification can fortify a land. The fortified land gets whatever bonuses the Fortification grants."
- **Example card**: Darksteel Garrison — "Fortify {1}{W} ({1}{W}: Attach this Fortification to target land you control. Fortify only as a sorcery. The fortified land gets +1/+1 and has vigilance.)"
- **Rule source**: Activated ability to attach to a land, similar to Equip but for lands

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/fortify.py` with `Fortify` class extending `KeywordAbility`
- [ ] `parse_fortify_cost(oracle_text) -> str | None` detects fortify cost
- [ ] `apply()` attaches the Fortification to a target land (similar to equip but for lands)
- [ ] Fortify cost is parsed (e.g., "Fortify {1}{W}" means cost is {1}{W})
- [ ] Restricted to sorcery speed
- [ ] Target must be a land controlled by the Fortification's controller
- [ ] Fortification grants bonuses defined in its oracle text (e.g., +1/+1, vigilance)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: fortify a land, cannot fortify creature, sorcery speed restriction, cost payment, multiple fortifications on same land, unattach when land leaves
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: High

## Estimated Effort: M

## Notes
- Mechanically identical to equip but targets lands instead of creatures
- Can reuse much of the Equip module implementation
- Darksteel Garrison is the most well-known Fortification
- Fortifications generally grant +1/+1 and vigilance to the fortified land
- The keyword is P0/High because it was separately identified as the most common missing mechanic

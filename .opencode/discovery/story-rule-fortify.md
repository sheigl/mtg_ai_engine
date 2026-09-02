# Story: Fortify (CR 702.54a)

## User Story
As a game engine developer, I want the Fortify mechanic to function correctly as a land-equivalent of Equip, so that Fortification cards can be attached to lands at sorcery speed per CR 702.54a.

## Context
Fortify is a keyword ability on Fortification cards (similar to how Equip works on Equipment). "Fortify [cost]" means "[cost]: Attach this permanent to target land you control. Activate only as a sorcery." Fortifications are a subtype of artifact that attach to lands. The mechanic is structurally identical to Equip but targets lands instead of creatures.

### Comprehensive Rules Grounding
- **CR 702.54a**: "Fortify is an activated ability of Fortification cards. 'Fortify [cost]' means '[cost]: Attach this Fortification to target land you control. Activate this ability only any time you could cast a sorcery.'"
- **CR 702.54b**: "A Fortification's fortify ability can't be activated if the Fortification is already attached to a land."
- **Example card**: Darksteel Garrison — "Fortify {2}" ("Fortified land has indestructible.")

## Acceptance Criteria
- [ ] Fortify cost detection: `parse_fortify_cost(oracle_text) -> str | None`
- [ ] Fortify activation: sorcery-speed, attach to target land you control
- [ ] Fortification can't be activated if already attached (CR 702.54b)
- [ ] Fortified land gains abilities/effects from the Fortification card
- [ ] AI auto-resolves: attaches to the land most likely to benefit from the fortification
- [ ] Human path: presents list of valid land targets for fortify activation
- [ ] Fortification on illegally attached (no longer a land) falls off
- [ ] Pure transform via `model_copy(update={...})`
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- This is a rule-level wrapper for the existing keyword story `story-kw-fortify.md`

## Priority: High

## Status: ❌ Not Implemented

### Gap Description
Fortify keyword is recognized in the ability parser keyword list but has zero implementation anywhere in the engine. There is no parse_fortify_cost() function, no fortify activation mechanism, no Fortification subtype handling, no attachment-to-lands logic, and no fortify keyword module.

## Estimated Effort: M

## Notes
- **This story is a rule-level companion to `story-kw-fortify.md`** — the keyword story covers the module implementation, while this story covers the CR 702.54a rules grounding
- Fortify is structurally identical to Equip (CR 702.6) but targets lands rather than creatures
- Fortification is a subtype, just as Equipment is a subtype of artifact
- Key difference: Equip targets creatures you control, Fortify targets lands you control
- If the fortified land stops being a land, the Fortification becomes illegally attached (similar to Aura/Equipment rules)
- Fortification bonuses generally grant abilities to the land (indestructible, mana abilities, etc.)

# Story: Fear (CR 702.24)

## User Story
As a game engine developer, I want creatures with fear to be blockable only by artifact creatures and/or black creatures, so that fear's blocking restriction works per CR 702.24.

## Context
Fear is a color-based blocking restriction keyword. A creature with fear can't be blocked except by artifact creatures and/or black creatures. Fear is effectively "protection from non-black, non-artifact creatures" for blocking purposes. Fear has been functionally replaced by intimidate in newer sets, but still works in older formats.

### Comprehensive Rules Grounding
- **CR 702.24a**: "Fear means this creature can't be blocked except by artifact creatures and/or black creatures."
- **CR 702.24b**: "Fear is a combat damage avoidance ability."
- **Example card**: Nirkana Revenant — "Fear"

## Acceptance Criteria
- [ ] `has_fear(perm) -> bool` detection
- [ ] Fear creature can't be blocked by non-black, non-artifact creatures
- [ ] Black creatures CAN block fear creatures (regardless of artifact status)
- [ ] Artifact creatures CAN block fear creatures (regardless of color)
- [ ] Black artifact creatures CAN block fear creatures
- [ ] Non-black, non-artifact creatures CANNOT block fear creatures
- [ ] Fear works on both offense and defense (a fear creature can block any creature, but can only be blocked by creatures matching the restriction)
- [ ] Colorless non-artifact creatures (e.g., tokens with no color) can't block fear creatures
- [ ] Integration tests cover: black blocker blocks fear, artifact blocker blocks fear, non-black non-artifact can't block, black artifact blocks fear, colorless non-artifact can't block
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone combat restriction keyword)

## Priority: Low

## Status: ❌ Not Implemented

### Gap Description
Fear keyword is recognized in the ability parser keyword list but has zero implementation anywhere in the engine. There is no has_fear() helper, no fear blocking restriction in declare_blockers(), no integration with combat validation, and no keyword module. Fear creatures have no special blocking restrictions.

## Estimated Effort: S

## Notes
- Fear was primarily in the original Mirrodin block and a few other sets
- Fear has been replaced by intimidate in newer sets (both are similar but intimidate checks color and artifact separately from color)
- Key difference from intimidate: fear specifically allows artifact creatures to block regardless of color; intimidate allows artifact creatures to block AND creatures that share a color
- Fear is slightly LESS restrictive than intimidate because artifact creatures can always block fear creatures
- The engine's blocking validation needs to check fear when determining legal blockers
- Black creatures can always block fear creatures because they share the color black
- Colorless artifact creatures can block fear creatures because they're artifact creatures

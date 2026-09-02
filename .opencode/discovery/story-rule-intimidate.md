# Story: Intimidate (CR 702.13)

## User Story
As a game engine developer, I want creatures with intimidate to be blockable only by artifact creatures and/or creatures that share a color, so that intimidate's blocking restriction works per CR 702.13.

## Context
Intimidate is a color-and-artifact-based blocking restriction keyword. A creature with intimidate can't be blocked except by artifact creatures and/or creatures that share a color with it. Intimidate functionally replaced fear (which allows artifact creatures and black creatures to block regardless of the blocked creature's color). Intimidate is a combat damage avoidance ability.

### Comprehensive Rules Grounding
- **CR 702.13a**: "Intimidate means this creature can't be blocked except by artifact creatures and/or creatures that share a color with it."
- **CR 702.13b**: "Intimidate is a combat damage avoidance ability."
- **Example card**: Phyrexian Crusader — "Intimidate" (also has protection from red and from white)

## Acceptance Criteria
- [ ] `has_intimidate(perm) -> bool` detection
- [ ] Intimidate creature can't be blocked by creatures that don't share a color and aren't artifacts
- [ ] Artifact creatures CAN block intimidate creatures (regardless of color)
- [ ] Creatures sharing at least one color with the intimidate creature CAN block
- [ ] Multicolored intimidate creatures can be blocked by creatures that share ANY of their colors
- [ ] Colorless creatures (not artifacts) can't block intimidate creatures
- [ ] Colorless artifact creatures CAN block intimidate creatures
- [ ] Intimidate works on both offense and defense
- [ ] Integration tests cover: same-color blocker blocks intimidate, artifact blocker blocks intimidate, different-color non-artifact can't block, colorless non-artifact can't block, multicolor intimidate
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone combat restriction keyword)

## Priority: Low

## Status: ❌ Not Implemented

### Gap Description
Intimidate keyword is recognized in the ability parser keyword list but has zero implementation anywhere in the engine. There is no has_intimidate() helper, no intimidate blocking restriction, no integration with combat validation, and no keyword module. Intimidate creatures have no special blocking restrictions.

## Estimated Effort: S

## Notes
- Intimidate is the functional replacement for fear (from Zendikar onward)
- Key difference from fear: intimidate checks the intimidate creature's OWN color(s), while fear checks only the blocker's color
- Intimidate is LESS restrictive than fear for same-color blockers but MORE restrictive for artifact creatures (fear allows ALL artifacts to block; intimidate allows ALL artifacts to block)
- Example: A black creature with intimidate can be blocked by black creatures (same color) or artifact creatures — same as fear
- Example: A green creature with intimidate can be blocked by green creatures — fear would NOT allow this (fear only allows black or artifact)
- The engine's blocking validation needs to check intimidate when determining legal blockers
- Intimidate is a "color matters" mechanic that has been phased out of modern sets (introduced in Zendikar, last in Amonkhet)

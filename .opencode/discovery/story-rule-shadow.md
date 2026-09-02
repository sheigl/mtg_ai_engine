# Story: Shadow (CR 702.27)

## User Story
As a game engine developer, I want shadow creatures to be able to block and be blocked only by other shadow creatures, so that shadow's combat restriction works per CR 702.27.

## Context
Shadow is a keyword ability that places a combat restriction on creatures. A creature with shadow can only be blocked by creatures with shadow. Similarly, a creature with shadow can only block creatures with shadow. Non-shadow creatures and shadow creatures effectively exist in separate combat "planes" — they can't interact directly in combat. Shadow was a primary mechanic in Tempest block.

### Comprehensive Rules Grounding
- **CR 702.27a**: "Shadow means this creature can block or be blocked only by creatures with shadow."
- **CR 702.27b**: "Shadow is a combat damage avoidance ability."
- **Example card**: Dauthi Slayer — "Shadow (This creature can't be blocked except by creatures with shadow.)"

## Acceptance Criteria
- [ ] `has_shadow(perm) -> bool` detection
- [ ] Shadow creatures can only be blocked by shadow creatures (declaration of blockers)
- [ ] Shadow creatures can only block other shadow creatures (declaration of blockers)
- [ ] Non-shadow creatures can't be blocked by shadow creatures
- [ ] Non-shadow creatures can't block shadow creatures
- [ ] Shadow works both ways: the blocking restriction applies in both directions
- [ ] Shadow interacts with flying (a creature with both shadow and flying has both restrictions)
- [ ] Creatures can have multiple combat restriction abilities (shadow + flying + horsemanship + fear — all apply independently)
- [ ] Integration tests cover: shadow blocks shadow, shadow blocks non-shadow (blocked), non-shadow blocks shadow (blocked), shadow attacker can't be blocked by non-shadow, shadow creature blocks shadow attacker
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone combat restriction keyword)

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Shadow blocking restriction is implemented in declare_blockers() (lines 342-347) - shadow creatures can only block/be blocked by shadow creatures. But missing: standalone keyword module, has_shadow() query helper, reach-equivalent handling, and comprehensive shadow integration tests.

## Estimated Effort: M

## Notes
- Shadow is functionally similar to horsemanship (also a blocking restriction) but flavored differently
- Shadow creatures and non-shadow creatures effectively fight in separate "shadow realm" — they can't interact in combat
- Shadow is a combat damage avoidance ability (like flying, horsemanship, intimidate, fear) — these all create blocking restrictions
- A creature with both shadow and flying must be blocked by a creature that has BOTH shadow and flying, OR by a creature with reach that also has shadow
- Shadow was last used in Time Spiral block (2006-2007) and Modern Horizons (2019)
- The engine's blocking validation needs to check shadow status when determining legal blockers

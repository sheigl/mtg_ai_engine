# Story: Horsemanship (CR 702.30)

## User Story
As a game engine developer, I want horsemanship to function as a blocking restriction equivalent to flying, so that creatures with horsemanship can be blocked only by creatures with horsemanship per CR 702.30.

## Context
Horsemanship is a keyword ability from the Portal: Three Kingdoms set (and featured in Masters sets). It provides a combat damage avoidance ability similar to flying — a creature with horsemanship can only be blocked by creatures with horsemanship. Unlike flying, there is no "reach" equivalent for horsemanship — only creatures with horsemanship can block creatures with horsemanship.

### Comprehensive Rules Grounding
- **CR 702.30a**: "Horsemanship means this creature can block or be blocked only by creatures with horsemanship."
- **CR 702.30b**: "Horsemanship is a combat damage avoidance ability."
- **Example card**: Sun Quan, Lord of Wu — "Horsemanship"

## Acceptance Criteria
- [ ] `has_horsemanship(perm) -> bool` detection
- [ ] Horsemanship creatures can only be blocked by horsemanship creatures
- [ ] Horsemanship creatures can only block horsemanship creatures
- [ ] Non-horsemanship creatures can't block horsemanship creatures
- [ ] Non-horsemanship creatures can't be blocked by horsemanship creatures
- [ ] There is NO "reach" equivalent for horsemanship (unlike flying)
- [ ] Horsemanship can stack with other combat restriction abilities (flying, shadow, etc.)
- [ ] Integration tests cover: horsemanship blocks only horsemanship, non-horsemanship can't block horsemanship, multiple combat restrictions
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone combat restriction keyword)

## Priority: Low

## Status: 🔄 Partial

### Gap Description
Basic horsemanship check exists in declare_blockers() (lines 350-352) - horsemanship creatures can only be blocked/block by horsemanship creatures. But missing: standalone keyword module, has_horsemanship() query helper, and comprehensive horsemanship integration tests.

## Estimated Effort: S

## Notes
- Horsemanship is mechanically identical to shadow in how blocking restrictions work
- The only functional difference from shadow is flavor and set context
- Unlike flying, there is no "horsemanship-reach" — the ONLY way to block a creature with horsemanship is with a creature that also has horsemanship
- Horsemanship is rare in Magic — it appears primarily on Portal: Three Kingdoms cards and some Masters set reprints
- The engine's blocking validation should treat horsemanship as a "blocking restriction" similar to flying

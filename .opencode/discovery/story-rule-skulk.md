# Story: Skulk (CR 702.120)

## User Story
As a game engine developer, I want creatures with skulk to be unblockable by creatures with greater power, so that skulk's power-based blocking restriction works per CR 702.120.

## Context
Skulk is a keyword ability from Shadows over Innistrad block. A creature with skulk can't be blocked by creatures with greater power. This means a 1/1 with skulk can't be blocked by a 2/2 (or any creature with power 2 or greater), but CAN be blocked by a 1/3 (same or lower power). Changes to a blocker's power after blocking is declared (e.g., by Giant Growth) still apply.

### Comprehensive Rules Grounding
- **CR 702.120a**: "Skulk means this creature can't be blocked by creatures with greater power."
- **CR 702.120b**: "Skulk is a combat damage avoidance ability."
- **Example card**: Kitesail Freebooter — "Skulk"

## Acceptance Criteria
- [ ] `has_skulk(perm) -> bool` detection
- [ ] Skulk creature can't be blocked by creatures with higher power
- [ ] Skulk creature CAN be blocked by creatures with equal or lower power
- [ ] Power comparison is checked at blocker declaration time
- [ ] Power changes after blocking is declared still apply (if blocker's power becomes greater than the skulk creature's power, the block is still legal — the restriction is checked at declaration time only)
- [ ] If the skulk creature's power changes after declaration, the block remains legal even if now unequal
- [ ] 0-power skulk creatures can't be blocked by any creature with power > 0
- [ ] Integration tests cover: same-power blocker, lower-power blocker, higher-power can't block, power change after declaration, 0-power skulk, pump spell on skulk creature after block declaration
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone combat restriction keyword)

## Priority: Low

## Status: ❌ Not Implemented

### Gap Description
Skulk keyword is recognized in the ability parser keyword list but has zero implementation anywhere in the engine. There is no has_skulk() helper, no skulk power-based blocking restriction, no integration with combat validation, and no keyword module. Skulk creatures have no special blocking restrictions.

## Estimated Effort: S

## Notes
- Skulk is a "power matters" mechanic that rewards small creatures
- Key timing: the blocking restriction is checked at blocker declaration time — if a creature with power 2 tries to block a 1/1 skulk, it's illegal
- However, if a creature with power 1 blocks a 1/1 skulk, then gets +2/+2 later, the block remains legal (was legal when declared)
- Skulk is similar in spirit to shadow (a combat damage avoidance ability) but based on power rather than keyword
- Skulk works well with pump spells that DON'T increase power (e.g., "toughness +0/+3") since the creature stays unblockable
- The engine's blocking validation should check skulk status when determining legal blockers

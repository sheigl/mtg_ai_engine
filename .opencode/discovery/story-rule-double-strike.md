# Story: Double Strike Timing (CR 702.4)

## User Story
As a game engine developer, I want double-strike creatures to deal damage in both the first-strike and regular combat damage steps, so that double strike timing works per CR 702.4.

## Context
Double strike causes a creature to deal its combat damage in both combat damage steps (first-strike and regular). During the first-strike combat damage step, creatures with first strike and double strike deal damage. During the regular combat damage step, creatures with double strike and creatures without first or double strike deal damage. A creature that gains double strike after the first-strike step (e.g., during first-strike damage) still deals damage in the regular step.

### Comprehensive Rules Grounding
- **CR 702.4a**: "Double strike means a creature deals both first-strike and regular combat damage."
- **CR 702.4b**: "If a creature has double strike but loses it before the first-strike damage step, it deals damage only during the regular combat damage step."
- **CR 702.4c**: "If a creature gains double strike after first-strike damage is dealt, it still deals regular combat damage."
- **CR 702.7**: "First strike creatures deal damage in the first-strike combat damage step."
- **Example card**: Embercleave — "Double strike" — creature deals damage twice

## Acceptance Criteria
- [x] `has_double_strike(perm) -> bool` detection
- [x] Double-strike creature deals damage in first-strike combat damage step
- [x] Double-strike creature ALSO deals damage in regular combat damage step
- [x] If double-strike creature loses double strike before first-strike step, it only deals regular damage
- [x] If double-strike creature gains double strike after first-strike step, it still deals regular damage
- [x] Double-strike creature blocked by a creature with first strike: both deal damage in first-strike step; only the double-striker deals damage in regular step
- [x] Damage marking: damage from first-strike step is marked on both creatures; SBAs check after each damage step
- [x] If a creature dies in first-strike step from the double-striker's damage, the double-striker has no blocker in regular step — its regular damage goes unblocked (to the defending player if it has trample, or it deals no damage without trample)
- [x] Integration tests cover: double strike both steps, double strike vs first strike (blocker dies in first strike), double strike loses ability, double strike gains ability after first strike, double strike + trample
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: First Strike Timing (CR 702.7) — double strike uses the first-strike combat damage step
- Story: Trample Damage Assignment (CR 702.19) — trample + double strike interactions

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- Double strike is effectively "first strike + strikes again in regular damage step"
- The two combat damage steps are separate rounds of damage dealing — SBAs are checked BETWEEN them
- This means a creature can die from first-strike damage before it gets to deal its regular damage
- Trample + double strike: excess damage from FIRST-STRIKE trample goes to player; then in regular damage step, the full power is dealt again (since SBAs between steps destroy blockers, leaving no blocker for regular damage)
- Key timing: effects that trigger on damage are triggered AFTER each combat damage step (not after both)
- Double strike DOES stack with first strike — having both is redundant (double strike already includes first strike)

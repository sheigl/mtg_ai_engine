# Story: First Strike Timing (CR 702.7)

## User Story
As a game engine developer, I want first-strike creatures to deal damage before non-first-strike creatures in the first-strike combat damage step, so that first-strike timing works per CR 702.7.

## Context
First strike causes a creature to deal combat damage in the first-strike combat damage step, which occurs before the regular combat damage step. Creatures without first strike (or double strike) deal damage only in the regular step. If no creatures have first or double strike, the first-strike step is skipped entirely.

### Comprehensive Rules Grounding
- **CR 702.7a**: "First strike means a creature deals combat damage before creatures without first strike."
- **CR 702.7b**: "During the first-strike combat damage step, only creatures with first strike and double strike deal damage."
- **CR 702.7c**: "After the first-strike damage step, if no creatures have first or double strike, proceed to the regular damage step."
- **CR 704.3**: "State-based actions are checked after each combat damage step."
- **Example card**: Elite Vanguard — "First strike" — deals damage before most other creatures

## Acceptance Criteria
- [x] `has_first_strike(perm) -> bool` detection
- [x] If any creature has first strike or double strike, a first-strike combat damage step occurs
- [x] First-strike creatures deal damage in the first-strike combat damage step
- [x] Non-first-strike creatures (without double strike) do NOT deal damage in the first-strike step
- [x] Non-first-strike creatures deal damage in the regular combat damage step
- [x] If no creatures have first strike or double strike, the first-strike step is skipped
- [x] SBAs are checked between first-strike and regular combat damage steps
- [x] A creature that dies from first-strike damage doesn't deal regular damage
- [x] Integration tests cover: first strike vs non-first strike, first strike kills blocker before it can deal damage, first strike step is skipped when no first-strike creatures, first strike + double strike both deal damage in first-strike step
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Double Strike Timing (CR 702.4) — double strike also deals damage in the first-strike step
- Story: State-Based Actions (CR 704) — SBAs between combat damage steps

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- First strike is one of the most iconic and common keyword abilities
- The first-strike combat damage step is distinct from the regular combat damage step — they are two separate phases for SBA checking
- Key combat flow: Declare Blockers → First-Strike Damage step → SBA check → Regular Damage step → SBA check → End of Combat
- A creature with first strike that trades with a non-first-strike creature: the first striker deals damage and kills the non-first-striker, but the non-first-striker's damage is NOT dealt (it died in the first-strike step)
- First strike does NOT stack with double strike (double strike already includes first strike)
- Creatures that gain first strike after the first-strike damage step (e.g., a "creature gets first strike until end of turn" effect during the first-strike step) do NOT deal damage retroactively

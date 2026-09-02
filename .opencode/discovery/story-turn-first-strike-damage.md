# Story: First Strike / Double Strike Damage Step (CR 510.4)

## User Story
As a game engine developer, I want the first strike and double strike combat damage step to function correctly per CR 510.4, so that creatures with first strike or double strike deal their combat damage before regular combat damage creatures.

## Context
If at least one attacking or blocking creature has first strike or double strike, a combat damage step occurs before the regular combat damage step. During this step, creatures with first strike and double strike deal combat damage. Double strike creatures also deal damage in the regular combat damage step. The current engine has first strike damage logic in `begin_step()` at `turn_manager.py` line 353-363, which calls `assign_combat_damage(game_state, first_strike_only=True)`.

### Comprehensive Rules Grounding
- **CR 510.4**: "If at least one attacking or blocking creature has first strike or double strike, a combat damage step occurs before the regular combat damage step."
- **CR 702.7b**: "First strike means a creature deals combat damage before creatures without first strike."
- **CR 702.4b**: "Double strike allows a creature to deal both first-strike and regular combat damage."
- **Purpose**: First strike creatures deal damage before regular combat damage creatures

## Acceptance Criteria
- [x] First strike damage step only occurs if at least one creature has first strike or double strike
- [x] Creatures with first strike deal their combat damage during this step
- [x] Creatures with double strike deal their combat damage during this step
- [x] Creatures without first strike or double strike deal NO damage during this step
- [x] State-based actions are checked after first strike damage resolves
- [x] Priority is granted to active player after first strike damage resolves
- [x] Combat damage assignment rules (trample, deathtouch, lifelink, infect) apply here too
- [x] Full regression passes

## Dependencies
- story-turn-declare-blockers.md (Declare Blockers Step)

## Status: ✅ Complete

Implemented: `Step.FIRST_STRIKE_DAMAGE` at `turn_manager.py:101`. `begin_step()` handler at `turn_manager.py:353-363` calls `assign_combat_damage(gs, first_strike_only=True)`. `has_first_strike_combatants()` at `combat/core.py:766-778`. Auto-skip if no first/double strike creatures.

## Priority: High

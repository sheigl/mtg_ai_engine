# Story: End of Combat Step (CR 511)

## User Story
As a game engine developer, I want the end of combat step to function correctly per CR 511, so that "at end of combat" triggers fire and creatures are removed from combat.

## Context
The end of combat step is the last step of the combat phase. "At end of combat" and "whenever a creature deals combat damage" triggered abilities that trigger here are put onto the stack. All attacking, blocking, and blocked creatures are removed from combat at this time. The current engine has `end_combat()` called from `advance_step()` at `turn_manager.py` line 436-438, which is invoked when leaving the End of Combat step.

### Comprehensive Rules Grounding
- **CR 511.1**: "The end of combat step is the last step of the combat phase."
- **CR 511.2**: "Abilities that trigger 'at end of combat' trigger here."
- **CR 511.3**: "When the end of combat step ends, all creatures are removed from combat."
- **Purpose**: Clean up combat state; fire end-of-combat triggers

## Acceptance Criteria
- [x] End of combat step occurs after combat damage step(s)
- [x] "At end of combat" triggered abilities fire and are queued as pending triggers
- [x] Attackers, blockers, and blocked creatures are removed from combat status
- [x] "Until end of combat" effects expire after this step
- [x] Priority is granted to active player
- [x] `end_combat()` is called from `advance_step()` when transitioning out of end-of-combat step
- [x] Full regression passes

## Dependencies
- story-turn-combat-damage.md (Combat Damage Step)

## Status: ✅ Complete

Implemented: `Step.END_OF_COMBAT` at `turn_manager.py:103`. `end_combat()` called on exit at `turn_manager.py:436-438` sets `game_state.combat = None`.

## Priority: High

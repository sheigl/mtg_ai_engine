# Story: Combat Phase (CR 506)

## User Story
As a game engine developer, I want the combat phase to function correctly per CR 506, so that creatures attack, blockers are declared, and combat damage is dealt in the correct sequence.

## Context
The combat phase consists of five steps: beginning of combat, declare attackers, declare blockers, combat damage (first strike/double strike step if applicable, then regular combat damage), and end of combat. The current engine supports `TURN_SEQUENCE` with `Phase.COMBAT` and six steps: `BEGINNING_OF_COMBAT`, `DECLARE_ATTACKERS`, `DECLARE_BLOCKERS`, `FIRST_STRIKE_DAMAGE`, `COMBAT_DAMAGE`, `END_OF_COMBAT`. Combat does not necessarily happen every turn — the active player chooses whether to attack.

### Comprehensive Rules Grounding
- **CR 506.1**: "The combat phase consists of five steps: declare attackers, declare blockers, first strike combat damage, combat damage, and end of combat." *(Note: Beginning of Combat is also a step per CR 507)*
- **CR 506.2**: "Some effects refer to 'the beginning of combat' or 'at the beginning of combat.'"
- **Purpose**: Handle all combat-related actions — attacking, blocking, damage assignment

## Acceptance Criteria
- [x] Combat phase steps execute in correct order: Beginning of Combat → Declare Attackers → Declare Blockers → Combat Damage(s) → End of Combat
- [x] Beginning of Combat step fires "at beginning of combat" triggers
- [x] Active player chooses whether to declare attackers (combat is optional)
- [x] Active player receives priority at the beginning of each step
- [x] Combat damage step(s) deal damage correctly (first strike step only if creatures with first strike/double strike exist)
- [x] End of Combat step fires "at end of combat" triggers and clears combat state
- [x] Full regression passes

## Dependencies
- story-turn-main-phase.md (Main Phase)
- story-turn-declare-attackers.md, story-turn-declare-blockers.md, story-turn-combat-damage.md, etc.

## Status: ✅ Complete

Implemented: `Phase.COMBAT` at `models/game.py:25` with 6 steps in `TURN_SEQUENCE` (`turn_manager.py:98-103`). Full combat module at `mtg_engine/engine/combat/core.py` with declare attackers, blockers, damage assignment, first strike handling, and end of combat.

## Priority: High

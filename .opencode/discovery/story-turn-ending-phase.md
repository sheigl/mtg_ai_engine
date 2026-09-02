# Story: Ending Phase (CR 512)

## User Story
As a game engine developer, I want the ending phase to function correctly per CR 512, so that each turn correctly transitions through the end step and cleanup step.

## Context
The ending phase is the final phase of each turn. It consists of two steps: the end step and the cleanup step. "At end of turn" effects expire during this phase. The current engine supports `Phase.ENDING` in `TURN_SEQUENCE` with `Step.END` and `Step.CLEANUP`.

### Comprehensive Rules Grounding
- **CR 512.1**: "The ending phase consists of two steps: end step and cleanup step."
- **Purpose**: Handle end-of-turn triggers, discard to hand size, and damage removal

## Acceptance Criteria
- [x] Ending phase occurs after postcombat main phase
- [x] End step runs first, then cleanup step
- [x] End step fires "at the beginning of the end step" triggers
- [x] Cleanup step handles discard to hand size and damage removal
- [x] After cleanup step, the turn ends and the next player's turn begins
- [x] "Until end of turn" effects expire during cleanup step
- [x] Full regression passes

## Dependencies
- story-turn-combat-phase.md (Combat Phase)
- story-turn-main-phase.md (Main Phase)

## Status: ✅ Complete

Implemented: `Phase.ENDING` at `models/game.py:27` with two steps: END and CLEANUP at `turn_manager.py:105-106`.

## Priority: High

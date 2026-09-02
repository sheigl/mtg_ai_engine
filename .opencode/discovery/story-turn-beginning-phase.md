# Story: Beginning Phase (CR 500.1)

## User Story
As a game engine developer, I want the beginning phase to function correctly per the Comprehensive Rules, so that each turn starts with the correct sequence of untap, upkeep, and draw steps.

## Context
The beginning phase is the first phase of each turn. It consists of three steps in order: untap, upkeep, and draw. This phase sets the stage for the turn's main phase. The current engine already has `TURN_SEQUENCE` defined in `turn_manager.py` with these three steps within `Phase.BEGINNING`, and `_advance_turn()` resets the game state to `(Phase.BEGINNING, Step.UNTAP)` at the start of each turn.

### Comprehensive Rules Grounding
- **CR 500.1**: "The beginning phase consists of three steps: untap, upkeep, and draw."
- **Purpose**: Establishes the mandatory starting steps of every turn

## Acceptance Criteria
- [x] `TURN_SEQUENCE` correctly includes Beginning phase with Untap, Upkeep, and Draw steps in order (turn_manager.py:94-96)
- [x] `_advance_turn()` transitions to `(Phase.BEGINNING, Step.UNTAP)` at turn start (turn_manager.py:547-548)
- [x] Beginning phase steps execute fully before transitioning to precombat main phase
- [x] Skip-empty-phases feature (Feature 029) respects beginning phase step ordering
- [x] Full regression passes

## Dependencies
- None

## Status: ✅ Complete

Implemented: `Phase.BEGINNING` in `models/game.py:23`, three steps (UNTAP, UPKEEP, DRAW) in `TURN_SEQUENCE` at `turn_manager.py:94-96`, `_advance_turn()` transitions to beginning phase at `turn_manager.py:547-548`.

## Priority: High

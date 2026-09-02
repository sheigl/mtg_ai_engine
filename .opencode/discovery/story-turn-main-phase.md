# Story: Main Phase (CR 505)

## User Story
As a game engine developer, I want the main phase to function correctly per CR 505, so that players can cast sorcery-speed spells, activate abilities, and play lands during their main phases.

## Context
There are two main phases each turn: the precombat main phase (after the draw step) and the postcombat main phase (after combat). During a main phase, the active player may cast sorcery-speed spells, activate abilities (unless they are instant-speed), and play one land. The current engine supports `Phase.PRECOMBAT_MAIN` and `Phase.POSTCOMBAT_MAIN` in `TURN_SEQUENCE`, both with `Step.MAIN`. Priority is granted to the active player at the start of each main phase.

### Comprehensive Rules Grounding
- **CR 505.1**: "A player can cast spells, activate abilities, and play lands during their main phase. There are two main phases each turn."
- **CR 505.2**: "The precombat main phase comes after the draw step. The postcombat main phase comes after the combat phase."
- **CR 505.4**: "Sorceries can only be cast during a main phase when the stack is empty."
- **Purpose**: Primary timing for sorcery-speed actions, land plays, and strategic decision-making

## Acceptance Criteria
- [x] Precombat main phase occurs after draw step and before combat phase
- [x] Postcombat main phase occurs after end of combat and before ending phase
- [x] Active player receives priority at start of each main phase
- [x] Sorcery-speed spells are legal to cast during main phase with empty stack
- [x] Active player may play up to one land during their main phase
- [x] Activate abilities (non-instant speed) are legal during main phase
- [x] Instant-speed spells/abilities remain legal during main phase
- [x] Empty stack check for sorceries is enforced
- [x] Full regression passes

## Dependencies
- story-turn-draw-step.md (Draw Step)

## Status: ✅ Complete

Implemented: `Phase.PRECOMBAT_MAIN` and `Phase.POSTCOMBAT_MAIN` at `models/game.py:24-26`. Sorcery-speed casting validated via `_can_cast_at_sorcery_speed()` at `stack.py:41-51`. Legal actions include cast, activate, play land during main phase.

## Priority: High

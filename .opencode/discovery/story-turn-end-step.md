# Story: End Step (CR 513)

## User Story
As a game engine developer, I want the end step to function correctly per CR 513, so that "at the beginning of the end step" and "until end of turn" effects resolve at the correct time.

## Context
The end step is the first step of the ending phase. "At the beginning of the end step" and "at the end of turn" triggered abilities fire during this step. Delayed triggers that specify "at the beginning of the next end step" also fire here. The Monarch end-step draw (CR 702.147, MON-01) and Evoke sacrifice (CR 702.74, SA-04) are handled in this step. The current engine has end step logic in `begin_step()` at `turn_manager.py` line 405-413 for Monarch draw and Evoke sacrifice resolution.

### Comprehensive Rules Grounding
- **CR 513.1**: "The end step is the first step of the ending phase. 'At the beginning of the end step' and 'at the end of turn' triggers fire here."
- **CR 513.2**: "'Until end of turn' effects expire at the cleanup step, not the end step."
- **Purpose**: Fire end-of-turn triggers; resolve delayed end-step effects

## Acceptance Criteria
- [x] "At the beginning of the end step" triggered abilities fire and are queued as pending triggers
- [x] "At the end of turn" triggered abilities fire and are queued as pending triggers
- [x] "At the beginning of the next end step" delayed triggers fire (CR 603.7)
- [x] Monarch draw fires: if active player is monarch, they draw a card
- [x] Evoke sacrifice fires: creatures with evoke are sacrificed if evoke cost wasn't paid
- [x] Dash creatures return to owner's hand at end step
- [x] Discard step of cleanup is NOT part of the end step
- [x] Priority is granted to active player
- [x] Full regression passes

## Dependencies
- story-turn-ending-phase.md (Ending Phase)
- story-gm-monarch.md (Monarch)
- story-gm-venture.md (Venture/Dungeon)

## Status: ✅ Complete

Implemented: `begin_step()` END handler at `turn_manager.py:377-419` — delayed triggers, monarch draw (MON-01), evoke sacrifice (SA-04), mana pool clearing.

## Priority: High

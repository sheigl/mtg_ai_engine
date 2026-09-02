# Story: Upkeep Step (CR 503)

## User Story
As a game engine developer, I want the upkeep step to function correctly per CR 503, so that "at the beginning of your upkeep" triggers fire and cumulative upkeep costs are paid at the correct time.

## Context
The upkeep step is the second step of the beginning phase. This is the first step where players receive priority. All "at the beginning of your upkeep" triggered abilities are put onto the stack. The current engine already has substantial upkeep logic in `begin_step()` at `turn_manager.py` line 167-318: suspend time counter removal (CR 702.62), Fading counter removal (CR 702.67), Saga lore counter increment (CR 715), Echo payment check (CR 702.28), and Initiative venturing into Undercity (INT-01). Priority is granted to the active player after begin_step completes for this step.

### Comprehensive Rules Grounding
- **CR 503.1**: "The upkeep step is the second step of the beginning phase. The active player receives priority."
- **CR 503.2**: "Abilities that trigger 'at the beginning of your upkeep' trigger here."
- **Purpose**: Resolve upkeep-triggered abilities; grant first priority of the turn

## Acceptance Criteria
- [x] Active player receives priority at start of upkeep step
- [x] "At the beginning of your upkeep" triggered abilities are queued as pending triggers
- [x] Suspend time counters are removed (one per upkeep per suspended card)
- [x] Fading creatures lose one fade counter; sacrificed when last counter removed
- [x] Saga lore counters are incremented and chapter abilities triggered
- [x] Echo payment check fires for echo permanents
- [x] Initiative holder ventures into Undercity dungeon (if applicable)
- [x] Priority passes correctly when all triggers resolve
- [x] Full regression passes

## Dependencies
- story-turn-untap-step.md (Untap Step)

## Status: ✅ Complete

Implemented: `begin_step()` UPKEEP handler at `turn_manager.py:167-318` — suspended card time counter removal, fading, saga lore counters, echo payment, initiative venture. Priority granted during upkeep.

## Priority: High

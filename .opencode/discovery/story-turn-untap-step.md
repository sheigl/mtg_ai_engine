# Story: Untap Step (CR 502)

## User Story
As a game engine developer, I want the untap step to function correctly per CR 502, so that the active player untaps all their permanents at the start of each turn.

## Context
The untap step is the first step of the beginning phase. During this step, the active player untaps all permanents they control. No player receives priority during this step — triggered abilities that would trigger during the untap step are put onto the stack at the next time a player would receive priority (typically the upkeep step). The current engine already has untap logic in `begin_step()` at `turn_manager.py` line 127-165, which iterates the battlefield and sets `tapped=False`, `summoning_sick=False`, and `loyalty_activated_this_turn=False` for the active player's permanents. Day/night transition checks (CR 730.2) also occur here.

### Comprehensive Rules Grounding
- **CR 502.1**: "The untap step is the first step of the beginning phase. The active player untaps all permanents they control."
- **CR 502.2**: "No player receives priority during the untap step. Any abilities that trigger at the beginning of the untap step are put onto the stack the next time a player would receive priority."
- **Purpose**: Refresh permanents for the new turn; clear summoning sickness; track day/night transition

## Acceptance Criteria
- [x] Active player's permanents are untapped (`tapped=False`) during untap step (turn_manager.py:127-165)
- [x] Active player's creatures lose summoning sickness (`summoning_sick=False`)
- [x] `lands_played_this_turn` is reset to 0 for active player
- [x] `loyalty_activated_this_turn` is reset to false for active player
- [x] Non-active player's permanents are NOT untapped
- [x] `priority_holder` is NOT set during untap step (no priority granted)
- [x] Mana pools are NOT cleared during untap step
- [x] Day/night transition check fires (CR 730.2) after untapping
- [x] Phasing in/out happens before untapping (CR 702.26b) — deferred to phasing story
- [x] Full regression passes

## Dependencies
- story-turn-beginning-phase.md (Beginning Phase)

## Status: ✅ Complete

Implemented: `begin_step()` UNTAP handler at `turn_manager.py:127-165` — untaps permanents, resets summoning sickness and loyalty, resets land count, checks day/night transition. No priority granted during untap step (`turn_manager.py:519`).

## Priority: High

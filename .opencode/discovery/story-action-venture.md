# Story: Venture into the Dungeon (CR 701.61)

## User Story
As a game engine developer, I want the venture into the dungeon action to function correctly per the Comprehensive Rules, so that players can start dungeons, advance through rooms, and complete dungeons for their rewards.

## Context
This game action is already fully documented under the game mechanic story `story-gm-venture.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 701.61**: "To venture into the dungeon, the player who controls the dungeon (or who starts a new dungeon) moves to the next room."
- **CR 701.61a**: A player may start a new dungeon if they don't have one in progress
- **CR 701.61b**: Venturing advances to the next room and triggers the room's ability
- **CR 701.61c**: When the last room is completed, the dungeon is completed and a new one may be started
- **Example card**: Varis, Silverymoon Ranger — "Whenever you cast a creature spell, venture into the dungeon."

## Acceptance Criteria
- [x] See `story-gm-venture.md` for full acceptance criteria
- [x] The action "venture into the dungeon" creates/increments dungeon progress per CR 701.61
- [x] Room abilities fire through the stack
- [x] Dungeon completion increments `player_completed_dungeons` counter

## Dependencies
- story-gm-venture.md (full game mechanic story)
- Trigger system (completed dungeon triggers)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

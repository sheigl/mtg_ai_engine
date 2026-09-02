# Story: Priority System (CR 117)

## User Story
As a game engine developer, I want the priority system to function correctly per CR 117, so that players can cast spells and activate abilities only when they have priority, and the game advances through steps and phases correctly when all players pass.

## Context
Priority is the system that controls when players may act. The active player receives priority at the start of most steps and phases (except untap step). When a player has priority, they may cast spells, activate abilities, or take special actions. When they pass priority, it goes to the next player in turn order. If all players pass in succession and the stack is non-empty, the top object resolves. If all players pass in succession and the stack is empty, the current step/phase ends and the game advances. The current engine has priority logic in `pass_priority()` and `advance_step()` at `turn_manager.py`.

### Comprehensive Rules Grounding
- **CR 117.1**: "A player may cast spells and activate abilities when they have priority."
- **CR 117.3b**: "The active player receives priority at the beginning of most steps and phases."
- **CR 117.4**: "If all players pass in succession, the top object on the stack resolves."
- **CR 117.5**: "If all players pass in succession and the stack is empty, the current step or phase ends."
- **Purpose**: Control turn progression and ensure fair opportunity to respond

## Acceptance Criteria
- [x] Active player receives priority at start of each step/phase (except untap step)
- [x] Priority passes from active player to non-active player in two-player games
- [x] When a player passes priority with a non-empty stack, the next player receives priority
- [x] When all players pass with a non-empty stack, the top stack object resolves
- [x] When all players pass with an empty stack, the current step/phase ends and game advances
- [x] Players may cast instants and activate abilities at instant speed when they have priority
- [x] Sorcery-speed spells are only legal during main phase with empty stack
- [x] Auto-pass (Feature 029) correctly skips players with only pass actions available
- [x] Full regression passes

## Dependencies
- All step/phase stories (priority grants at each step)

## Status: ✅ Complete

Implemented: `pass_priority()` at `turn_manager.py:651-695` handles stack/non-stack priority passing. Priority granted each step except UNTAP at `turn_manager.py:519-520`. Auto-pass for AI with no valid actions (Feature 029). Split-second restriction at `stack.py:17-25`.

## Priority: High

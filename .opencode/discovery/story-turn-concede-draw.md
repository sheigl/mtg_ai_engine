# Story: Conceding / Drawing the Game (CR 104)

## User Story
As a game engine developer, I want the concede and draw game rules to function correctly per CR 104, so that players can concede at any time and simultaneous win/loss conditions result in a draw.

## Context
A player may concede a game at any time — this is a game action that does not use the stack and cannot be responded to. When a player concedes, all of their permanents leave the game and their opponent wins. If all of a player's opponents have conceded, that player wins the game. The game is a draw if all remaining players would simultaneously lose or if a player would both win and lose simultaneously. These rules govern game termination beyond normal loss conditions (life total reaching 0, decking, poison counters, commander damage, etc.).

### Comprehensive Rules Grounding
- **CR 104.2**: "A player may concede a game at any time. The opponent wins the game."
- **CR 104.3**: "If a player's opponent has conceded, that player wins the game."
- **CR 104.4**: "If a player would both win and lose simultaneously, the game is a draw."
- **CR 104.5**: "If all players remaining in the game would lose simultaneously, the game is a draw."
- **Purpose**: Allow graceful game termination; handle edge cases where multiple win/loss events occur simultaneously

## Acceptance Criteria
- [ ] Player can concede at any time (even during opponent's turn, during combat, etc.)
- [ ] Conceding does not use the stack and cannot be responded to
- [ ] When a player concedes, all their permanents leave the game
- [ ] Conceding player's opponent is declared the winner
- [ ] If both players would lose simultaneously, the game is a draw
- [ ] If a player would both win and lose simultaneously, the game is a draw
- [ ] Game's `is_game_over` flag is set correctly for all concede/draw scenarios
- [ ] Game winner is recorded in game state
- [ ] Full regression passes

## Dependencies
- None

## Status: ⏳ Not Implemented

Not implemented: `PlayerActionType.CONCEDE` enum exists at `player_actions.py:34` and `GameOutcome` supports draw/concede scenarios (`export/outcome.py:9-10`), but there is **no API endpoint** for conceding, **no legal action** offering concede to the player, and **no concede handler** in any game action endpoint.

## Priority: High

## Estimated Effort: M

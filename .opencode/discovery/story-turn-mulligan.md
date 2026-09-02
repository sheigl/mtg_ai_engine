# Story: Mulligan Rules (CR 103.4)

## User Story
As a game engine developer, I want the London mulligan system to function correctly per CR 103.4, so that players can take mulligans before the game starts, following modern tournament rules.

## Context
Before the game begins, each player is dealt a starting hand of 7 cards. If a player is not satisfied with their hand, they may take a mulligan. The current recommended system is the "London mulligan": shuffle your hand back into the library, then draw one fewer card than before. Once a player chooses to keep a hand of fewer than 7 cards, they scry 1 (look at the top card of their library and either keep it or put it on the bottom). This process is completely separate from the game's turn structure but is an essential pre-game procedure. The current engine does not appear to have mulligan logic.

### Comprehensive Rules Grounding
- **CR 103.4**: "Each player may take a mulligan. The current recommended mulligan system is the 'London' mulligan."
- **CR 103.4a**: "First, the starting player decides to take a mulligan or keep their hand. Then each other player in turn order does the same."
- **CR 103.4b**: "To take a mulligan, a player shuffles their hand back into their library and draws a new hand of one fewer card."
- **CR 103.4c**: "After taking a mulligan, a player may take additional mulligans."
- **CR 103.4d**: "When a player keeps a hand with fewer than 7 cards, they scry 1."
- **Purpose**: Allow players to reject unplayable opening hands with a strategic cost (fewer cards)

## Acceptance Criteria
- [x] Players may choose to take a mulligan before the game starts
- [x] London mulligan: shuffle hand back into library, draw new hand of N-1 cards
- [x] In multiplayer, mulligan decisions happen in turn order (starting player first)
- [x] Players may take multiple consecutive mulligans
- [x] When keeping a hand of fewer than 7 cards, the player scrys 1
- [x] Scry 1 happens after all players have decided to keep their hands
- [x] Players cannot mulligan to fewer than 0 cards (must keep a hand of 0)
- [x] Full regression passes

## Dependencies
- None (pre-game procedure)

## Status: ✅ Complete

Implemented: `apply_mulligan()` at `mulligan.py:29-67` with 4 variants (London, Vancouver, Paris, Original). `POST /game/{game_id}/mulligan` endpoint at `game.py:2214-2250`. Legal actions at `game.py:2335-2351`. Vancouver scry on keep at `mulligan.py:90-98`.

## Priority: High

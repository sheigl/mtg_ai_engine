# Story: Companion Restrictions (CR 903.5)

## User Story
As a game engine developer, I want companion restrictions to function correctly per the Comprehensive Rules, so that players can pay {3} to put a companion from the sideboard into their hand if their deck meets the companion's restriction.

## Context
This game action is already fully documented under the game mechanic story `story-gm-companion.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 903.5a**: "Each player may designate one legendary creature as their companion if their starting deck meets its companion restriction."
- **CR 903.5b**: "During the game, a player may pay {3} to move their companion from the sideboard to their hand."
- **CR 903.5c**: "This is a special action that can be taken any time the player could cast an instant."
- **Example card**: Lurrus of the Dream-Den — "Companion — Each permanent card in your starting deck has mana value 2 or less."

## Acceptance Criteria
- [x] See `story-gm-companion.md` for full acceptance criteria
- [x] Deck validation checks companion restriction before game start
- [x] In-game special action: pay {3} to move companion from sideboard to hand
- [x] Can only be done any time the player could cast an instant

## Dependencies
- story-gm-companion.md (full game mechanic story)
- story-gm-commander.md (structure parallels)

## Priority: Medium
## Status: ✅ Complete

## Estimated Effort: S

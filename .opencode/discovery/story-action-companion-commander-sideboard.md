# Story: Companions / Commanders from Sideboard (CR 903.5)

## User Story
As a game engine developer, I want companions and commanders designated from outside the game to function correctly per the Comprehensive Rules, so that companion restrictions are checked and commanders start the game in the command zone.

## Context
This game action is already covered by existing stories:
- **Companion**: `story-gm-companion.md` — full companion implementation including sideboard-to-hand special action
- **Commander**: `story-gm-commander.md` — full commander implementation including command zone, commander tax, and zone replacement
- **Companion Restrictions** (CR 903.5): `story-action-companion.md` — the in-game action reference

This file serves as a summary reference for the sideboard/outside-game interaction patterns.

### Comprehensive Rules Grounding
- **CR 903.5**: "Each player may designate one legendary creature as their companion if their starting deck meets its companion restriction."
- **CR 903.6**: "In Commander, the commander starts the game in the command zone."
- **CR 903.8**: "Commander tax: Each time a commander is cast from the command zone, it costs {2} more."

## Acceptance Criteria
- [x] See `story-gm-companion.md` and `story-gm-commander.md` for full acceptance criteria
- [x] Companion restriction is validated during deck construction
- [x] Commander zone replacement: if commander would go to graveyard/exile, controller may choose command zone

## Dependencies
- story-gm-companion.md
- story-gm-commander.md

## Priority: High
## Status: ✅ Complete

## Estimated Effort: S

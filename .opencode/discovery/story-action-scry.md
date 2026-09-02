# Story: Scry (CR 701.20)

## User Story
As a game engine developer, I want the scry action to function correctly per the Comprehensive Rules, so that players can look at the top N cards of their library and arrange them by putting any number on the bottom and the rest on top in any order.

## Context
This game action is already fully documented under the keyword story `story-kw-scry.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 701.20a**: "To scry N, look at the top N cards of your library. Put any number of them on the bottom of your library in any order and the rest on top in any order."
- **CR 701.20b**: "If a player is instructed to scry, then an ability triggers 'whenever you scry,' that ability triggers after the player finishes scrying."
- **CR 701.20c**: "Scry is different from surveil — scried cards go to the bottom or top of the library, not to the graveyard."
- **Example card**: Serum Visions — "Scry 2, then draw a card."

## Acceptance Criteria
- [x] See `story-kw-scry.md` for full acceptance criteria
- [x] The action "scry N" lets the player rearrange the top N cards
- [x] Cards placed on bottom of library in any order
- [x] Remaining cards stay on top in any order
- [x] "Whenever you scry" triggers fire

## Dependencies
- story-kw-scry.md (full keyword story)
- Surveil (story-action-surveil.md) — related but distinct

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

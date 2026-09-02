# Story: Suspend (CR 702.62)

## User Story
As a game engine developer, I want the suspend action to function correctly per the Comprehensive Rules, so that players can exile cards from their hand with time counters and have them cast automatically when the last counter is removed.

## Context
This game action is already fully documented under the keyword story `story-kw-suspend.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 702.62a**: "Suspend is a keyword ability that lets a player exile a card from their hand with time counters."
- **CR 702.62b**: "At the beginning of the player's upkeep, remove a time counter. When the last is removed, cast the card without paying its mana cost."
- **CR 702.62c**: "A player may suspend a card from their hand during their main phase by exiling it with N time counters. This is a special action."
- **Example card**: "Suspend 5 — {W}"

## Acceptance Criteria
- [x] See `story-kw-suspend.md` for full acceptance criteria
- [x] The special action to exile and set time counters works
- [x] Time counter removal during upkeep happens automatically
- [x] When last counter removed, the spell is cast without mana cost

## Dependencies
- story-kw-suspend.md (full keyword story)
- Special Actions (CR 116) — story-action-special-actions.md

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

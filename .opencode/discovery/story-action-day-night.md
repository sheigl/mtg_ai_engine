# Story: Day/Night Bound (CR 702.148)

## User Story
As a game engine developer, I want the day/night cycle to function correctly per the Comprehensive Rules, so that daybound/nightbound cards transform appropriately and permanents enter with correct day/night status.

## Context
This game action is already fully documented under the game mechanic story `story-gm-day-night.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 702.148a**: "Daybound and nightbound are keyword abilities found on transforming double-faced cards."
- **CR 702.148b**: "A card with daybound enters the battlefield on its day face. While it's day, it remains on its day face."
- **CR 702.148c**: "If it becomes night, permanents with daybound transform to their nightbound face."
- **CR 702.148d**: "The game starts as day. It becomes night when a player casts no spells during their own turn."
- **Example card**: Tovolar, Dire Overlord // Tovolar, the Midnight Scourge

## Acceptance Criteria
- [x] See `story-gm-day-night.md` for full acceptance criteria
- [x] Game starts as "day" — daybound cards are on their day face
- [x] It becomes "night" when a player passes their turn without casting spells
- [x] It becomes "day" again when a player casts at least two spells in a turn

## Dependencies
- story-gm-day-night.md (full game mechanic story)
- Transform rules (story-rule-transform.md)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

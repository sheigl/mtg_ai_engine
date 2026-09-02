# Story: Kicker / Multi-kicker (CR 702.33)

## User Story
As a game engine developer, I want the kicker mechanic to function correctly per the Comprehensive Rules, so that players may pay an additional optional cost when casting a spell to increase its effect.

## Context
This game action is already fully documented under the keyword story `story-kw-kicker.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 702.33a**: "Kicker is a keyword ability that represents an optional additional cost."
- **CR 702.33b**: "A player may pay the kicker cost as they cast the spell."
- **CR 702.33c**: "Multi-kicker means a player may pay the kicker cost any number of times."
- **CR 702.33d**: "The spell checks whether it was kicked to determine its effect."
- **Example card**: "Kicker {1}{B}"

## Acceptance Criteria
- [x] See `story-kw-kicker.md` for full acceptance criteria
- [x] Kicker cost is an optional additional cost paid during casting
- [x] Multi-kicker can be paid multiple times
- [x] The spell's effect is modified based on whether/ how many times it was kicked

## Dependencies
- story-kw-kicker.md (full keyword story)
- Casting a Spell (story-action-cast-spell.md) — kicker is paid during step 3

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

# Story: Proliferate (CR 702.39)

## User Story
As a game engine developer, I want the proliferate action to function correctly per the Comprehensive Rules, so that players can choose permanents and/or players with counters and add one more of each existing counter type.

## Context
This game action is already fully documented under the game mechanic story `story-gm-proliferate.md`. This file serves as an action-oriented reference.

### Comprehensive Rules Grounding
- **CR 702.39a**: "To proliferate, choose any number of permanents and/or players that have a counter, then give each exactly one additional counter of a kind that permanent or player already has."
- **CR 702.39b**: "If a permanent has both +1/+1 and -1/-1 counters, proliferating adds one of each (since they are different kinds)."
- **Example card**: Flux Channeler — "Whenever you cast a noncreature spell, proliferate."

## Acceptance Criteria
- [x] See `story-gm-proliferate.md` for full acceptance criteria
- [x] The action "proliferate" selects targets with counters and adds one more of each counter type
- [x] Player counters (poison, experience, energy) are also valid targets
- [x] "Whenever you proliferate" triggers fire

## Dependencies
- story-gm-proliferate.md (full game mechanic story)
- Counter rules (story-rule-counters.md)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

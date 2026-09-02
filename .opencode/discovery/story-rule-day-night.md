# Story: Day/Night Cycle (CR 702.148)

## User Story
As a game engine developer, I want the Day/Night cycle to correctly track whether the game is day or night, transform appropriate permanents at each turn's beginning, and correctly trigger day/night-change events per CR 702.148.

## Context
The Day/Night cycle is a global game state that starts when a player casts a spell with daybound/nightbound during a non-day turn. When it becomes day, nightbound creatures transform to their daybound side. When it becomes night, daybound creatures transform to their nightbound side. The cycle switches between day and night based on whether players cast spells during their turns.

### Comprehensive Rules Grounding
- **CR 702.148a**: "Day is a designation that applies to the game as a whole. It begins when a player casts a daybound/nightbound spell."
- **CR 702.148b**: "If it's day, nightbound creatures are day-side up. If it's night, daybound creatures are night-side up."
- **CR 702.148c**: "Day becomes night if no spells were cast during a turn. Night becomes day if two or more spells were cast during a turn."
- **CR 702.148d**: "The day/night cycle is tracked on the game state, not on any permanent."
- **Example card**: Tovolar, Dire Overlord // Tovolar, the Midnight Hunt — transforms with day/night

## Acceptance Criteria
- [x] `is_day(gs) -> bool` and `is_night(gs) -> bool` query helpers
- [x] Day/Night state tracked on GameState as `day_or_night: str` ("day" / "night" / None)
- [x] Day/Night begins when a player casts a daybound/nightbound spell during non-day
- [x] Day→Night: checked as each turn ends — if no spells were cast that turn, it becomes night
- [x] Night→Day: checked as each turn ends — if two or more spells were cast that turn, it becomes day
- [x] Daybound creatures transform to nightbound at the beginning of each turn if it's night
- [x] Nightbound creatures transform to daybound at the beginning of each turn if it's day
- [x] Day/Night change triggers: cards that care about day/night changing trigger appropriately
- [x] No spells cast by ANY player (not just the active player) in a turn causes day→night
- [x] Two or more spells cast by the active player in a turn causes night→day
- [x] Integration tests cover: day starts, day→night, night→day, daybound transforms, nightbound transforms, day/night change triggers, no spells case
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Transform Rules (CR 701.28) — day/night cycle causes transforms
- Game mechanic story: `story-gm-day-night.md` — the day/night mechanic overview

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- This story covers the RULES aspects of the day/night cycle, while `story-gm-day-night.md` covers the game mechanic implementation
- Day/Night was introduced in Innistrad: Midnight Hunt and Innistrad: Crimson Vow
- The cycle is checked at the BEGINNING of each turn (upkeep step) for transforms, and at the END of each turn for day/night switching
- "No spells were cast" means by ANY player during that turn — so if Player A passes without casting and Player B casts on Player A's turn, it counts
- Day/night can be changed by spells/abilities that say "it becomes day" or "it becomes night"
- A game that hasn't started day/night (no daybound/nightbound spell cast) doesn't track it
- The GameState needs a `day_or_night: str | None` field that's None initially
- Day/Night is tracked globally for the game, not per player
- Spell counting: just the number of spells cast, not the number of spell casts (copies don't count)

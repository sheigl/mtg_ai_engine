# Story: Riot (CR 702.135)

## User Story
As an MTG engine developer, I want a new riot keyword module with real apply() and integration tests, so that cards with riot work correctly in the engine.

## Context
No file exists for riot. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.135**: "Riot is a static ability that functions while a creature is on the battlefield. 'Riot' means 'This creature enters with an additional +1/+1 counter on it or with haste.'"
- **Example card**: Gruul Spellbreaker — "Riot (This creature enters with your choice of a +1/+1 counter on it or haste.)"
- **Rule source**: ETB modal static ability (counter or haste)

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/riot.py` with `Riot` class extending `PassiveKeyword`
- [ ] `parse_riot(oracle_text) -> bool` detects riot keyword
- [ ] For human players: queues `pending_riot_choice` with options (counter vs haste)
- [ ] For AI players: auto-resolves (prefers haste if the creature can attack immediately, otherwise counter)
- [ ] Counter path: places a +1/+1 counter on the creature as it enters
- [ ] Haste path: grants haste ability to the creature (sets `summoning_sick = False`)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: choose +1/+1 counter, choose haste, human choice queuing, AI auto-resolution, counter + haste from other sources can coexist, multiple riot creatures entering
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: S

## Notes
- One of the simpler modal keywords (just a binary choice)
- Haste is applied as the creature enters (not as an activated ability)
- The choice is made as the creature enters the battlefield
- Ravnica Allegiance mechanic (Gruul)
- Similar pattern to fabricate but simpler (only 2 options)

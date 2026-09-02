# Story: Devour (CR 702.66)

## User Story
As an MTG engine developer, I want a new devour keyword module with real apply() and integration tests, so that cards with devour N work correctly in the engine.

## Context
No file exists for devour. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.66**: "Devour is a static ability. 'Devour N' means 'As this object enters, you may sacrifice any number of creatures. This permanent enters with N +1/+1 counters on it for each creature sacrificed this way.'"
- **Example card**: Devourer of Fate — "Devour 2 (As this enters, you may sacrifice any number of creatures. It enters with twice that many +1/+1 counters on it.)"
- **Rule source**: ETB replacement that adds +1/+1 counters based on sacrificed creatures

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/devour.py` with `Devour` class extending `TriggeredKeyword`
- [ ] `parse_devour(oracle_text) -> int | None` detects devour N count
- [ ] For human players: queues `pending_devour_choice` with eligible creature selections
- [ ] For AI players: auto-resolves (sacrifices all eligible creatures with power <= 2, or skips if none)
- [ ] Counters placed after sacrifice resolution: N counters per creature sacrificed
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: devour 2 with 3 creatures, devour 0 (no creatures), devour 1 with 1 creature, AI auto-resolution choice, human choice queuing, zero creatures to sacrifice
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: S

## Notes
- The sacrifice happens as the creature enters the battlefield (part of ETB replacement)
- Can sacrifice 0 creatures — the creature just enters without extra counters
- Shards of Alara block mechanic
- The number of +1/+1 counters is N × creatures_sacrificed

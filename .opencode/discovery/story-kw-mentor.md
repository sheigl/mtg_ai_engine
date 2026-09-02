# Story: Mentor (CR 702.134)

## User Story
As an MTG engine developer, I want a new mentor keyword module with real apply() and integration tests, so that cards with mentor work correctly in the engine.

## Context
No file exists for mentor. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.134**: "Mentor is a triggered ability. 'Mentor' means 'Whenever this creature attacks, put a +1/+1 counter on target attacking creature with power less than this creature's power.'"
- **Example card**: Mentor of the Meek — "Mentor (Whenever this creature attacks, put a +1/+1 counter on target attacking creature with power less than this creature's power.)"
- **Rule source**: Attack-triggered +1/+1 counter placement

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/mentor.py` with `Mentor` class extending `TriggeredKeyword`
- [ ] `check_mentor_trigger(game_state, attacker_id) -> bool` checks if the attacking creature has mentor
- [ ] `find_mentor_targets(game_state, attacker_id) -> list[str]` finds eligible targets (other attacking creatures with lesser power)
- [ ] For human players: queues target selection with eligible creatures
- [ ] For AI players: auto-resolves (chooses the creature with the lowest power that is less than mentor)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic mentor trigger, target must have lesser power, no eligible targets (no trigger), multiple mentor triggers simultaneously, mentor power changes before trigger resolves
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: S

## Notes
- Similar to evolve but attack-triggered instead of ETB-triggered
- Target's power must be strictly less than mentor's power (checked on trigger and on resolution)
- Only targets attacking creatures the mentor creature attacked with (same combat)
- Guilds of Ravnica mechanic (Boros and Azorius)

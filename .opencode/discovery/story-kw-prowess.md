# Story: Prowess (CR 702.119)

## User Story
As an MTG engine developer, I want a new prowess keyword module with real apply() and integration tests, so that cards with prowess work correctly in the engine.

## Context
No file exists for prowess. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.119**: "Prowess is a triggered ability. 'Prowess' means 'Whenever you cast a noncreature spell, this creature gets +1/+1 until end of turn.'"
- **Example card**: Stormwing Entity — "Prowess (Whenever you cast a noncreature spell, this creature gets +1/+1 until end of turn.)"
- **Rule source**: Triggered +1/+1 until end of turn on noncreature spell cast

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/prowess.py` with `Prowess` class extending `TriggeredKeyword`
- [ ] `check_prowess_trigger(game_state, spell_cast, controller) -> bool` detects prowess on controller's creatures
- [ ] `apply_prowess(game_state, creature_id) -> GameState` gives +1/+1 until end of turn
- [ ] Trigger fires for each noncreature spell cast by the creature's controller
- [ ] Does NOT trigger on creature spells
- [ ] +1/+1 bonus lasts until end of turn (needs turn-based cleanup)
- [ ] Multiple triggers stack (casting 2 spells = +2/+2)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic prowess trigger on instant, trigger on sorcery, no trigger on creature spell, multi-spell stacking, multiple prowess creatures both trigger, prowess on enchantment cast, +1/+1 wears off at end of turn
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: S

## Notes
- Signature ability of Jeskai (from Khans of Tarkir) and one of the most common modern evergreen keywords
- Since 2019, prowess also appears on red/blue cards as evergreen
- Can trigger multiple times per turn; the +1/+1 bonuses stack
- Must correctly detect "noncreature spell" — excludes creature spells but includes artifact, enchantment, instant, sorcery, planeswalker, battle
- The Prowess trigger goes on the stack above the triggering spell

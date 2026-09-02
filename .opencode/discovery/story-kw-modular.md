# Story: Modular (CR 702.42)

## User Story
As an MTG engine developer, I want a new modular keyword module with real apply() and integration tests, so that cards with modular N work correctly in the engine.

## Context
No file exists for modular. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.42**: "Modular represents two abilities: one static ability that causes the permanent to enter with N +1/+1 counters, and a triggered ability that causes those counters to move to another artifact creature when the permanent dies."
- **CR 702.42a**: "Modular N means 'This permanent enters with N +1/+1 counters on it' and 'When this permanent dies, you may put a +1/+1 counter on target artifact creature for each +1/+1 counter that was on this permanent.'"
- **Example card**: Arcbound Ravager — "Modular 1 (This enters with a +1/+1 counter on it. When it dies, you may put its +1/+1 counters on target artifact creature.)"
- **Rule source**: ETB counters + death trigger counter transfer

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/modular.py` with `Modular` class extending `TriggeredKeyword`
- [ ] `parse_modular(oracle_text) -> int | None` detects modular N count
- [ ] ETB effect: places N +1/+1 counters on the creature when it enters
- [ ] Death trigger: moves all +1/+1 counters from this permanent to target artifact creature
- [ ] For human players: queues target selection for death trigger
- [ ] For AI players: auto-resolves (chooses the artifact creature with the lowest power)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: modular 1 enters with 1 counter, modular 3 enters with 3 counters, death trigger moves counters to another artifact creature, no target (no trigger), counter count at death is what moves (not necessarily N)
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Key part of affinity/artifact synergies (Mirrodin block)
- The number of counters that move is the number on the creature WHEN it dies (could be more or less than N due to other effects)
- Transfer is optional; target must be an artifact creature
- Very commonly played in Modern/Legacy affinity decks

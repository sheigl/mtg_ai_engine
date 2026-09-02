# Story: Evolve (CR 702.100)

## User Story
As an MTG engine developer, I want a new evolve keyword module with real apply() and integration tests, so that cards with evolve work correctly in the engine.

## Context
No file exists for evolve. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.100**: "Evolve is a triggered ability. 'Evolve' means 'Whenever a creature you control enters, if that creature has power greater than this creature and/or toughness greater than this creature, put a +1/+1 counter on this creature.'"
- **Example card**: Cloudfin Raptor — "Evolve (Whenever a creature you control enters, if that creature has greater power or toughness than this, put a +1/+1 counter on this creature.)"
- **Rule source**: ETB-triggered +1/+1 counter based on comparative stats

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/evolve.py` with `Evolve` class extending `TriggeredKeyword`
- [ ] `check_evolve(game_state, creature_entered_id, evolver_id) -> bool` checks if the entered creature has greater power OR greater toughness than the evolver
- [ ] `apply_evolve(game_state, evolver_id) -> GameState` places +1/+1 counter on the evolver
- [ ] Trigger fires when a creature ETBs under the same controller
- [ ] Does NOT fire if the entering creature has lesser or equal power AND lesser or equal toughness
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: triggers on greater power, triggers on greater toughness, triggers on both greater, does NOT trigger on lesser, does NOT trigger on equal both, multiple evolver interactions, non-creature ETB doesn't trigger
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Very similar to mentor but triggered on ETB rather than attack
- Can trigger multiple times for each new creature that enters with greater stats
- Only checks power OR toughness — if either is greater, it triggers
- Gatecrash mechanic, appears on many Simic-colored cards
- Works well with +1/+1 counter synergies

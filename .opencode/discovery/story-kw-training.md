# Story: Training (CR 702.128)

## User Story
As an MTG engine developer, I want a new training keyword module with real apply() and integration tests, so that cards with training work correctly in the engine.

## Context
No file exists for training. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.128**: "Training is a triggered ability. 'Training' means 'Whenever this creature attacks with another creature with greater power, put a +1/+1 counter on this creature.'"
- **Example card**: Sigiled Sword of Valeron — "Training (Whenever this creature attacks with another creature with greater power, put a +1/+1 counter on this creature.)"
- **Rule source**: Attack-triggered +1/+1 counter when attacking with a stronger creature

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/training.py` with `Training` class extending `TriggeredKeyword`
- [ ] `check_training_trigger(game_state, attacker_id, all_attackers) -> bool` checks if training creature attacks with another creature of greater power
- [ ] `apply_training(game_state, creature_id) -> GameState` places a +1/+1 counter
- [ ] Trigger only fires if there is at least one other attacking creature with strictly greater power
- [ ] Does NOT trigger if no other creatures attack or if all other attackers have equal or lesser power
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basics training trigger with stronger creature, no trigger without stronger creature, multiple training creatures both can trigger, power buffs are considered, equal power does NOT trigger, creature with training plus its own +1/+1 counters can later train itself again
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: S

## Notes
- Similar to mentor but opposite direction: training checks if another attacker has GREATER power
- The check is "greater power" not "greater or equal"
- Often found on white cards in Strixhaven and Innistrad: Midnight Hunt
- Dominaria United had training as a major mechanic
- Naturally good with +1/+1 counter synergies

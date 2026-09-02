# Story: Mutates Trigger (CR 702.149)

## User Story
As an MTG engine developer, I want a "mutates" trigger pattern with check function and engine wiring, so that cards with "whenever this creature mutates" triggered abilities fire correctly.

## Context
No mutate trigger pattern exists in triggers.py. Mutate (CR 702.149) was introduced in Ikoria: Lair of Behemoths. When a creature mutates, it merges with another creature, becoming a single creature with all abilities. Cards like [[Aetherstorm Roc]] have "whenever this creature mutates" triggers.

### Comprehensive Rules Grounding
- **CR 702.149b**: "A non-Human creature that targets a Human creature with mutate merges with it. The merged creature is the topmost creature on the stack."
- **CR 702.149e**: "When a creature mutates, its controller puts the card onto the battlefield or on top of the target creature."
- **Game event**: A mutate spell resolves, merging the mutate card with the target creature
- **Example card**: *Auspicious Starrix* — "Whenever this creature mutates, reveal cards from the top of your library until you reveal a permanent card. Put that card onto the battlefield and the rest on the bottom."

## Acceptance Criteria
- [ ] Create `MUTATE_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:this|~|this creature) mutates", "whenever a creature you control mutates"
- [ ] Create `check_mutate_triggers(game_state, mutated_perm_id: str)` that queues PendingTriggers
- [ ] Wire into the mutate resolution handler (where the merge happens)
- [ ] Integration tests: mutating fires trigger, casting a non-mutate spell does NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- Mutate creates a merged creature stack — the trigger source is the topmost card's abilities
- The trigger condition is the mutate event itself (the spell resolving and merging)
- Forge's trigger: `MutatedTrigger`

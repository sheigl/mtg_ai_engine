# Story: Excess Damage Trigger (CR 702.19)

## User Story
As an MTG engine developer, I want an excess-damage trigger pattern with check function and engine wiring, so that cards with "Whenever ~ deals excess damage to a creature" triggered abilities (trample excess) fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. When a creature with trample deals lethal damage to a blocker, the remaining damage is "excess damage" that can trigger other abilities.

### Comprehensive Rules Grounding
- **CR 702.19**: "If a creature with trample would assign enough damage to its blockers to kill them, the rest may be assigned to the defending player or planeswalker."
- **Example card**: *Silverstar Swordsman* — "Whenever a creature you control deals excess damage to a creature that player controls, draw a card."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into trample damage assignment in combat/core.py
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Excess damage refers to damage beyond what is needed to destroy the blocking creature in trample damage assignment.
- The trigger fires on the amount of damage assigned past lethal to the blocker.
- Must work with existing trample implementation and damage assignment.
- Example cards: *Silverstar Swordsman*, *Ghalta, Primal Hunger* (trample enabler interaction).

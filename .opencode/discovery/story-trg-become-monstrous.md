# Story: Become Monstrous Trigger (CR 702.31)

## User Story
As an MTG engine developer, I want a become-monstrous trigger pattern with check function and engine wiring, so that cards with "When ~ becomes monstrous" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Monstrous" is a keyword ability from Theros block where a creature activates its monstrosity ability and becomes monstrous.

### Comprehensive Rules Grounding
- **CR 702.31**: "Monstrosity is an activated ability that functions while the creature is on the battlefield. '{Cost}: Monstrosity N.' This means 'If this permanent isn't monstrous, put N +1/+1 counters on it and it becomes monstrous.'"
- **Example card**: *Nemesis of Mortals* — "When Nemesis of Mortals becomes monstrous, put X +1/+1 counters on it, where X is the number of creature cards in your graveyard."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into monstrosity keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- The trigger fires as part of activating the monstrosity ability, after the creature becomes monstrous.
- The trigger should only fire once per activation — if the creature is already monstrous, monstrosity does nothing and no trigger fires.
- Cards like *Nemesis of Mortals*, *Polukranos, World Eater*, and *Stormbreath Dragon* have become-monstrous triggers.

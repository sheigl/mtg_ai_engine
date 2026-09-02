# Story: Devoured Trigger (CR 702.66)

## User Story
As an MTG engine developer, I want a devoured trigger pattern with check function and engine wiring, so that cards with "When ~ devours" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. Devour is a keyword from the Shards of Alara block where creatures eat other creatures and get +1/+1 counters.

### Comprehensive Rules Grounding
- **CR 702.66**: "Devour N means 'As this permanent enters the battlefield, you may sacrifice any number of creatures. This permanent enters the battlefield with N +1/+1 counters on it for each creature sacrificed this way.'"
- **Example card**: *Mycoloth* — "When Mycoloth devours, put X +1/+1 counters on it, where X is the number of creatures devoured."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into devour keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Devour triggers fire as part of the devour keyword ability when the creature enters the battlefield.
- The trigger fires after the sacrifice and counter placement are complete.
- Must track how many creatures were devoured (devour count) for the trigger to reference.
- Example cards: *Mycoloth*, *Predator Dragon*, *Thornling*, *Hellkite Overlord*.

# Story: Becomes Crewed Trigger (CR 702.121a)

## User Story
As an MTG engine developer, I want a becomes-crewed trigger pattern with check function and engine wiring, so that cards with "Whenever ~ becomes crewed" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. Crew is an ability on Vehicle artifacts that allows creatures to be tapped to animate the vehicle.

### Comprehensive Rules Grounding
- **CR 702.121a**: "Crew is an activated ability of Vehicle artifacts. '{Q}: Crew N' means 'Tap any number of untapped creatures you control with total power N or more: This permanent becomes an artifact creature until end of turn.'"
- **Example card**: *Aethersphere Harvester* — "Whenever Aethersphere Harvester becomes crewed, you gain 1 life."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into crew keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md
- Crew keyword module (story-kw-crew.md)

## Priority: Medium

## Estimated Effort: M

## Notes
- The trigger fires when a Vehicle artifact becomes an artifact creature via crewing.
- Distinguish from the vehicle becoming a creature via other means (e.g., animated by another effect).
- Example cards: *Aethersphere Harvester*, *Heart of Kiran*, *Cultivator's Caravan*, *Skysovereign, Consul Flagship*.

# Story: Abandoned Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want an abandoned trigger pattern with check function and engine wiring, so that cards with "Whenever you abandon a creature" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Abandoned" is a vehicle-crewing-related mechanic where a creature that was crewing a vehicle becomes abandoned (typically when the vehicle leaves the battlefield or is otherwise no longer crewed).

### Comprehensive Rules Grounding
- **CR 702.XX**: "To abandon a creature means that a creature that was crewing a vehicle is no longer crewing it. This typically happens when the vehicle leaves the battlefield or when the crewing creature leaves the battlefield."
- **Example card**: *Weatherlight* — "Whenever a creature you control becomes abandoned, you may draw a card."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into vehicle/crew event flow (when vehicle leaves battlefield or crew creature leaves)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md
- Crew keyword module (story-kw-crew.md) for crew mechanic grounding

## Priority: Medium

## Estimated Effort: M

## Notes
- Abandoned triggers are relatively rare but exist in vehicle-heavy sets like Weatherlight, Aetherdrift, and Kaladesh block.
- The trigger fires when a creature that was crewing a vehicle is no longer crewing it — typically when the vehicle is destroyed, exiled, or returned to hand, or when the crewing creature leaves the battlefield.
- Consider whether this should be a dedicated zone-change listener or a subset of existing leave-the-battlefield triggers.

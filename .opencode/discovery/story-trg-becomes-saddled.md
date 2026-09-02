# Story: Becomes Saddled Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a becomes-saddled trigger pattern with check function and engine wiring, so that cards with "When ~ becomes saddled" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Saddle" is a keyword from Outlaws of Thunder Junction (OTJ) that allows Mounts to be saddled by tapping creatures, similar to Crew but for Mount creatures.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Saddle is an activated ability. '{T}: Saddle N' means 'Tap any number of untapped creatures you control with total power N or more: This Mount becomes saddled until end of turn.'"
- **Example card**: *Highway Robbery* — "When ~ becomes saddled, create a Treasure token."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into saddle keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md
- Saddle keyword module (story-kw-saddle.md)

## Priority: Medium

## Estimated Effort: M

## Notes
- Saddle triggers fire when a Mount becomes saddled (similar to Crew triggers).
- Distinguish from the mount becoming saddled via other means (e.g., effects that cause it to become saddled without using the activated ability).
- Example cards: *Highway Robbery*, *Ghost Town*, *Bone Hunters*, *Emberfoot Cardillo*.

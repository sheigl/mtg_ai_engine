# Story: Elementalbend Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want an elementalbend trigger pattern with check function and engine wiring, so that cards with Avatar-themed bending abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Elementalbend" is an Avatar/Universes Beyond-themed mechanic that involves manipulating elements.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Elementalbend is a special action that allows a player to change the element (color) of a spell or permanent."
- **Example card**: *Aang, the Last Airbender* — "Whenever you elementalbend, you may tap or untap target permanent."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into elementalbending resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Elementalbend is a Universes Beyond mechanic tied to Avatar-themed sets.
- The trigger fires when a player performs the "elementalbend" special action.
- This is a niche mechanic and may not appear in many tournament-legal sets.
- Exact CR reference may vary depending on the specific set/mechanic implementation.

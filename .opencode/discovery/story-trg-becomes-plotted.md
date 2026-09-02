# Story: Becomes Plotted Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a becomes-plotted trigger pattern with check function and engine wiring, so that cards with "When ~ becomes plotted" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Plot" is a keyword from recent sets (e.g., Outlaws of Thunder Junction, Aetherdrift) that allows exiling cards from hand to cast later.

### Comprehensive Rules Grounding
- **CR 702.XX**: "To plot a card, exile it from your hand facedown. You may look at it and cast it from exile on a later turn as though it were in your hand."
- **Example card**: Various plot cards — "When this creature becomes plotted, you may have it deal damage equal to its power to target creature."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into plot keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Plot is a newer mechanic; the trigger fires when a card is plotted (exiled face-down from hand).
- Distinguish from other exile effects — plot specifically uses the "plot" keyword action.
- Affected sets: Outlaws of Thunder Junction (OTJ), Aetherdrift (DFT), and other recent standard sets.

# Story: Chaos Ensues Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a chaos-ensues trigger pattern with check function and engine wiring, so that Planechase planar cards with chaos abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Chaos ensues" is the trigger condition for the chaos symbol on planar cards in the Planechase variant format.

### Comprehensive Rules Governing Planes
- **CR 702.XX**: "Whenever you roll the planar die and get a chaos result, the plane's 'chaos ensues' ability triggers."
- **Example card**: *The Eon Fog* — "Chaos ensues — Upkeep: Skip your next turn."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into planar die roll flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Chaos ensues is specific to the Planechase variant and the planar die (6-sided die with {CHAOS}, {PLANESWALK}, and blank faces).
- Triggers specifically on a chaos result from the planar die roll.
- A lower priority until Planechase variant support is added, but the trigger pattern should be established for completeness.

# Story: Crank Contraption Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a crank-contraption trigger pattern with check function and engine wiring, so that Un-set contraption-cranking triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Crank" is a mechanic from the Unstable set where contraptions are "cranked" to activate their abilities.

### Comprehensive Rules Governing Contraptions
- **CR 702.XX**: "To crank a contraption, a player chooses any number of assembled contraptions they control and assembles them again. Each time a contraption is assembled, it may crank."
- **Example card**: *Boomflinger* — "Whenever you crank a contraption, Boomflinger deals 2 damage to any target."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into contraption-cranking flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Crank contraption is an Un-set mechanic from Unstable and is not legal in tournament formats.
- The trigger fires when a contraption is cranked (activated/assembled).
- Lower priority for tournament-legal format support but should exist for completeness.
- Example cards: *Boomflinger*, *Pie-eating Contest*, *Large Pile of Dead Germs*.

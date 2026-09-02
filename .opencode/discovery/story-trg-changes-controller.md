# Story: Changes Controller Trigger (CR 108.3)

## User Story
As an MTG engine developer, I want a changes-controller trigger pattern with check function and engine wiring, so that cards with "Whenever ~ changes controllers" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. Control-change effects allow a permanent to move from one player's control to another's, which can trigger abilities that care about control changes.

### Comprehensive Rules Grounding
- **CR 108.3**: "The controller of a permanent or spell is the player who placed it on the battlefield or on the stack as appropriate."
- **CR 108.6**: "If a spell or ability instructs a player to gain control of a permanent, that player becomes its controller. If a spell or ability instructs a player to exchange control of two permanents, each player gains control of the other player's permanent."
- **Example card**: *Molten Primordial* — "When Molten Primordial enters the battlefield, for each opponent, gain control of target creature until end of turn."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into control-change effect resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Control change triggers fire when a permanent's controller changes for any reason (spell effect, ability resolution, etc.).
- Distinguish between temporary control changes ("until end of turn") and permanent ones.
- Cards that care about control changes include *Captive Audience*, *Blatant Thievery*, *Insurrection*, and *Redirect*.
- Consider how to track the old controller and new controller for trigger resolution.

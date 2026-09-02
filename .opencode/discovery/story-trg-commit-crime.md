# Story: Commit Crime Trigger (CR 701.XX)

## User User
As an MTG engine developer, I want a commit-crime trigger pattern with check function and engine wiring, so that cards with "Whenever you commit a crime" triggered abilities from Outlaws of Thunder Junction fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Commit a crime" is a keyword mechanic from Outlaws of Thunder Junction (OTJ) that tracks when a player targets an opponent or something an opponent controls.

### Comprehensive Rules Grounding
- **CR 701.XX**: "To commit a crime means to target an opponent or something an opponent controls with a spell or ability you control."
- **Example card**: *Rilsa Rael, Kingpin* — "Whenever you commit a crime, target creature gets +1/+0 and gains deathtouch until end of turn."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into targeting flow (when a player targets an opponent or opponent's permanent)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- "Commit a crime" is a broad trigger that fires whenever you target an opponent (player) or a permanent/spell/ability an opponent controls.
- This overlaps with "becomes target" triggers but is from the targeting player's perspective rather than the target's perspective.
- Example cards: *Rilsa Rael, Kingpin*, *Vial Smasher the Gleeful*, *Jolene, the Plunder Queen*.
- Must ensure this doesn't double-fire with existing targeting triggers.

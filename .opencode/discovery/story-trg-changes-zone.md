# Story: Changes Zone Trigger (CR 400.1)

## User Story
As an MTG engine developer, I want a general changes-zone trigger pattern with check function and engine wiring, so that cards with "Whenever ~ is put into a graveyard from anywhere" or "Whenever ~ leaves the battlefield" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. General zone-change triggers respond to a permanent moving from one zone to another, regardless of the specific zone involved.

### Comprehensive Rules Grounding
- **CR 400.1**: "A zone is a place where objects can be during a game. There are normally seven zones: library, hand, battlefield, graveyard, stack, exile, and command zone."
- **CR 400.7**: "An object that moves from one zone to another becomes a new object with no memory of, or relation to, its previous existence."
- **Example card**: *Gary, the Grieftaker* — "Whenever a creature is put into a graveyard from anywhere, you gain 1 life."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into zone-change event flow in zones.py
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- This is a general "leaves the battlefield" / "enters a graveyard from anywhere" trigger pattern.
- Must be careful not to double-fire with more specific triggers (death triggers, sacrifice triggers).
- The zone change event in zones.py is the single point where all zone transitions happen — this is where wiring should occur.
- Consider whether this should be a catch-all or if individual zone transitions should each have their own pattern.

# Story: Counter Added All Trigger (CR 122.1)

## User Story
As an MTG engine developer, I want a counter-added-all trigger pattern with check function and engine wiring, so that cards with "Whenever one or more counters are put on a permanent you control" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. This is a broader trigger than a specific "counter placed on this creature" — it fires whenever ANY counter is placed on ANY permanent the player controls.

### Comprehensive Rules Grounding
- **CR 122.1**: "A counter is a marker placed on an object or player that modifies its characteristics and/or interacts with a number of abilities."
- **CR 122.6**: "If a spell or ability instructs a player to put counters on an object, that player puts that many counters on that object."
- **Example card**: *Hardened Scales* — "Whenever one or more counters are put on a creature you control, put an additional counter of that type on it."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into all counter-placement flows
- [ ] Integration tests that distinguish from specific counter triggers
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- This trigger fires when counters are put on ANY permanent the player controls (not just a specific one).
- Must be wired into the same centralized counter-placement flow as other counter triggers.
- Must coexist with more specific counter triggers without double-firing.
- Example cards: *Hardened Scales*, *Kami of Whispered Hopes*, *Branching Evolution*, *Winding Constrictor*.
- Distinguish from "counter placed on this creature" — this is a broader "any of my permanents" pattern.

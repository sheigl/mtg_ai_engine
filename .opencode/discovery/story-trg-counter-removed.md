# Story: Counter Removed Trigger (CR 122.1)

## User Story
As an MTG engine developer, I want a counter-removed trigger pattern with check function and engine wiring, so that cards with "Whenever a counter is removed from ~" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. Counter removal triggers fire when one or more counters are removed from a permanent (not when they are placed).

### Comprehensive Rules Grounding
- **CR 122.1**: "A counter is a marker placed on an object or player that modifies its characteristics and/or interacts with a number of abilities."
- **CR 122.7**: "If a spell or ability instructs a player to remove counters from an object, that player removes that many counters from that object."
- **Example card**: *Power Conduit* — "Remove a counter from target permanent you control: Put a charge counter on target artifact."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into counter-removal flow (when counters are removed, not placed)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Counter removal triggers fire specifically when counters are removed, not when placed.
- Must distinguish from counter placement triggers and ensure both can coexist.
- Example cards: *Power Conduit*, *Hex Parasite*, *Aether Snap*, *Leeching Licid*.
- Consider whether "removed" includes moving counters (e.g., from one permanent to another via *Reyhan, Last of the Abzan*).

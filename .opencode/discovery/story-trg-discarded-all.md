# Story: Discarded All Trigger (CR 701.18)

## User Story
As an MTG engine developer, I want a discarded-all trigger pattern with check function and engine wiring, so that cards with "Whenever you discard one or more cards" triggered abilities fire correctly — distinguishing from single-discard triggers.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. This is distinct from the "whenever you discard a card" trigger — this fires once for a batch discard (e.g., discarding multiple cards simultaneously) rather than once per card discarded.

### Comprehensive Rules Grounding
- **CR 701.18**: "To discard a card, a player moves a card from their hand to their graveyard. A player may be instructed to discard one or more cards as a cost or as part of an effect."
- **Example card**: *Surly Badgersaur* — "Whenever you discard one or more cards, create a Treasure token."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py (distinguish "discard one or more" from "discard a card")
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into discard flow alongside existing discard triggers
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- This trigger fires once per discard event (batch), not once per card discarded.
- Distinguish pattern from simple "whenever you discard a card" — check for "one or more cards" in the oracle text.
- Example cards: *Surly Badgersaur*, *Honor-Worn Shaku*, *Jaheira, Friend of the Forest*.
- Must coexist with single-discard triggers and ensure both don't double-fire for the same event.

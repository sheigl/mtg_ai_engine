# Story: Discover Trigger (CR 701.XX)

## User Story
As an MTG engine developer, I want a discover trigger pattern with check function and engine wiring, so that cards with "When you discover" triggered abilities from The Lost Caverns of Ixalan fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Discover" is a keyword from The Lost Caverns of Ixalan (LCI) that exiles cards from the top of the library until a nonland card with a certain mana value or less is found.

### Comprehensive Rules Grounding
- **CR 701.XX**: "To discover N, exile cards from the top of your library until you exile a nonland card with mana value N or less. You may cast that card without paying its mana cost. Put the exiled cards on the bottom of your library in a random order."
- **Example card**: *Trumpeting Carnosaur* — "When you discover, Trumpeting Carnosaur deals damage equal to its power to any target."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into discover keyword resolution flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Discover triggers fire when the discover ability resolves (after casting or exiling the found card).
- Similar to Cascade but uses mana value threshold rather than casting cost.
- Example cards: *Trumpeting Carnosaur*, *Titanic Pelagosaur*, *Biolume Prince*, *Gishath's Incursion*.

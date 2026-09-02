# Story: Conjure (CR 702.XX)

## User Story
As a game engine developer, I want the conjure action to function correctly per the Comprehensive Rules, so that digital-only (Alchemy) effects can create cards that didn't start in the game.

## Context
Conjure is a digital-only (Alchemy) mechanic that creates a card from outside the game. The card is created in the specified zone (typically hand, library, or battlefield). Conjured cards are real game objects that can be played normally, but they cease to exist if they leave the game.

### Comprehensive Rules Grounding
- **CR 702.XXa**: "To conjure a card, a player creates a card that didn't start the game in any player's deck or sideboard."
- **CR 702.XXb**: "Conjured cards are put into the specified zone (hand, library, battlefield, graveyard, or exile)."
- **CR 702.XXc**: "A conjured card is a real Magic card with all normal characteristics."
- **CR 702.XXd**: "A conjured card ceases to exist if it would leave the game (e.g., exiled face-down)."
- **CR 702.XXe**: "Conjured cards are subject to all normal game rules."
- **Example card**: Various Alchemy cards — "Conjure a copy of a card from the spellbook."

## Acceptance Criteria
- [ ] `conjure(gs, player_name, card_definition, zone)` creates a card object in the specified zone
- [ ] Conjured card has all normal characteristics (name, mana cost, type, abilities, etc.)
- [ ] Conjured card behaves like a normal card — can be cast, sacrificed, etc.
- [ ] Conjured card ceases to exist if it leaves the game (exiled face-down, etc.)
- [ ] Conjured cards in hand count toward maximum hand size
- [ ] Conjured cards in graveyard can be targeted by graveyard effects
- [ ] Integration test: conjure a creature card, cast it from hand
- [ ] Integration test: conjured card can be reanimated from graveyard
- [ ] Integration test: multiple conjures create separate card objects
- [ ] Full regression suite passes

## Dependencies
- Card creation infrastructure (must support dynamic card creation)
- Zone management

## Priority: Low
## Status: ❌ Not Implemented

> **Gap**: No conjure implementation.

## Estimated Effort: L

# Story: Mill (CR 701.14)

## User Story
As a game engine developer, I want the mill action to function correctly per the Comprehensive Rules, so that players can put the top N cards of their library into their graveyard.

## Context
Milling is a keyword action that moves cards from the top of the library directly to the graveyard. It is not drawing, so it does not trigger "whenever you draw a card" effects and does not impact maximum hand size. Milling is a key enabler for graveyard-based strategies.

### Comprehensive Rules Grounding
- **CR 701.14**: "To mill N cards, a player puts the top N cards of their library into their graveyard."
- **CR 701.14b**: "Milling is not drawing cards. Abilities that trigger when a player draws a card do not trigger when a player mills a card."
- **Example card**: Thought Scour — "Target player mills three cards."
- **Example card**: Glimpse the Unthinkable — "Target player mills ten cards."

## Acceptance Criteria
- [ ] `mill(gs, player_name, n)` moves the top N cards from library to graveyard
- [ ] Cards enter graveyard in order (top card milled first is on top of graveyard)
- [ ] Milling does NOT trigger draw triggers
- [ ] Milling does NOT count toward maximum hand size
- [ ] If library has fewer than N cards, all cards are milled (no error)
- [ ] "Whenever a card is put into your graveyard from anywhere" triggers fire for milled cards
- [ ] "Whenever you mill a card" specific triggers fire
- [ ] Integration test: mill 3 cards, verify 3 cards from top of library are in graveyard
- [ ] Integration test: mill from empty library — no effect, no error
- [ ] Integration test: triggers that care about cards entering graveyard fire for milled cards
- [ ] Integration test: mill does not trigger draw triggers
- [ ] Full regression suite passes

## Dependencies
- Library/graveyard zone management
- Trigger system (graveyard entry triggers)

## Priority: High
## Status: 🔄 Partial

> **Gap**: Pattern matching detects `mill N` effects in stack.py, but the `_mill()` implementation is a stub that only logs and does not actually move cards from library to graveyard.

## Estimated Effort: S

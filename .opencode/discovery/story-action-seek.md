# Story: Seek (CR 702.XX)

## User Story
As a game engine developer, I want the seek action to function correctly per the Comprehensive Rules, so that digital-only (Alchemy) effects can search a player's library for a card with specific characteristics and put it into their hand.

## Context
Seek is a digital-only (Alchemy) mechanic that searches a player's library for a card matching specific criteria and puts it into their hand. Unlike a normal tutor, seeking does not require the player to know the contents of their library — the game engine finds a valid card automatically.

### Comprehensive Rules Grounding
- **CR 702.XXa**: "To seek a card, a player looks at their library, finds a card that matches the seeking criteria, and puts it into their hand."
- **CR 702.XXb**: "If multiple cards match the criteria, the player chooses one."
- **CR 702.XXc**: "If no card matches the criteria, seek does nothing."
- **CR 702.XXd**: "Seek does not shuffle the library unless specified."
- **CR 702.XXe**: "Seek uses the card's current characteristics (not copiable values) to determine matches."
- **Example card**: Various Alchemy cards — "Seek a card with mana value 2 or less."
- **Example card**: "Seek a creature card."

## Acceptance Criteria
- [ ] `seek(gs, player_name, criteria)` searches library for cards matching the criteria
- [ ] Criteria can include: mana value, card type, color, keyword, etc.
- [ ] Player (or AI) chooses which matching card to put into hand
- [ ] If multiple cards match, one is chosen and put into hand
- [ ] If no cards match, nothing happens (library is not shuffled)
- [ ] Library is not shuffled after seeking (unless specified)
- [ ] Seek is deterministic for AI (first match or best match by heuristic)
- [ ] Integration test: seek a creature card, find it in deck, put into hand
- [ ] Integration test: seek with criteria that doesn't match any card — nothing happens
- [ ] Integration test: seek by mana value range
- [ ] Integration test: seek does not shuffle library
- [ ] Full regression suite passes

## Dependencies
- Library zone operations (search, reveal)
- Card filtering/matching infrastructure

## Priority: Low
## Status: ❌ Not Implemented

> **Gap**: No seek implementation.

## Estimated Effort: M

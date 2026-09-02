# Story: Ante (CR 707)

## User Story
As a game engine developer, I want the ante mechanic to function correctly per the Comprehensive Rules, so that if ante cards are ever implemented, the proper ante rules are available.

## Context
Ante is a defunct mechanic from the earliest days of Magic where players would wager cards (their "ante") before the game. The winner of the game would take the loser's ante card. Ante was removed from tournament play in 1995 and cards that reference ante are banned in all competitive formats. Implementation is extremely low priority and primarily for completeness.

### Comprehensive Rules Grounding
- **CR 707.1**: "Ante is a method of playing Magic where each player puts one random card from their deck into the ante."
- **CR 707.2**: "When a player wins the game, that player gains ownership of all cards in the ante."
- **CR 707.3**: "Cards that reference ante are banned in all tournament formats."
- **CR 707.4**: "When playing for ante, each player antes a random card from their deck at the start of the game."
- **Example card**: Contract from Below — "Remove Contract from Below from your deck before playing if you're not playing for ante."
- **Example card**: Darkpact — "You gain ownership of the target player's ante card."

## Acceptance Criteria
- [ ] `setup_ante(gs)` moves one random card from each player's deck to the ante zone
- [ ] The ante zone is a separate game zone
- [ ] When a player wins the game, that player takes ownership of all ante cards
- [ ] Ante-related cards (Contract from Below, etc.) interact with the ante zone
- [ ] Ante is disabled by default (flagged as "not tournament legal")
- [ ] Integration test: ante setup — verify one random card from each player is in ante zone
- [ ] Integration test: ante transfer on game win
- [ ] Full regression suite passes

## Dependencies
- Game setup/initialization
- Zone management (ante zone)

## Priority: Low
## Status: ❌ Not Implemented

> **Gap**: No ante implementation.

## Estimated Effort: S

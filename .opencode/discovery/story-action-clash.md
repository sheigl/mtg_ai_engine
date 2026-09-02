# Story: Clash (CR 701.23)

## User Story
As a game engine developer, I want the clash action to function correctly per the Comprehensive Rules, so that players can reveal the top card of their library, compare mana values, and determine the winner who gets the bonus.

## Context
Clash is a keyword action where two or more players compare the top cards of their libraries. The player who reveals the card with the highest mana value wins the clash. All clashed cards go to the bottom of their owner's library in any order. Clash originated in Lorwyn block.

### Comprehensive Rules Grounding
- **CR 701.23a**: "To clash, starting with the player whose turn it is, each player reveals the top card of their library and puts it back on top."
- **CR 701.23b**: "The player who revealed a card with the highest mana value wins the clash."
- **CR 701.23c**: "Each player then puts their revealed card on the bottom of their library in any order."
- **CR 701.23d**: "If multiple players tie for highest mana value, no one wins the clash."
- **CR 701.23e**: "A clash has no effect if all players have empty libraries."
- **Example card**: "Clash with an opponent. If you win, draw a card."
- **Example card**: Judge of Ages — "Whenever Judge of Ages attacks, clash with target opponent. If you win, untap Judge of Ages."

## Acceptance Criteria
- [ ] `clash(gs, player_a, player_b)` reveals top card of each player's library
- [ ] Winner is the player with the highest mana value among revealed cards
- [ ] If tied (or all same), no one wins the clash
- [ ] All revealed cards go to the bottom of their owner's library in any order
- [ ] If any library is empty, that player reveals nothing and cannot win
- [ ] "Whenever you clash" triggers fire after clash resolves
- [ ] The clash winner condition ("if you win the clash") is evaluated for effects
- [ ] For human players: auto-resolve (clash is deterministic based on top card MV)
- [ ] Integration test: two-player clash, winner gets bonus
- [ ] Integration test: tied clash — no one wins
- [ ] Integration test: empty library player — cannot win clash
- [ ] Full regression suite passes

## Dependencies
- Library zone operations (reveal, bottom manipulation)
- Trigger system (clash triggers — story-trg-clashed.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No `clash()` function found anywhere in the engine.

## Estimated Effort: M

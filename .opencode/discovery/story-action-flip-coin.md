# Story: Flipping a Coin (CR 701.24)

## User Story
As a game engine developer, I want coin flipping to function correctly per the Comprehensive Rules, so that players can call heads or tails and have the result determine the effect of coin-flip cards.

## Context
Coin flipping is a randomized action used by several Magic cards. The player (usually the controller of the effect) calls "heads" or "tails" before the flip. The coin is presumed to be fair (50/50 outcome). The result of the flip determines which branch of the effect occurs.

### Comprehensive Rules Grounding
- **CR 701.24a**: "To flip a coin, the player who is flipping calls 'heads' or 'tails' before flipping."
- **CR 701.24b**: "If the call matches the result, the player wins the flip."
- **CR 701.24c**: "A coin is presumed to be fair — 50% chance of heads, 50% chance of tails."
- **CR 701.24d**: "Some effects allow a player to flip again if they lose the flip."
- **CR 701.24e**: "The game engine determines the outcome of the flip randomly."
- **Example card**: Mana Clash — "Each player flips a coin. Repeat until a player loses a flip."
- **Example card**: Krark's Thumb — "If you would flip a coin, instead flip two coins and ignore one."
- **Example card**: Frenetic Efreet — "Flip a coin: If you win the flip, Frenetic Efreet phases out."

## Acceptance Criteria
- [ ] `flip_coin(gs, player_name, call)` returns heads or tails randomly
- [ ] For human players: player chooses "heads" or "tails" as their call
- [ ] For AI players: auto-call (e.g., always heads) or true random
- [ ] The result is determined by a seeded random number generator (for reproducibility)
- [ ] "Whenever you win/lose a coin flip" triggers fire
- [ ] Replacements: Krark's Thumb replaces "flip a coin" with "flip two coins, ignore one"
- [ ] Multiple flips in a single effect (Mana Clash) loop until condition is met
- [ ] Integration test: flip a coin, verify result is heads or tails
- [ ] Integration test: Krark's Thumb replacement — flip two, get preferred result
- [ ] Integration test: Mana Clash loops until a player loses
- [ ] Integration test: deterministic with same seed
- [ ] Full regression suite passes

## Dependencies
- Random number generation (seeded for reproducibility)
- Replacement effects (story-rule-replacement-effects.md, for Krark's Thumb)
- Trigger system (coin flip triggers — story-trg-flipped-coin.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No coin flip implementation.

## Estimated Effort: S

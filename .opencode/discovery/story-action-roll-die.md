# Story: Rolling a Die (CR 701.25)

## User Story
As a game engine developer, I want die rolling to function correctly per the Comprehensive Rules, so that cards that reference rolling dice (primarily from Dungeons & Dragons sets) resolve properly.

## Context
Die rolling is a randomized action used in D&D-themed Magic sets. Dice can be various sizes (d4, d6, d12, d20 as most common). The player rolls the die and the result determines which outcome occurs based on the card's text. "Roll a d20" results often have multiple outcomes based on ranges.

### Comprehensive Rules Grounding
- **CR 701.25a**: "To roll a die, a player rolls a six-sided die unless a different size is specified."
- **CR 701.25b**: "The result is the number rolled on the die."
- **CR 701.25c**: "Some effects say 'roll a d20' — roll a 20-sided die."
- **CR 701.25d**: "Some effects have multiple outcomes based on the die roll result."
- **CR 701.25e**: "If a die is rerolled, the new result replaces the old one."
- **CR 701.25f**: "The game engine determines the result randomly."
- **Example card**: Delina, Wild Mage — "Roll a d20."
- **Example card**: Pixie Guide — "Grant an advantage: roll an additional die and choose the higher result."
- **Example card**: Wyll, Blade of Frontiers — "Whenever you roll one or more dice, Wyll gets +1/+1 until end of turn."

## Acceptance Criteria
- [ ] `roll_die(gs, player_name, sides)` returns a random integer from 1 to `sides`
- [ ] Supports d4, d6, d12, d20 (and any other die size)
- [ ] For human players: the roll is performed by the engine (random outcome)
- [ ] For AI players: auto-roll, deterministic with seed
- [ ] "Whenever you roll one or more dice" triggers fire
- [ ] Advantage: "roll an additional die and ignore the lowest" replacements
- [ ] Rerolls replace the previous result
- [ ] Range-based outcomes are determined by which range the result falls into
- [ ] Integration test: roll a d6, verify result is 1-6
- [ ] Integration test: roll a d20, verify range-based effect mapping
- [ ] Integration test: advantage — roll 2, take higher
- [ ] Integration test: die roll triggers fire
- [ ] Full regression suite passes

## Dependencies
- Random number generation (seeded for reproducibility)
- Replacement effects (for advantage/reroll)
- Trigger system (die roll triggers — story-trg-rolled-die.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No die roll implementation.

## Estimated Effort: S

# Story: Mana Cost / Mana Value (CR 107.4, 202)

## User Story
As a game engine developer, I want mana cost and mana value calculations to be accurate and consistent, so that the engine correctly computes the colored and generic mana requirements and total mana value for any card per CR 107 and CR 202.

## Context
Mana cost is the sequence of mana symbols required to cast a card. Mana value (formerly "converted mana cost" or CMC) is the total amount of mana in the mana cost, ignoring color. Mana cost includes colored mana symbols ({W}, {U}, {B}, {R}, {G}), generic mana symbols ({1}, {2}, etc.), hybrid mana ({W/U}, etc.), colorless mana ({C}), and phyrexian mana ({W/P}, etc.). The mana value is computed differently depending on which zone the card is in and what type of card it is.

### Comprehensive Rules Grounding
- **CR 107.4**: "Mana cost is the amount of mana required to cast a card."
- **CR 202.3**: "The mana value of an object is a number equal to the total amount of mana in its mana cost."
- **CR 202.3b**: "The mana value of a spell on the stack is determined by its mana cost, including any additional costs or alternative costs paid."
- **CR 202.3c**: "The mana value of a split card not on the stack is the sum of both halves' mana values."
- **CR 202.3d**: "The mana value of a double-faced card is based on the front face's mana cost unless specified otherwise."
- **Example card**: Sphinx's Revelation — mana cost {X}{W}{U}{U}, mana value = 3 + X

## Acceptance Criteria
- [ ] `calculate_mana_value(card, zone, context=None)` computes correct mana value for any card in any zone
- [ ] Standard cards: mana value = sum of all mana symbols in mana cost (CR 202.3)
- [ ] Split cards (not on stack): mana value = left + right halved total (CR 202.3c)
- [ ] Split card (on stack): mana value = cast half only
- [ ] Double-faced cards: mana value from front face unless transformed (CR 202.3d)
- [ ] X spells: mana value includes X as 0 in non-stack zones, X's value on stack
- [ ] Hybrid mana: counts as 1 toward mana value regardless of color choice
- [ ] Phyrexian mana: counts as 1 toward mana value
- [ ] Colorless mana ({C}): counts as 1 toward mana value
- [ ] `parse_mana_cost(mana_cost_string)` correctly parses mana costs into structured ManaCost objects
- [ ] Integration tests cover: standard calculation, X spells, hybrid, phyrexian, split cards, DFCs
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Split Cards / Fuse (CR 709) — split card mana value
- Story: Color Rules (CR 105) — color determination from mana cost

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
parse_mana_cost() handles WUBRG, generic, colorless {C}, snow {S}, hybrid, and Phyrexian symbols. But missing: calculate_mana_value() function, zone-dependent mana value (X=0 in non-stack, combined for split cards off-stack, half-only on stack), and comprehensive mana value calculation used by spell effects.

## Estimated Effort: M

## Notes
- Mana value is used extensively in the game: for counterspells ("counter target spell with mana value 3"), cascade, delve, and many other effects
- The engine likely already has partial mana cost parsing and mana value calculation — this story refactors it into a centralized system
- X spells in non-stack zones: X = 0 for mana value calculation (CR 202.3e)
- Hybrid mana symbols count as 1 toward mana value but contribute both colors to color identity
- {C} (colorless mana symbol) counts as 1 toward mana value but does NOT produce colored mana
- Snow mana {S} also counts as 1 toward mana value
- The ManaCost model should support: colored components, generic component, hybrid, phyrexian, snow, and X components

# Story: Color Rules (CR 105)

## User Story
As a game engine developer, I want card colors to be correctly determined from mana cost, color indicators, and color-setting effects, so that color-dependent mechanics (protection from color, color hosers, devotion) work per CR 105.

## Context
A card's color is determined by its mana cost (colored mana symbols), any color indicator (e.g., "Devoid — This card is colorless"), or effects that set or change color. Color matters for many game mechanics: protection (from color), color hosers ("destroy target black creature"), devotion, color identity, and color-based targeting restrictions.

### Comprehensive Rules Grounding
- **CR 105.1**: "The colors in Magic are white, blue, black, red, and green."
- **CR 105.2**: "An object's color is determined by its mana cost. Each colored mana symbol in the mana cost adds that color to the object's color."
- **CR 105.3**: "A color indicator on a card (e.g., a circle) sets the card's color, overriding the mana cost."
- **CR 105.4**: "Color-changing effects can change an object's color."
- **CR 105.5**: "Colorless objects have no color."
- **CR 105.6**: "Gold/multicolored objects have more than one color."
- **Example card**: Progenitus — "Protection from everything" — color is all five colors

## Acceptance Criteria
- [ ] `determine_color(card, game_state=None)` returns a list of colors for any card
- [ ] Default: color from mana cost — each colored mana symbol adds that color (CR 105.2)
- [ ] Color indicator overrides mana cost (CR 105.3) — e.g., devoid cards
- [ ] Color-setting effects are applied in layer 5 (CR 613.1e)
- [ ] Color-changing effects modify colors per layer system rules
- [ ] Colorless objects are identified correctly (no colored mana symbols, no color indicator, no color-setting effects)
- [ ] Gold/multicolor objects have multiple colors
- [ ] Hybrid mana symbols contribute both colors
- [ ] Color-dependent mechanics (protection, Devotion) use this color system
- [ ] Color is determined for all zones (battlefield, stack, hand, graveyard, library, exile, command zone)
- [ ] Integration tests cover: monocolor, multicolor, colorless, devoid (color indicator), color-changing effects, hybrid color contribution
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Layer System (CR 613) — color is determined in layer 5
- Story: Color Identity (CR 903.4) — color identity uses color plus mana symbols

## Priority: Medium

## Status: ❌ Not Implemented

### Gap Description
No central color determination system exists. Card.colors field exists on the model but there is no determine_color() function that derives color from mana cost, color indicators (devoid), or color-setting effects. Layer 5 in layers.py has basic 'is all colors'/'is colorless'/'enchanted creature is [color]' patterns, but these are ad-hoc. No systematic CR 105 color rules enforcement anywhere in the engine.

## Estimated Effort: M

## Notes
- Color is distinct from color identity (used in Commander deck construction)
- Mana symbols in rules text (e.g., "Sacrifice a creature: Add {B}{B}") do NOT contribute to the card's color, but DO contribute to color identity
- Color indicators are used primarily on cards with Devoid (which are colorless despite having colored mana costs) and on transforming double-faced cards
- The engine likely has partial color handling already — this story formalizes it
- Layer 5: color-changing effects like "target creature becomes black" change the color for all game purposes
- Protection from color uses the color system: "protection from black" means can't be damaged/targeted/blocked/enchanted by black sources

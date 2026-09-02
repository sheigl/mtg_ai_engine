# Story: Color Identity (CR 903.4)

## User Story
As a game engine developer, I want color identity to be correctly calculated for Commander and Brawl format validation, so that deck construction enforces the color identity rule per CR 903.4.

## Context
Color identity determines which cards can be included in Commander and Brawl decks. A card's color identity includes its own color(s) plus the colors of any mana symbols in its mana cost, rules text, AND characteristic-defining abilities. Basic lands have the color identity of the mana they produce. Color identity is NOT the same as color — a card can be colorless but have a non-empty color identity (e.g., artifacts with colored mana abilities).

### Comprehensive Rules Grounding
- **CR 903.4**: "A card's color identity is its color plus the color of any mana symbols in its mana cost or rules text."
- **CR 903.4a**: "The color identity of a card is determined by the colored mana symbols in its mana cost OR its rules text."
- **CR 903.4b**: "The color identity of a basic land is the color of the mana it produces (e.g., Plains is white)."
- **CR 903.4c**: "Cards with characteristic-defining abilities (e.g., "This card is white") have the colors defined by those abilities."
- **CR 903.4d**: "Color identity is always checked as a subset: a card can only go in a Commander deck if its color identity is a subset of the commander's color identity."
- **Example card**: Command Tower — "T: Add one mana of any color in your commander's color identity."

## Acceptance Criteria
- [ ] `calculate_color_identity(card) -> list[str]` computes color identity for any card
- [ ] Color identity includes: colors from mana cost + colors from mana symbols in rules text (CR 903.4a)
- [ ] Basic lands: color identity = color of mana produced (CR 903.4b)
- [ ] Extort ({W/B} symbol in rules text but not mana cost) adds to color identity
- [ ] Color identity validation: card's CI must be a subset of commander's CI (CR 903.4d)
- [ ] Split cards: both halves' color identities combine
- [ ] Double-faced cards: both faces' color identities combine (for Commander purposes)
- [ ] Hybrid mana symbols contribute both colors to color identity
- [ ] Phyrexian mana symbols contribute their color to color identity
- [ ] Colorless cards with colored activated abilities (e.g., artifacts with {B}: ability) have the colored identity
- [ ] Integration tests cover: monocolor, multicolor, colorless-with-identity, basic lands, hybrid, phyrexian, extort, split cards, DFCs
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Color Rules (CR 105) — color identity is built on color rules
- Story: Format Rules (FMT-01) — deck validation uses color identity

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
get_color_identity() in formats/commander.py derives color identity from mana cost and rules text. Deck validation enforces color identity for Commander. But missing: basic land color identity assignment (Plains=W, etc.), hybrid/phyreyan symbol expansion to both colors, extort symbol detection, and comprehensive color identity testing.

## Estimated Effort: M

## Notes
- Color identity is the #1 most important rule for Commander format validation
- Key distinction from color: a card can be colorless (no colored mana in cost) but have a color identity (colored mana symbols in rules text)
- Example: some artifacts have "{W}: ..." abilities — they're colorless artifacts but have white color identity
- The engine already has `get_color_identity()` as a fallback in `commander.py` and `deck_builder.py` — this story refactors it to a first-class system
- Transformed DFC: both sides' color identities count (e.g., Nicol Bolas, the Ravager transforms to a planeswalker with Grixis identity)
- Commander color identity check: the deck can only contain cards whose CI is a subset of the commander's CI
- Partner: each partner's CI is checked independently; the combined CI is the union of both partners' identities for the deck's allowed colors

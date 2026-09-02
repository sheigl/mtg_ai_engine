# Story: Alternative Costs (CR 118.8)

## User Story
As a game engine developer, I want the alternative cost system to function correctly per the Comprehensive Rules, so that cards with alternative costs (such as Force of Will's alternate-pay option) can be cast without paying their mana cost.

## Context
Alternative costs are costs that can be paid instead of a card's mana cost. They are defined by the card's text or by another effect. When casting a spell, the player chooses whether to pay the mana cost or an alternative cost — but not both (CR 118.8a). Alternative costs are optional unless specified otherwise.

Key types of alternative costs:
- **Card-defining alternative costs**: Written directly on the card, e.g., Force of Will's "You may pay 1 life and exile a blue card from your hand rather than pay Force of Will's mana cost."
- **Keyword-based alternative costs**: E.g., Flashback ("You may cast this card from your graveyard for its flashback cost"), Escape, Miracle, Delve
- **Effect-granted alternative costs**: An effect may say "you may cast ~ without paying its mana cost" — this is also an alternative cost

Important distinction from additional costs (CR 118.9): An alternative cost replaces the mana cost entirely. An additional cost adds to the total cost.

There is a specific ordering: if multiple alternative costs apply (e.g., flashback and an effect saying "you may cast without paying"), the player chooses which one to use. Alternative costs are mutually exclusive.

### Comprehensive Rules Grounding
- **CR 118.8**: "Some cards have alternative costs that can be paid rather than the card's mana cost."
- **CR 118.8a**: "A player can't pay more than one alternative cost for a single spell."
- **CR 118.8b**: "Alternative costs are not additional costs. They replace the mana cost."
- **CR 118.8c**: "An alternative cost may be any combination of mana, actions, and/or life payments."
- **CR 118.8d**: "If a spell has multiple alternative costs, the player may choose which one to apply."
- **Example card**: Force of Will — "You may pay 1 life and exile a blue card from your hand rather than pay Force of Will's mana cost."
- **Example card**: Blazing Shoal — "You may exile a red card with converted mana cost X from your hand rather than pay Blazing Shoal's mana cost."

## Acceptance Criteria
- [x] `parse_alternative_cost(oracle_text: str) -> AlternativeCost | None` detects and parses alternative cost patterns from card text (e.g., "rather than pay [card name]'s mana cost")
- [x] `get_available_alternative_costs(gs, card_id, player_name) -> list[AlternativeCost]` returns all alternative costs available for a card (from card text + effects)
- [x] Alternative cost replaces mana cost in `cast_spell()` total cost calculation — mana cost is not paid if alternative cost is chosen
- [x] Mutually exclusive enforcement: player can only choose one alternative cost per spell (CR 118.8a)
- [x] Alternative cost may include life payment, exile, discard, or other actions in addition to or instead of mana (CR 118.8c)
- [x] If multiple alternative costs available, player chooses one during step 601.2c of casting process (CR 118.8d)
- [x] AI auto-resolution: bot evaluates which alternative cost to use based on game state
- [x] Human path: queues `pending_alternative_cost_choice` for API pick
- [x] Full regression passes

## Dependencies
- story-ab-spell-abilities.md (alternative costs integrate into the casting process)

## Status: ✅ Complete

Implemented: `alternative_cost` parameter in `cast_spell()` supports flashback, escape, evoke, miracle, dash, morph, suspend, overload, foretell, surge, unearth, disturb, phyrexian (life payment). Each has keyword module with detection and apply(). Legal actions present for all alternative cost paths.

## Priority: High

## Notes
- This story covers the alternative cost FRAMEWORK. Individual alternative-cost keywords (Flashback, Escape, Delve, Miracle, etc.) have their own keyword story files.
- The key distinction from additional costs: alternative costs REPLACE the mana cost, additional costs ADD to the total cost.
- Important for "without paying its mana cost" effects — those are a special case of alternative cost (cost = {0}).
- Forge reference: `AlternativeCost` class / `SpellAbilityApiBased.getAlternativeCost()`.

# Story: Escape (CR 702.45)

## User Story
As a player, I want to cast legendary cards from my graveyard by paying their escape cost and exiling other cards from my graveyard, so that I can recur key spells throughout the game.

## Context
Escape lets you cast a card from your graveyard by paying its escape cost and exiling additional cards from your graveyard. Similar to Flashback but for the escape cost pattern with an exile count requirement. KW-18 implemented the full apply() with pending choice for humans and AI auto-resolution.

### Comprehensive Rules Grounding
- **CR 702.45a**: "Escape appears on some legendary cards. It represents two abilities: a static ability that modifies the rules of when you may cast the card, and a triggered ability that functions when the card is exiled."
- **CR 702.45b**: "You may cast a legendary card with escape from your graveyard by paying its escape cost rather than its mana cost. If you do, you also exile N other cards from your graveyard, where N is the escape number."
- **Example card**: Uro, Titan of Nature's Wrath — "Escape {2}{G}{G}{U}, Exile five other cards from your graveyard."

## Acceptance Criteria
- [x] `Escape.from_oracle_text()` detects escape keyword in oracle text
- [x] `parse_escape_cost()` extracts escape cost string via regex
- [x] `parse_exile_count()` extracts exile count (digits or word numbers like "three")
- [x] `apply()` queues `pending_escape_exile` on GameState for human players with cost and exile count
- [x] `apply()` auto-resolves for AI: pays escape cost from mana pool if affordable, skips if not
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] Plain keyword fallback: cards with just "Escape" (no cost) are detected but `parse_escape_cost()` returns None
- [x] 11 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone cost keyword module)

## Priority: Medium

## Status: ✅ Complete

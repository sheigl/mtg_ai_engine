# Story: Flashback (CR 702.34)

## User Story
As a player, I want to cast spells from my graveyard by paying their flashback cost, then exile them instead of putting them anywhere else, so that I get a second use from key spells.

## Context
Flashback gives an alternate way to cast a spell from the graveyard. Pay the flashback cost, then exile the card instead of discarding or putting it anywhere else. KW-17 implemented the full apply() with pending choice for humans and AI auto-resolution based on mana affordability.

### Comprehensive Rules Grounding
- **CR 702.34a**: "Flashback appears on some instants and sorceries. It represents two abilities: a static ability that modifies the rules of when you may cast the card, and a triggered ability that functions when the card is exiled."
- **CR 702.34c**: "If you cast a spell with flashback from your graveyard, you may pay its flashback cost rather than its mana cost. If you do, exile it instead of putting it anywhere else."
- **Example card**: Snapcaster Mage — "Target sorcery card in your graveyard gains flashback until end of turn. The flashback cost is equal to its mana cost."

## Acceptance Criteria
- [x] `Flashback.from_oracle_text()` detects flashback keyword in oracle text
- [x] `parse_flashback_cost()` extracts flashback cost string via regex
- [x] `apply()` queues `pending_flashback_exile` on GameState for human players
- [x] `apply()` auto-resolves for AI: pays flashback cost from mana pool if affordable, skips if not
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] No-op guard: cards without parseable flashback cost return unchanged state
- [x] Mana payment handles colored mana first, generic from remaining pool
- [x] 10 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone cost keyword module)

## Priority: Medium

## Status: ✅ Complete

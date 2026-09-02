# Story: Dredge (CR 702.60)

## User Story
As a player, I want to replace card draws by putting N cards from my library into my graveyard and returning a dredge card from my graveyard to my hand, so that graveyard-centric decks can fill their graveyard while drawing key cards.

## Context
Dredge N replaces a card draw: you may put N cards from your graveyard into your library instead of drawing a card. If you do, return the dredge card from your graveyard to your hand. KW-23 implemented the full apply() with pending choice for humans and AI auto-resolution.

### Comprehensive Rules Grounding
- **CR 702.60a**: "Dredge is a static ability that functions only while the card with dredge is in a player's graveyard. 'Dredge N' means 'As long as this card is in your graveyard, you may instead put the top N cards of your library into your graveyard. If you do, return this card from your graveyard to your hand.'"
- **CR 702.60b**: "A player who would draw a card may put the top N cards of their library into their graveyard instead, then return the card with dredge to their hand."
- **Example card**: Golgari Grave-Troll — "Dredge 6 (If you would draw a card, you may mill 6 instead and return this card from your graveyard to your hand.)"

## Acceptance Criteria
- [x] `Dredge.from_oracle_text()` detects dredge keyword in oracle text
- [x] `parse_dredge_value()` extracts N from "Dredge N" pattern
- [x] `apply()` queues `pending_dredge_choice` on GameState for human players with dredge_n
- [x] `apply()` auto-resolves for AI: checks library size >= dredge_n, returns card to hand if enough
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] No-op guard: cards without Dredge keyword, or with no parseable value
- [x] 9 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone keyword module, called during draw replacement)

## Priority: Medium

## Status: ✅ Complete

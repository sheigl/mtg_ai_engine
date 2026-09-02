# Story: Delve (CR 702.86)

## User Story
As a player, I want to exile cards from my graveyard to help pay for a spell's mana cost, so that delve spells become cheaper to cast the more cards I have in my graveyard.

## Context
Delve allows exiling cards from your graveyard to help pay for a spell's mana cost. Each card exiled reduces the generic mana cost by {1}. KW-19 implemented the full apply() with pending choice for humans and AI auto-resolution.

### Comprehensive Rules Grounding
- **CR 702.86a**: "Delve is a static ability that functions while the spell is on the stack. 'Delve' means 'You may exile any number of cards from your graveyard. Each card you exile from your graveyard while casting this spell pays for {1}.'"
- **CR 702.86b**: "The number of cards that can be exiled to pay for a spell with delve is limited only by the spell's total cost and the number of cards in your graveyard."
- **Example card**: Treasure Cruise — "Delve (Each card you exile from your graveyard while casting this spell pays for {1}.)"

## Acceptance Criteria
- [x] `Delve.from_oracle_text()` detects delve keyword in oracle text
- [x] `parse_delve_cost()` extracts optional explicit delve cost from oracle text
- [x] `parse_delve_count()` extracts exile count (digits or word numbers)
- [x] `apply()` queues `pending_delve_choice` on GameState for human players with cards_to_exile limit
- [x] `apply()` auto-resolves for AI: selects graveyard cards up to generic_cost, sets resolved=True
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] No-op guard: cards without Delve keyword, or with no generic mana cost
- [x] Bugfixes applied: multi-part cost regex, word number parsing, early-return guard
- [x] 10 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone cost keyword module)

## Priority: Medium

## Status: ✅ Complete

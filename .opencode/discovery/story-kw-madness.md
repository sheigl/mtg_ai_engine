# Story: Madness (CR 702.35)

## User Story
As a player, I want to cast cards I discard for their madness cost instead of putting them into the graveyard, so that discard outlets become beneficial instead of detrimental.

## Context
Madness is a replacement effect that applies when a player would discard a card with madness. Instead of being put into the graveyard, it's exiled and may be cast for its madness cost. KW-22 implemented the full apply() with pending choice for humans and AI auto-resolution.

### Comprehensive Rules Grounding
- **CR 702.35a**: "Madness is a keyword that represents two abilities: a static ability and a triggered ability. The static ability is 'If you would discard this card, you may discard it into exile instead.' The triggered ability is 'When you discard this card into exile, you may cast it by paying its madness cost.'"
- **CR 702.35b**: "If you cast a spell with madness from exile, you may pay its madness cost rather than its mana cost. If you don't, the card is put into your graveyard."
- **Example card**: Fiery Temper — "Madness {R} (If you discard this card, discard it into exile. When you do, cast it for its madness cost or put it into your graveyard.)"

## Acceptance Criteria
- [x] `Madness.from_oracle_text()` detects madness keyword in oracle text
- [x] `parse_madness_cost()` extracts madness cost string via regex
- [x] `apply()` queues `pending_madness_choice` on GameState for human players with cost details
- [x] `apply()` auto-resolves for AI: pays madness cost from mana pool if affordable, skips if not
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] No-op guard: cards without parseable madness cost return unchanged state
- [x] Colored mana cost payment handled correctly
- [x] 10 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone cost keyword module)

## Priority: Medium

## Status: ✅ Complete

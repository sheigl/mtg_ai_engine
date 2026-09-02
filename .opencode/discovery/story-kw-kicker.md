# Story: Kicker (CR 702.33)

## User Story
As a player, I want to pay an optional additional cost (kicker) when casting spells, so that kicked spells have enhanced effects as described on the card.

## Context
Kicker is an additional optional cost that may be paid as the spell is cast. If paid, the spell has enhanced effects (tracked by `kicked=True` flag). KW-16 implemented the full apply() with pending choice for humans and AI auto-resolution based on mana affordability.

### Comprehensive Rules Grounding
- **CR 702.33a**: "Kicker is a static ability that functions while the spell is on the stack. 'Kicker [cost]' means 'You may pay an additional [cost] as you cast this spell.'"
- **CR 702.33c**: "If a spell's controller pays the kicker cost, that spell has been 'kicked.'"
- **Example card**: Verazol, the Split Current — "Kicker {1}"

## Acceptance Criteria
- [x] `Kicker.from_oracle_text()` detects kicker keyword in oracle text
- [x] `parse_kicker_cost()` extracts kicker cost string via regex
- [x] `apply()` queues `pending_kicker_choice` on GameState for human players with cost details
- [x] `apply()` auto-resolves for AI: pays kicker cost from mana pool if affordable, skips if not
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] No-op guard: cards without Kicker keyword return unchanged state
- [x] 10 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone cost keyword module)

## Priority: Medium

## Status: ✅ Complete

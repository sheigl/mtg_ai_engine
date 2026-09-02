# Story: Dash (CR 702.138)

## User Story
As a player, I want to cast creatures for their dash cost to give them haste and have them return to my hand at end step, so that I can make surprise attacks without losing card advantage.

## Context
Dash {cost} is an alternative cost to cast a creature spell. If paid, the creature gains haste and is returned to its owner's hand at the beginning of the next end step. KW-25 implemented the full apply() with pending choice for humans and AI auto-resolution.

### Comprehensive Rules Grounding
- **CR 702.138a**: "Dash is an alternative cost that may be paid rather than a spell's mana cost. A creature cast using its dash cost gains haste and is returned to its owner's hand at the beginning of the next end step."
- **CR 702.138b**: "At the beginning of the next end step, return the creature to its owner's hand."
- **Example card**: Lightning Berserker — "Dash {R} (You may cast this spell for its dash cost. If you do, it gains haste, and it's returned from the battlefield to its owner's hand at the beginning of the next end step.)"

## Acceptance Criteria
- [x] `Dash.from_oracle_text()` detects dash keyword in oracle text
- [x] `parse_dash_cost()` extracts dash cost string via regex
- [x] `apply()` queues `pending_dash_choice` on GameState for human players
- [x] `apply()` auto-resolves for AI: pays dash cost if affordable, adds haste keyword, tracks in `dashed_creatures`
- [x] `handle_dash_return_to_hand()` returns dashed creatures to owner's hand at end step (CR 702.138b)
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] 8 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone keyword module, called during casting and end step)

## Priority: Medium

## Status: ✅ Complete

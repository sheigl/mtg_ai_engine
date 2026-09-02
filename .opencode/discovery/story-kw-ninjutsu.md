# Story: Ninjutsu (CR 702.61)

## User Story
As a player, I want to return an unblocked attacking creature to my hand and put a ninja creature from my hand onto the battlefield tapped and attacking, so that ninja creatures can ambush opponents during combat.

## Context
Ninjutsu {cost} is an activated ability. Return an unblocked attacking creature you control to its owner's hand, then put this card from your hand onto the battlefield tapped and attacking the same target. KW-24 implemented the full apply() with pending choice for humans and AI auto-resolution.

### Comprehensive Rules Grounding
- **CR 702.61a**: "Ninjutsu is an activated ability that functions only while the card with ninjutsu is in a player's hand. '{Cost}: Return an unblocked attacking creature you control to its owner's hand. If you do, put this card onto the battlefield from your hand tapped and attacking the same player or planeswalker.'"
- **CR 702.61b**: "The creature returned to its owner's hand must be an unblocked attacking creature you control."
- **Example card**: Ninja of the Deep Hours — "Ninjutsu {1}{U} ({1}{U}, Return an unblocked attacker you control to hand: Put this card onto the battlefield from your hand tapped and attacking.)"

## Acceptance Criteria
- [x] `Ninjutsu.from_oracle_text()` detects ninjutsu keyword in oracle text
- [x] `parse_ninjutsu_cost()` extracts ninjutsu cost string via regex
- [x] `apply()` queues `pending_ninjutsu_choice` on GameState for human players with attacker info
- [x] `apply()` auto-resolves for AI: finds unblocked attacker, returns to hand, puts ninja on battlefield tapped and attacking
- [x] All state transforms use `model_copy(update={...})` — no direct mutations
- [x] No-op guard: cards without Ninjutsu keyword return unchanged state
- [x] `apply_ninjutsu()` module-level convenience function for external callers
- [x] 6 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone keyword module, called during combat)

## Priority: Medium

## Status: ✅ Complete

# Story: Hexproof (CR 702.11)

## User Story
As a player, I want my hexproof creatures and permanents to be untargetable by opponents' spells and abilities, so that I can protect key pieces from removal.

## Context
Hexproof is a static ability that prevents targeting. A permanent or player with hexproof can't be the target of spells or abilities that an opponent controls. The controller may still target their own hexproof permanents. KW-29 implemented query helpers for passive keyword targeting validation.

### Comprehensive Rules Grounding
- **CR 702.11b**: "A permanent or player with hexproof can't be the target of spells or abilities that players other than its controller control."
- **Example card**: Slippery Bogle — "Hexproof (This creature can't be the target of spells or abilities your opponents control.)"

## Acceptance Criteria
- [x] `Hexproof.has_hexproof()` correctly detects hexproof keyword
- [x] `Hexproof.from_oracle_text()` detects hexproof in oracle text
- [x] `Hexproof.can_be_targeted()` returns True for non-hexproof, or same controller
- [x] `is_hexproof(gs, perm_id_or_player_name)` query helper checks permanent/player on battlefield
- [x] `can_target_hexproof(gs, target, source_controller)` returns True if targeting is legal
- [x] `_find_target_controller()` resolves permanent ID or player name to controller
- [x] Query helpers are pure functions (no state mutation)
- [x] 7 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone passive keyword)

## Priority: Medium

## Status: ✅ Complete

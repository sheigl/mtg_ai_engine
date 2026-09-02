# Story: Shroud (CR 702.18)

## User Story
As a player, I want my shrouded creatures and permanents to be completely untargetable by any spell or ability, including my own, so that only global effects can affect them.

## Context
Shroud is a static ability that prevents all targeting. A permanent or player with shroud can't be the target of any spell or ability, regardless of who controls it. Unlike hexproof, even the controller cannot target their own shrouded permanents. KW-30 implemented query helpers.

### Comprehensive Rules Grounding
- **CR 702.18b**: "A permanent or player with shroud can't be the target of spells or abilities."
- **Example card**: Lightning Greaves — "Equipped creature has shroud. (It can't be the target of spells or abilities.)"

## Acceptance Criteria
- [x] `Shroud.has_shroud()` correctly detects shroud keyword
- [x] `Shroud.from_oracle_text()` detects shroud in oracle text
- [x] `Shroud.can_be_targeted()` returns False for shrouded permanents regardless of controller
- [x] `is_shrouded(gs, perm_id_or_player_name)` query helper checks permanent/player on battlefield
- [x] `can_target_shrouded(gs, target_id_or_player_name)` returns False if target has shroud
- [x] Query helpers are pure functions (no state mutation)
- [x] 7 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone passive keyword)

## Priority: Medium

## Status: ✅ Complete

# Story: Reach (CR 702.17)

## User Story
As a player, I want creatures with reach to be able to block flying creatures, so that non-flying creatures with reach can defend against aerial attackers.

## Context
Reach is a static ability that modifies blocking rules. A creature with reach can block creatures with flying, ignoring the normal restriction that only flying creatures can block flying creatures. KW-28 implemented query helpers for passive keyword blocking validation.

### Comprehensive Rules Grounding
- **CR 702.17b**: "Creatures with flying or reach can block creatures with flying, ignoring the normal restriction that only flying creatures can block flying creatures."
- **Example card**: Giant Spider — "Reach (This creature can block creatures with flying.)"

## Acceptance Criteria
- [x] `Reach.has_reach()` correctly detects reach keyword in keyword list
- [x] `Reach.from_oracle_text()` detects reach in oracle text
- [x] `Reach.can_block_flying()` returns True if blocker has flying or reach
- [x] `has_reach(gs, perm_id)` query helper checks battlefield permanent for reach
- [x] `can_block_flying(gs, blocker_perm_id)` query helper checks if blocker can block flying
- [x] Query helpers are pure functions (no state mutation)
- [x] 8 integration tests pass in `test_keywords_integration.py`

## Dependencies
- None (standalone passive keyword)

## Priority: Medium

## Status: ✅ Complete

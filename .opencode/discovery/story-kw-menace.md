# Story: Menace (CR 702.111)

## User Story
As a player, I want creatures with menace to require two or more blockers, so that they are harder to block and can push damage through more effectively.

## Context
Menace is a static ability that modifies blocking rules. A creature with menace can't be blocked except by two or more creatures. KW-31 implemented query helpers for passive keyword blocking validation with comprehensive unit and integration tests.

### Comprehensive Rules Grounding
- **CR 702.111b**: "An attacking creature with menace can't be blocked unless it's blocked by two or more creatures."
- **Example card**: Goblin War-Paint — "Menace (This creature can't be blocked except by two or more creatures.)"

## Acceptance Criteria
- [x] `Menace.has_menace()` correctly detects menace keyword
- [x] `Menace.from_oracle_text()` detects menace in oracle text
- [x] `Menace.min_blockers()` returns 2 as minimum blocker count
- [x] `Menace.is_block_legal()` checks if blocking declaration is legal given menace
- [x] `is_menacing(gs, perm_id)` query helper checks battlefield permanent for menace
- [x] `can_block_menacing(gs, attacker_perm_id, blocker_perm_ids)` validates blocker tally against menace requirement
- [x] Query helpers are pure functions (no state mutation)
- [x] 12 unit tests + 5 integration tests pass

## Dependencies
- None (standalone passive keyword)

## Priority: Medium

## Status: ✅ Complete

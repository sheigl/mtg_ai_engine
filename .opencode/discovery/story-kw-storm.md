# Story: Storm (CR 702.40)

## User Story
As a player, I want my storm spells to create copies for each spell cast before them this turn, so that storm combo decks can generate massive value from chaining spells.

## Context
Storm is a triggered ability that copies the spell for each other spell cast before it this turn. Copies are put on the stack in LIFO order so they resolve first. The storm count equals `spells_cast_this_turn - 1`. Implements real `apply()` with `model_copy` pure transforms.

### Comprehensive Rules Grounding
- **CR 702.40a**: "Storm is a triggered ability that functions on the stack. 'Storm' means 'When you cast this spell, you may copy it for each other spell that was cast before it this turn. If you do, you may choose new targets for the copies.'"
- **CR 702.40b**: "The number of copies is equal to the number of spells cast before the storm spell this turn."
- **Example card**: Grapeshot — "Storm (When you cast this spell, copy it for each spell cast before it this turn. You may choose new targets for the copies.)"

## Acceptance Criteria
- [x] `Storm.has_storm()` correctly detects storm keyword
- [x] `Storm.from_oracle_text()` detects storm in oracle text
- [x] `Storm.get_storm_count()` returns `spells_cast_this_turn` value
- [x] `create_storm_copies()` creates N = (spells_cast_this_turn - 1) copies on stack via pure `model_copy`
- [x] Copies are appended in LIFO order (last added resolves first)
- [x] Each copy has unique ID and `is_copy=True` flag
- [x] No-op when storm count is 0 (first spell of turn) or stack object not found
- [x] Pure transform: returns new GameState without mutating original
- [x] Unit tests in `tests/ability/keywords/test_storm.py` and integration tests in `tests/engine/test_keywords_integration.py`

## Dependencies
- None (standalone triggered keyword, called during spell resolution)

## Priority: Medium

## Status: ✅ Complete

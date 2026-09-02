# Story: Afterlife Death Trigger (CR 702.108)

## User Story
As a player, I want creatures with afterlife to create Spirit tokens when they die, so that afterlife cards generate board presence even when removed.

## Context
Afterlife N means "When this permanent dies, create N 0/0 white Spirit creature tokens with afterlife 1." Each token has afterlife 1, enabling chain reactions. Story #4a implemented as a stack-based death trigger with `resolve_trigger()` using pure transforms.

### Comprehensive Rules Grounding
- **CR 702.108b**: "'Afterlife N' means 'When this permanent dies, create N 0/0 white Spirit creature tokens with afterlife 1.'" (Tokens have dying trigger abilities.)
- **Example card**: Doomed Traveler — "Afterlife 1 (When this creature dies, create a 1/1 white Spirit creature token with flying.)"

## Acceptance Criteria
- [x] Afterlife triggers are wired into `_on_zone_change()` in `triggers.py` via the keyword module's `create_trigger()` method, matching "dies" events (battlefield → graveyard)
- [x] `resolve_trigger()` creates N 0/0 white Spirit creature tokens with `afterlife` keyword via pure `model_copy` transforms
- [x] Created tokens have correct type line ("Creature — Spirit"), power/toughness "0/0", and afterlife keyword
- [x] Afterlife count parsed from oracle text (e.g., "Afterlife 2" creates 2 tokens)
- [x] Cards with plain "Afterlife" keyword default to 1 token
- [x] Trigger does NOT fire when creature is exiled (only on death)
- [x] Created tokens with afterlife 1 correctly trigger their own afterlife on death (chain reaction)
- [x] Token guard (CR 704.5d) prevents token death triggers
- [x] 9 integration tests pass in `tests/engine/test_afterlife_integration.py`

## Dependencies
- None (independent death trigger keyword)

## Priority: High

## Status: ✅ Complete

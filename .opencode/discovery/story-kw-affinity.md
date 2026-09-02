# Story: Affinity (CR 702.41)

## User Story
As an MTG engine developer, I want a new affinity keyword module with real apply() and integration tests, so that cards with affinity for {quality} work correctly in the engine.

## Context
No file exists for affinity. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.41a**: "Affinity is a static ability that functions while the spell with affinity is on the stack. 'Affinity for [quality]' means 'This spell costs you {1} less to cast for each [quality] you control.'"
- **Example card**: Thoughtcast — "Affinity for artifacts (This spell costs {1} less to cast for each artifact you control.)"
- **Rule source**: Cost reduction static ability on the stack

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/affinity.py` with `Affinity` class extending `CostKeyword`
- [ ] `parse_affinity_quality(oracle_text) -> str | None` detects the quality (artifacts, instants, etc.)
- [ ] `apply()` reduces the spell's casting cost by {1} per controlled permanent matching the quality
- [ ] Cost reduction is computed based on `game_state.battlefield` count of matching permanents
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic affinity for artifacts, multi-quality affinity, zero-cost reduction when none controlled, type-specific affinity
- [ ] Plain keyword fallback: "Affinity" without a quality defaults to affinity for artifacts
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: S

## Notes
- Cost reduction applies only while the spell is on the stack; quality count snapshots at announcement time
- Quality can be "artifacts", "creatures", "instants", "sorceries", "lands", etc.
- Must integrate with the mana payment flow in `stack.py` during spell announcement

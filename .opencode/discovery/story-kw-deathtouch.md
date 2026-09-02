# Story: Deathtouch (CR 702.2)

## User Story
As a player, I want creatures with deathtouch to deal lethal damage with any nonzero damage amount, so that deathtouch creatures destroy creatures they damage regardless of toughness.

## Context
Deathtouch is a static ability that modifies how combat damage marking works. Any nonzero damage from a source with deathtouch is considered lethal damage, destroying the damaged creature via state-based actions (CR 704.5h). Refactored to pure transforms during P0 Combat Modifiers refactoring.

### Comprehensive Rules Grounding
- **CR 702.2b**: "Any nonzero amount of combat damage assigned to a creature by a source with deathtouch is considered to be lethal damage, regardless of that creature's toughness."
- **CR 702.2c**: "Damage from a source with deathtouch is considered to be lethal damage, regardless of the damage dealt."
- **Example card**: Typhon Grace (or any deathtouch creature) — "Deathtouch"

## Acceptance Criteria
- [x] `has_deathtouch()` / `has_deathtouch_perm()` query helpers correctly detect the keyword
- [x] `is_lethal()` returns True for any damage > 0 when source has deathtouch
- [x] `min_lethal_damage()` returns 1 for deathtouch sources
- [x] `apply_deathtouch_damage()` applies `__deathtouch_damage__` counter marker via pure `model_copy` transform — no direct mutations
- [x] `apply_deathtouch_damage_from_card()` wrapper handles stack.py call sites without a Permanent object
- [x] No-op for zero damage, non-deathtouch sources, planeswalker targets
- [x] Integrated into `combat/core.py`, `stack.py`, and `replacement.py` damage flows
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone passive keyword, wired into damage resolution pipeline)

## Priority: High

## Status: ✅ Complete

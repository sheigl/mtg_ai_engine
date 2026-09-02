# Story: Lifelink (CR 702.15)

## User Story
As a player, I want creatures with lifelink to grant me life equal to the damage they deal, so that lifelink creatures provide incremental life gain during combat and spell damage.

## Context
Lifelink is a static ability that causes its controller to gain life equal to the damage dealt by the source. Applies equally to combat damage and non-combat damage. Refactored to pure transforms during P0 Combat Modifiers refactoring.

### Comprehensive Rules Grounding
- **CR 702.15b**: "Damage dealt by a source with lifelink causes that source's controller, or its owner if it has no controller, to gain that much life (in addition to any other results that damage causes)."
- **Example card**: Ajani's Pridemate — "Lifelink" (triggers on life gain)

## Acceptance Criteria
- [x] `has_lifelink()` / `has_lifelink_perm()` query helpers correctly detect the keyword
- [x] `apply_lifelink_gain()` correctly computes new life total = old_life + damage
- [x] `apply_lifelink_to_gamestate()` applies life gain to the source's controller via pure `model_copy` transform
- [x] `apply_lifelink_from_card()` handles stack.py call sites without a Permanent object
- [x] No-op for zero/negative damage, non-lifelink sources
- [x] Integrated into `combat/core.py`, `stack.py`, and `replacement.py` damage flows with correct controller attribution
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone passive keyword, wired into damage resolution pipeline)

## Priority: High

## Status: ✅ Complete

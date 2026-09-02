# Story: Infect (CR 702.90)

## User Story
As a player, I want creatures with infect to deal damage to creatures as -1/-1 counters and to players as poison counters, so that the alternate damage model of infect/phyrexian strategy works correctly.

## Context
Infect is a static ability that modifies how damage is dealt: creatures get -1/-1 counters instead of marked damage, players get poison counters instead of life loss. Also covers Wither (CR 702.129) and Poisonous (CR 702.118). Refactored to pure transforms during P0 Combat Modifiers refactoring.

### Comprehensive Rules Grounding
- **CR 702.90b**: "Damage dealt to a creature by a source with infect is dealt in the form of -1/-1 counters."
- **CR 702.90c**: "Damage dealt to a player by a source with infect causes that player to get that many poison counters."
- **CR 702.129** (Wither): Creatures get -1/-1 counters, but players take normal damage.
- **CR 702.118** (Poisonous N): "Whenever this creature deals combat damage to a player, that player gets N poison counters."
- **Example card**: Blightsteel Colossus — "Infect, trample"

## Acceptance Criteria
- [x] `InfectKeyword`, `WitherKeyword`, `PoisonousKeyword` classes with detection and apply methods
- [x] `apply_infect_damage_to_creature()` adds -1/-1 counters via pure `model_copy` transform
- [x] `apply_infect_poison_to_player()` adds poison counters via pure `model_copy` transform, checks 10+ poison loss condition
- [x] `apply_infect_from_card()` handles stack.py call sites without a Permanent object
- [x] Wither handles creatures (-1/-1 counters) but not players (normal life loss)
- [x] Poisonous N applies N poison counters on combat damage to a player
- [x] No-op for zero damage, non-infect/wither sources
- [x] Integrated into `combat/core.py`, `stack.py`, and `replacement.py` damage flows
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone passive keyword, wired into damage resolution pipeline)

## Priority: High

## Status: ✅ Complete

# Story: Flanking (CR 702.25)

## User Story
As an MTG engine developer, I want the flanking keyword module to have a real `apply()` implementation with integration tests, so that cards with flanking produce correct game state instead of silently no-op'ing.

## Context
The flanking keyword module exists with detection/parsing logic and a helper `apply_flanking()` method. However, `apply()` delegates to `apply_flanking()` which directly mutates `blocked.power_bonus -= 1` and `blocked.toughness_bonus -= 1`. Must refactor to pure transforms.

### Comprehensive Rules Grounding
- **CR 702.25**: "Flanking is a triggered ability that triggers when a creature with flanking becomes blocked by a creature without flanking. The blocking creature gets -1/-1 until end of turn."
- **Example card**: Knight of the Mists — "Flanking"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
Combat-triggered ability. Wires into declare-blockers step in combat/core.py. If blocker has flanking and attacker doesn't, attacker gets -1/-1 until end of turn. Uses `power_bonus`/`toughness_bonus` and `power_bonus_expires`/`toughness_bonus_expires` on Permanent. Must use `model_copy(update={...})` on permanent, player, and game state.

# Story: Monarch (CR 702.147) — MON-01

## User Story
As a player, I want the Monarch mechanic fully implemented — becoming monarch, combat damage transfer, and end-step draw — so that cards like Palace Sentinels and Throne of the High City work correctly.

## Context
**Status: ✅ Complete**

Implemented as MON-01. Full CR 702.147 Monarch logic with pure transforms:

- **`set_monarch(gs, player_name)`**: Sets monarch, fires `become_monarch` pending trigger for monarch-matters cards. Pure `model_copy()` transform.
- **`is_monarch(gs, player_name)`**: Query helper for "if you're the monarch" card effects.
- **`handle_end_step_draw(gs)`**: At beginning of end step, if active player is monarch, they draw a card.
- **`check_combat_damage_monarch(gs, target_player, attacker_controller)`**: If combat damage dealt to monarch, attacker's controller becomes new monarch.
- **Game Initialization**: `monarch=active_player` for commander/conspiracy formats; `None` otherwise.

## Acceptance Criteria
- [x] `set_monarch()` returns new GameState via model_copy; fires `become_monarch` trigger
- [x] `is_monarch()` query helper for card effect conditions
- [x] End-step draw: monarch draws 1 card at end of their own turn
- [x] Combat damage transfer: dealing combat damage to monarch transfers it to attacker's controller
- [x] Game initialization sets monarch for commander/conspiracy formats
- [x] Wired into `combat/core.py` (combat damage hook) and `turn_manager.py` (end step hook)
- [x] Pre-existing dead code fix: moved unreachable combat_damage trigger detection into correct check function
- [x] 35 tests (14 unit + 21 integration) covering transfer, draw, triggers, edge cases

## Dependencies
- None (standalone module)

## Priority: High | Effort: Completed ✅

## Notes
- Key file: `mtg_engine/engine/monarch.py` (90 lines)
- Integration tests: `tests/engine/test_monarch_integration.py`, `tests/engine/test_monarch_qa.py`
- Unit tests: `tests/engine/test_monarch.py`
- `is_monarch()` used by card effects referencing "if you're the monarch" conditions

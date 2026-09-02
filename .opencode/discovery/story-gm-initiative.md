# Story: Initiative (CR 702.148) — INT-01

## User Story
As a player, I want the Initiative mechanic fully implemented — gaining initiative, combat damage transfer, and venturing into Undercity on upkeep — so that cards like White Plume Adventurer and Tomb of Annihilation work correctly.

## Context
**Status: ✅ Complete**

Implemented as INT-01. Full CR 702.148 Initiative logic with pure transforms:

- **`set_initiative(gs, player_name)`**: Sets initiative holder, fires `gain_initiative` pending trigger for initiative-matters cards. Pure `model_copy()` transform.
- **`handle_upkeep_venture(gs)`**: At beginning of initiative holder's upkeep, they venture into the Undercity dungeon (5 rooms).
- **`check_combat_damage_initiative(gs, target_player, attacker_controller)`**: If combat damage dealt to initiative holder, attacker's controller gains initiative.
- **Undercity dungeon integration**: Initiative-specific dungeon with 5 rooms, each with different abilities (scry, draw, mill, gain life, venture again).

## Acceptance Criteria
- [x] `set_initiative()` returns new GameState via model_copy; fires `gain_initiative` trigger
- [x] Initiative holder ventures into Undercity on their upkeep
- [x] Combat damage transfer: dealing combat damage to initiative holder transfers it to attacker's controller
- [x] Undercity dungeon with 5 rooms and proper abilities
- [x] Dungeon completion increments counter; can re-enter Undercity after completion
- [x] All state transforms use pure model_copy — no direct mutations
- [x] 30 tests (15 unit + 15 integration) covering transfer, venture, triggers, edge cases

## Dependencies
- Venture/Dungeon mechanic (story-gm-venture.md) — Initiative uses venture() to advance through Undercity

## Priority: High | Effort: Completed ✅

## Notes
- Key file: `mtg_engine/engine/initiative.py` (78 lines)
- Test files: `tests/engine/test_initiative.py`, `tests/engine/test_initiative_integration.py`
- Undercity dungeon defined in `mtg_engine/models/dungeon.py` lines 103-133 (5 rooms)
- Initiative triggers `venture(gs, player_name, dungeon_name="Undercity")` on upkeep
- Recursive venturing from Undercity room 4 guarded by `progress.is_complete` check

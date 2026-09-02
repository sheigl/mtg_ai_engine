# Story: Venture / Dungeon (CR 701.61) — VEN-01

## User Story
As a player, I want to venture into dungeons — starting them, advancing through rooms, and completing them — so that AFR cards like Varis, Silverymoon Ranger and Dungeon Descent work correctly.

## Context
**Status: ✅ Complete**

Implemented as VEN-01. Full CR 701.61 Venture into the Dungeon mechanic with 4 dungeons:

- **Dungeons**: Dungeon of the Mad Mage (3 rooms), Lost Mine of Phandelver (3 rooms), Tomb of Annihilation (4 rooms), Undercity (5 rooms, linked to Initiative)
- **`venture(gs, player_name, dungeon_name)`**: Full venturing logic — starts new dungeon if none in progress/completed, advances to next room, fires room ability via stack resolution, increments completion counter when done.
- **`start_dungeon(gs, player_name, dungeon_name)`**: Begins a specific dungeon, returns first room ability text.
- **`_apply_room_effect(gs, player_name, ability_text)`**: Routes room abilities through existing `_apply_single_effect_text()` for draw, scry, gain life, etc.
- **Room choices**: `DungeonRoomChoice` model; human path queues `pending_dungeon_room_choice`; AI auto-resolves via `is_default` flag.
- **Stack integration**: "venture into the dungeon" regex added to both `_apply_single_effect_text()` and `_apply_spell_effect()`.
- **Recursive venturing**: Undercity rooms contain "venture into the dungeon" — chains through stack resolution with loop guard via `progress.is_complete`.

## Acceptance Criteria
- [x] 4 dungeons fully defined with rooms and abilities
- [x] `venture()` advances to next room, fires room ability, handles completion
- [x] `start_dungeon()` initializes a specific dungeon for a player
- [x] Room effect resolution via stack (draw, scry, gain life, tokens, etc.)
- [x] Room choices for human players (pending_dungeon_room_choice); AI auto-resolves
- [x] "venture into the dungeon" regex wired into stack effect resolution
- [x] Per-player dungeon progress tracking; independent for each player
- [x] Completed dungeon counter increments; trigger support for "whenever you complete a dungeon"
- [x] Recursive venturing from Undercity rooms (guarded against infinite loops)
- [x] All state transforms use pure model_copy — no direct mutations
- [x] 52 tests covering venture, start_dungeon, completion, room effects, edge cases

## Dependencies
- Initiative mechanic (story-gm-initiative.md) — Initiative holder ventures into Undercity on upkeep

## Priority: High | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/engine/dungeon.py`, `mtg_engine/models/dungeon.py`, `mtg_engine/engine/stack.py`
- Test files: `tests/engine/test_dungeon.py`, `tests/engine/test_venture_integration.py`
- Undercity dungeons are also used by the Initiative mechanic (INT-01)
- Room choice model: `DungeonRoomChoice(choice_id, description, outcome_ability, is_default)`

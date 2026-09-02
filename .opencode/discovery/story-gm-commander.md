# Story: Commander Rules (CR 903) — CMD-01

## User Story
As a Commander format player, I want full CR 903 rules enforcement — commander tax, zone replacement, commander damage, and Partner support — so that I can play authentic Commander games.

## Context
**Status: ✅ Complete**

Implemented as CMD-01. All Commander rules from CR 903 are enforced:

- **CR 903.8 Commander Tax**: `commander_cast_counts` tracked per-card-name. Each subsequent cast from the command zone costs {2} more per previous cast. Integrated into mana cost calculation in stack.py.
- **CR 903.9 Zone Replacement**: When a commander would change zones, human players receive a `pending_commander_zone_choice` (command zone vs. intended destination). AI players auto-redirect to command zone.
- **CR 903.10a Commander Damage**: Tracked per-permanent-id on `PlayerState.commander_damage`. 21+ damage from a single commander permanent causes loss.
- **Partner**: Two commanders allowed; each tracks cast counts independently; damage tracked per permanent-id.
- **Companion**: Out of scope for CMD-01 (handled by COM-01).

## Acceptance Criteria
- [x] CR 903.8: Commander cast count tracked per card name; tax increases by {2} per previous cast
- [x] CR 903.9: Zone change to library/hand/graveyard/exile queues pending choice; AI auto-redirects to command zone
- [x] CR 903.10a: Commander damage tracked per permanent ID; 21+ damage from a single permanent triggers loss
- [x] Partner: Two commanders allowed; independent cast tracking; independent damage tracking
- [x] API handlers for `commander_zone_replace` and `commander_zone_stay` choices
- [x] `_compute_legal_actions` includes commander zone choice actions when `pending_commander_zone_choice` is set
- [x] All state transforms use pure `model_copy()` — no direct mutations
- [x] 59 tests covering: zone choice, commander tax, commander damage loss, Partner, API flows

## Dependencies
- None (standalone module)

## Priority: High | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/engine/formats/commander.py`, `mtg_engine/api/routers/game.py`, `mtg_engine/engine/zones.py`
- `_is_commander(card_name, player)` and `_get_commander_names(player)` helpers in `mtg_engine/engine/formats/commander.py`
- Test files: `tests/engine/formats/test_commander.py`, `tests/engine/formats/test_commander_integration.py`, `tests/api/test_commander_zone_choice.py`
- Fixed critical bug (CMD-01): `commander_zone_stay` caused card disappearance when source zone was already emptied

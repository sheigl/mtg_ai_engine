# Story: Companion (CR 903.5) — COM-01

## User Story
As a player, I want the Companion mechanic fully implemented — paying {3} to put companion from sideboard into hand, once-per-game restriction, and restriction checking — so that cards like Lurrus of the Dream-Den and Yorion, Sky Nomad work correctly.

## Context
**Status: ✅ Complete**

Implemented as COM-01. Full CR 903.5 Companion logic with pure transforms:

- **`activate_companion(gs, player_name)`**: Core activation — checks once-per-game guard, finds companion in sideboard, validates restriction, pays {3} from mana pool, moves companion to hand. Returns `(GameState, Card | None)`.
- **`has_companion(card)`**: Checks for "companion" keyword in card's keywords list.
- **`check_companion_restriction(gs, player_name, card)`**: Parses oracle text for common restrictions (e.g., "You own fewer than N cards"). Extensible for future companion cards.
- **`can_activate_companion(gs, player_name)`**: Convenience check — manages guard, mana availability, valid companion existence.
- **`get_companion_from_sideboard(gs, player_name)`**: Returns first valid companion card from sideboard.
- **Mana payment**: Deducts {3} from mana pool preferring colorless first, then any color — pure transform on ManaPool via model_copy.

## Acceptance Criteria
- [x] `activate_companion()` pays {3} and moves companion from sideboard to hand
- [x] Once-per-game restriction enforced via `companion_used` map
- [x] Restriction checking for common companion conditions
- [x] `can_activate_companion()` convenience check for legal actions
- [x] All state transforms use pure model_copy — no direct mutations
- [x] 45 tests (22 unit + 23 integration) covering activation, mana payment, restrictions, edge cases

## Dependencies
- Commander Rules (story-gm-commander.md) — CR 903.5 companion is referenced in CR 903 rules

## Priority: High | Effort: Completed ✅

## Notes
- Key file: `mtg_engine/engine/companion.py` (144 lines)
- Test files: `tests/engine/test_companion.py`, `tests/engine/test_companion_integration.py`
- Companion sideboard is separate from main deck — companions start in sideboard per CR 903.5
- Fixed mutability issues (COM-01): replaced direct `setattr` mutations with model_copy transforms
- Common restrictions supported: "You own fewer than N cards", extensible for future companions

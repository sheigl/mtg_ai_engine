# Tasks: Commander Deck Import Bug Fix

**Source**: Bug — Commander format rejects valid 99-card decklists when commander is specified separately.
**Scope**: `mtg_engine/card_data/deck_loader.py` and `mtg_engine/api/routers/game.py`.

---

## Bug Description

`load_commander_deck(card_names, commander_name)` expects the commander to be **included** in `card_names` (100 cards total), then removes it and validates 99 remain. However:

1. **`DEFAULT_COMMANDER_DECK`** in `ai_client/prompts.py` is 99 cards (no commander) — so the default AI client flow always fails with `"Commander not found in deck"`.
2. Users providing a standard 99-card decklist via the API (commander specified via `commander1` field, not counted in the deck list) get the same error.

The fix: when the commander name is absent from the deck list, append it before processing — or accept a 99-card list and look up the commander independently. The `create_game` endpoint is the right place to normalise this, keeping `load_commander_deck`'s internal contract clean.

---

## Bug Fixes

- [X] T001 Fix `create_game` endpoint in `mtg_engine/api/routers/game.py` — before calling `load_commander_deck(req.deck1, req.commander1)` (line ~238) and the equivalent for deck2, append the commander name to the deck list if it is not already present: `deck1_list = list(req.deck1); if req.commander1 not in deck1_list: deck1_list.append(req.commander1)` (and same for deck2/commander2); pass `deck1_list` / `deck2_list` to `load_commander_deck` instead of `req.deck1` / `req.deck2`

- [X] T002 [P] Update `DEFAULT_COMMANDER_DECK` comment in `ai_client/prompts.py` — change the docstring from `"Built-in 99-card mono-green Commander deck"` to `"Built-in 99-card mono-green Commander deck (commander is designated separately via --commander)"` so intent is clear; no code change needed

- [X] T003 Add a test in `tests/test_009/` (create file `tests/test_009/test_commander_deck_import.py` if it doesn't exist) — assert that `create_game` with `format="commander"`, a 99-card deck list (without the commander), and a valid `commander1` name succeeds and places the commander in the command zone; assert that passing a 100-card list (commander included) also succeeds (both import styles work)

---

## Root Cause

`load_commander_deck` was designed around a "100-card list including the commander" convention, but the default deck constant and the natural API usage both follow a "99-card list, commander specified separately" convention. The mismatch was never caught because end-to-end Commander game tests (T024 in 009) only validated via curl with manually-constructed 100-card lists.

## Fix Strategy

Normalise at the `create_game` call site (T001) so both conventions work:
- `req.deck1` has 99 cards → commander appended → 100 sent to `load_commander_deck` ✓
- `req.deck1` has 100 cards (commander already included) → no change → 100 sent ✓
- Singleton validation in `load_commander_deck` naturally catches if the commander appears **twice** in a 100-card list

No change to `load_commander_deck` internals required.

# Tasks: Commander Human Game Bugs — Library Count & Missing Commander Display

**Bug report**: When importing a Commander deck via Archidekt URL in the "Play vs AI" (human game) flow:
1. The library shows an incorrect card count (94 instead of the expected ~99)
2. The commander card is never shown in the command zone

**Root cause analysis**:
- `HumanGameCreator.tsx` has no commander name input fields for commander format
- `HumanGameRequest` (in `human_game.py`) has no `commander1`/`commander2` fields
- `human_game.py` always calls `load_deck()` instead of `load_commander_deck()` regardless of format
- Result: commander card stays in the 100-card library (never in command zone), library starts with 100 cards (not 99), command zone is empty, PlayerZone shows no commander

**References**:
- Reported deck: https://archidekt.com/decks/15175807/damned_if_you_do_damned_if_you_dont
- `HumanGameCreator.tsx` — frontend form (missing commander fields)
- `mtg_engine/api/routers/human_game.py` — backend endpoint (missing commander handling)
- `mtg_engine/card_data/deck_loader.py` — `load_commander_deck()` exists but is unused here
- `mtg_engine/card_data/archidekt_parser.py` — `parse_archidekt_json()` (may include wrong categories)

---

## Phase 1: Investigate (Blocking — understand exact failure before fixing)

- [X] T001 Fetch https://archidekt.com/api/decks/15175807/ and inspect the raw JSON response: count cards by category ("Commander", "Main", "Maybeboard", "Sideboard", etc.) to confirm the exact source of the card count discrepancy; document findings as a comment in `mtg_engine/card_data/archidekt_parser.py`

- [X] T002 Confirm that `HumanGameRequest` in `mtg_engine/api/routers/human_game.py` has no `commander1`/`commander2` fields and that `create_human_game()` always calls `load_deck()` not `load_commander_deck()` — confirm root cause of missing command zone

---

## Phase 2: Backend Fix — `human_game.py`

- [X] T003 Add `commander1: str | None = None` and `commander2: str | None = None` fields to `HumanGameRequest` in `mtg_engine/api/routers/human_game.py`

- [X] T004 In `create_human_game()` in `mtg_engine/api/routers/human_game.py`: when `req.format == "commander"` and `req.commander1` / `req.commander2` are provided, call `load_commander_deck(d1, req.commander1)` and `load_commander_deck(d2, req.commander2)` instead of `load_deck(d1)` / `load_deck(d2)`; pass the returned `commander_card` objects through to `mgr.create_game()` as `commander1_card` and `commander2_card`; when format is "commander" but no commander names are provided, return a 422 with a clear error message

---

## Phase 3: Backend Fix — Archidekt parser (if T001 reveals a category bug)

- [X] T005 In `parse_archidekt_json()` in `mtg_engine/card_data/archidekt_parser.py`: if T001 confirms that non-deck categories (e.g. "Maybeboard", "Considering", "Acquireboard") are being included in `main[]`, update the category filter to only include cards in "Main" or "Commander" categories (or cards with no category); exclude "Maybeboard", "Considering", "Acquireboard", and any other non-deck categories; update `_validate_parsed()` if needed to allow commander-format 100-card counts

---

## Phase 4: Frontend Fix — `HumanGameCreator.tsx`

- [X] T006 Add `commander1: string` and `commander2: string` fields to the `FormState` interface in `frontend/src/components/HumanGameCreator.tsx`; initialize them to `''`

- [X] T007 In `HumanGameCreator.tsx`: when `form.format === 'commander'`, render two text inputs (one for "Your Commander", one for "Opponent Commander") below the format selector; add validation that both fields are non-empty when commander format is selected; wire `onChange` to update `form.commander1` / `form.commander2`

- [X] T008 In `HumanGameCreator.tsx` `handleSubmit`: include `commander1` and `commander2` in the request body when `form.format === 'commander'`:
  ```typescript
  ...(form.format === 'commander' && {
    commander1: form.commander1.trim(),
    commander2: form.commander2.trim(),
  }),
  ```

---

## Phase 5: Validation

- [X] T009 Manually test with the reported deck URL (https://archidekt.com/decks/15175807/damned_if_you_do_damned_if_you_dont): paste URL into the "Play vs AI" form with format=commander, enter the commander name, submit — verify that (a) the game starts, (b) the command zone shows the commander card, (c) the library starts at 99 (or 92 after opening draw)

- [X] T010 Run `python -m pytest tests/ -x -q` and fix any test failures caused by the `HumanGameRequest` model change or the archidekt parser change

---

## Dependencies & Execution Order

```
T001 → T005 (parser fix depends on investigation findings)
T002 → T003 → T004 (backend fix is sequential)
T006 → T007 → T008 (frontend fix is sequential)
T004 must be complete before T009 (manual test needs backend fix)
T008 must be complete before T009 (manual test needs frontend fix)
T009 → T010
```

## Parallel Opportunities

```
# After T001/T002 complete:
T003 + T006 can run in parallel (different files)
T004 + T007 can run in parallel (different files)
T005 + T008 can run in parallel (different files)
```

## Notes

- `load_commander_deck` raises `ValueError` if commander not found in deck, not legendary creature, not 99 cards after removal, or color identity violation — all existing validations apply
- The existing `_validate_parsed()` in `archidekt_parser.py` requires ≥60 cards and ≤4 copies — neither check is correct for Commander; T005 may also need to add a commander-specific validation path
- `HumanGameCreator` sends to `/human-game`; `CreateGameForm` sends to `/ai-game` — these are separate endpoints; only `human_game.py` is broken (the AI game flow already handles commander correctly via `game.py`)

# Tasks: UI Game Creator

**Input**: Design documents from `/specs/015-ui-game-creator/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths in all descriptions

---

## Phase 1: Setup

No setup tasks required — this feature is purely additive to an existing Python/TypeScript project with all dependencies already installed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend endpoint and game loop adaptation that all frontend stories depend on.

**⚠️ CRITICAL**: All Phase 3–7 frontend tasks require the `POST /ai-game` endpoint to be in place.

- [X] T001 [P] Modify `ai_client/game_loop.py`: add `game_id: str | None = None` parameter to `GameLoop.__init__`; in `GameLoop.run()`, skip `self._engine.create_game()` and use the provided `game_id` directly when it is not None
- [X] T002 [P] Create `mtg_engine/api/routers/ai_game.py`: define `AIPlayerConfig`, `AIGameRequest`, `AIGameResponse` Pydantic models; implement `POST /ai-game` endpoint that validates the request, creates the game via `GameManager.create_game()`, builds `GameLoop` with the new `game_id` parameter, starts the loop in a `daemon=True` `threading.Thread`, and returns `{"data": {"game_id": game_id}}`
- [X] T003 Register the `ai_game` router in `mtg_engine/api/main.py` by importing and calling `app.include_router(ai_game_router.router)`

**Checkpoint**: `POST /ai-game` returns a `game_id` and a game appears in `GET /game` immediately; the game board at `/ui/game/{game_id}` shows autonomous play.

---

## Phase 3: User Story 1 — Launch a Standard AI Game (Priority: P1) 🎯 MVP

**Goal**: User can open the UI, click "New AI Game", configure two players (LLM or heuristic), and start a game that navigates to the live board.

**Independent Test**: Fill out the modal with two heuristic players and default settings → click "Start Game" → game board loads and advances autonomously.

- [X] T004 [P] [US1] Create `frontend/src/styles/create-game.css`: styles for the modal overlay, modal container, form sections, player config rows, field labels, type selector, conditional field visibility, submit/cancel buttons, and inline error display
- [X] T005 [US1] Create `frontend/src/components/CreateGameForm.tsx`: modal component with controlled form state; player 1 and player 2 sections each containing name input, player-type radio/select (llm | heuristic), and conditional base-url + model inputs shown only when type = llm; submit handler that POSTs to `/ai-game`, navigates to `/game/{game_id}` on success, and displays the error message from the response body on failure; cancel button closes the modal
- [X] T006 [US1] Modify `frontend/src/components/GameList.tsx`: add a "New AI Game" button in the page header; manage `showCreateForm: boolean` state; render `<CreateGameForm>` as a modal overlay when `showCreateForm` is true; close it on cancel or successful game creation

**Checkpoint**: A two-heuristic-player game can be created and observed entirely from the browser with no CLI required.

---

## Phase 4: User Story 2 — Configure Decks (Priority: P2)

**Goal**: User can enter custom comma-separated card lists for each player's deck instead of using the default.

**Independent Test**: Enter a short card list for player 1 (e.g. `Lightning Bolt, Mountain, Mountain`) → start game → game board shows those cards in player 1's library/hand.

- [X] T007 [US2] Add deck configuration fields to `frontend/src/components/CreateGameForm.tsx`: two textarea or text inputs (deck1, deck2), each with placeholder text "Leave blank to use the default deck (comma-separated card names)"; on submit, split the raw text on commas, strip whitespace, and filter empty strings before including in the POST body; if the engine returns a `DECK_LOAD_ERROR`, display the error message next to the relevant deck field

**Checkpoint**: Games can be started with custom card lists; invalid card names produce a visible error and leave the form open.

---

## Phase 5: User Story 3 — Commander Format (Priority: P3)

**Goal**: User can select Commander format and enter two commander names; the game starts with 40 life and command zones.

**Independent Test**: Select Commander, enter two valid legendary creature names → start game → game board shows 40 starting life for both players and the commander cards in the command zone.

- [X] T008 [US3] Add format and commander fields to `frontend/src/components/CreateGameForm.tsx`: a format selector (dropdown: Standard | Commander); when Commander is selected, show two text inputs for commander1 and commander2 with clear labels; include format and commander values in the POST body; surface `INVALID_COMMANDER` and `COLOR_IDENTITY_VIOLATION` engine errors inline on the form

**Checkpoint**: Commander games can be started from the UI with correct format enforcement.

---

## Phase 6: User Story 4 — Debug and Observer Options (Priority: P4)

**Goal**: User can enable debug mode so the debug panel auto-opens on the game board; optionally configure a separate observer AI endpoint.

**Independent Test**: Enable debug toggle → start game → game board opens with the debug panel active and entries appearing as the game progresses.

- [X] T009 [US4] Add debug and observer fields to `frontend/src/components/CreateGameForm.tsx`: a debug checkbox toggle; when debug is checked, reveal two text inputs for observer URL and observer model with placeholder text "Optional — defaults to first LLM player's endpoint"; include `debug`, `observer_url`, and `observer_model` in the POST body; if debug is checked and all players are heuristic and observer URL is empty, display an inline warning (not an error) that no LLM commentary will be available

**Checkpoint**: Games started with debug enabled show the debug panel auto-opened; observer commentary appears when an observer endpoint is configured.

---

## Phase 7: User Story 5 — Advanced Options (Priority: P5)

**Goal**: User can set a max-turns cap and enable verbose play-by-play logging via a collapsible advanced section.

**Independent Test**: Expand advanced options, set max turns to 5 → start game → game ends after 5 turns with the correct termination reason visible on the board.

- [X] T010 [US5] Add advanced options section to `frontend/src/components/CreateGameForm.tsx`: a collapsible "Advanced" toggle (collapsed by default); inside, a numeric max-turns input (default 200, label "Max turns (0 = unlimited)") and a verbose checkbox; include `max_turns` and `verbose` in the POST body

**Checkpoint**: Games respect the max-turns limit and verbose events appear in the action log when enabled.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation hardening and build verification across all form fields.

- [X] T011 Add comprehensive client-side validation to `frontend/src/components/CreateGameForm.tsx`: prevent submission when player names are empty; prevent submission when player names are identical; prevent submission when player type is llm but base_url or model is empty; validate that base_url starts with `http://` or `https://` for LLM players; require commander1 and commander2 when format is commander; require observer_model when observer_url is non-empty; display field-level error messages that clear when the user corrects the input
- [X] T012 Build the frontend to verify TypeScript compiles without errors: `cd frontend && npm run build`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — T001 and T002 can start immediately in parallel; T003 depends on T002
- **US1 (Phase 3)**: Depends on T003 (endpoint registered). T004 and T003 can overlap (CSS needs no backend). T005 depends on T004. T006 depends on T005.
- **US2–US5 (Phases 4–7)**: Each phase edits `CreateGameForm.tsx` sequentially; must complete in order to avoid merge conflicts
- **Polish (Phase 8)**: T011 and T012 require all form fields to exist (after Phase 7)

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational completion — no other story dependencies
- **US2 (P2)**: Depends on US1 (form component must exist)
- **US3 (P3)**: Depends on US1 (form component must exist); independent of US2
- **US4 (P4)**: Depends on US1; independent of US2/US3
- **US5 (P5)**: Depends on US1; independent of US2/US3/US4

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- T004 (CSS) can overlap with T003 (router registration)
- US2, US3, US4, US5 all edit the same file (`CreateGameForm.tsx`) — must run sequentially

---

## Parallel Example: Foundational Phase

```
# These two tasks can start simultaneously:
Task T001: Modify ai_client/game_loop.py
Task T002: Create mtg_engine/api/routers/ai_game.py

# T003 starts after T002 completes:
Task T003: Register router in mtg_engine/api/main.py
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 2: Foundational (T001–T003)
2. Complete Phase 3: US1 (T004–T006)
3. **STOP and VALIDATE**: `POST /ai-game` with two heuristic players works end-to-end from the browser
4. No CLI required at this point for a basic game

### Incremental Delivery

1. Foundation (T001–T003) → test via `curl` using quickstart.md scenarios
2. US1 (T004–T006) → test by launching a heuristic game from the UI
3. US2 (T007) → test by entering a custom card list
4. US3 (T008) → test by starting a commander game
5. US4 (T009) → test by enabling debug and observing the panel
6. US5 (T010) → test by capping a game at 5 turns
7. Polish (T011–T012) → validate all edge cases and build cleanly

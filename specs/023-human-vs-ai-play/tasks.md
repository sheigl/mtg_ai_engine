# Tasks: Human vs AI Gameplay

**Input**: Design documents from `specs/023-human-vs-ai-play/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Backend API tests included for the new endpoint and hybrid loop. Frontend verified by manual browser testing per quickstart.md checklist.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on other in-progress tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new files and directory structure. No logic yet.

- [X] T001 Create `ai_client/hybrid_game_loop.py` as empty module with class stub `HybridGameLoop(GameLoop)` in `ai_client/hybrid_game_loop.py`
- [X] T002 [P] Create `mtg_engine/api/routers/human_game.py` as empty module with APIRouter stub in `mtg_engine/api/routers/human_game.py`
- [X] T003 [P] Create `frontend/src/pages/HumanGameCreator.tsx` with placeholder export in `frontend/src/components/HumanGameCreator.tsx`
- [X] T004 [P] Create `frontend/src/pages/HumanGameBoard.tsx` with placeholder export in `frontend/src/components/HumanGameBoard.tsx`
- [X] T005 [P] Create `frontend/src/hooks/useLegalActions.ts` as empty module in `frontend/src/hooks/useLegalActions.ts`
- [X] T006 [P] Create `frontend/src/hooks/useHumanAction.ts` as empty module in `frontend/src/hooks/useHumanAction.ts`
- [X] T007 [P] Create `frontend/src/components/ActionPanel.tsx` with placeholder export in `frontend/src/components/ActionPanel.tsx`
- [X] T008 [P] Create `frontend/src/components/InteractiveHand.tsx` with placeholder export in `frontend/src/components/InteractiveHand.tsx`
- [X] T009 [P] Create `frontend/src/components/AttackerSelector.tsx` with placeholder export in `frontend/src/components/AttackerSelector.tsx`
- [X] T010 [P] Create `frontend/src/components/BlockerAssigner.tsx` with placeholder export in `frontend/src/components/BlockerAssigner.tsx`
- [X] T011 [P] Create `frontend/src/components/ChoiceModal.tsx` with placeholder export in `frontend/src/components/ChoiceModal.tsx`
- [X] T012 [P] Create `frontend/src/components/GameResultOverlay.tsx` with placeholder export in `frontend/src/components/GameResultOverlay.tsx`
- [X] T013 [P] Create `tests/api/test_human_game.py` as empty test file in `tests/api/test_human_game.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend infrastructure and frontend hooks that multiple user stories depend on. Must complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T014 Implement `HybridGameLoop` in `ai_client/hybrid_game_loop.py`: subclass `GameLoop`, add `human_player_name: str` constructor param, override the polling loop to `sleep(0.5); continue` when `legal_data["priority_player"] == self.human_player_name`, pass all other turns to the parent AI logic unchanged
- [X] T015 Add `HumanGameRequest` and `HumanGameResponse` Pydantic models to `mtg_engine/api/routers/human_game.py` per `specs/023-human-vs-ai-play/data-model.md` (fields: player1_type, player2_type, player1_deck, player2_deck, player1_name, player2_name, format, ai_model, observer_model, observer_enabled; response: game_id, human_player_name, redirect_url)
- [X] T016 Implement `useLegalActions` hook in `frontend/src/hooks/useLegalActions.ts`: poll `GET /game/{gameId}/legal-actions` every 750ms using React Query, expose `{ isMyTurn, legalActions, legalActionsByCard, hasPendingChoice, pendingChoiceType }` where `isMyTurn = priority_player === humanPlayerName`
- [X] T017 Implement `useHumanAction` hook in `frontend/src/hooks/useHumanAction.ts`: expose `submitAction(actionType: string, payload: object): Promise<void>` that POSTs to `POST /game/{gameId}/{actionType}`, manages `isPending: boolean` state, and on success invalidates React Query cache for game state and legal actions

**Checkpoint**: Foundation ready — HybridGameLoop drives AI turns and idles for human turns; frontend hooks can detect human priority windows and submit actions.

---

## Phase 3: User Story 1 — Create and Join a Human vs AI Game (Priority: P1) 🎯 MVP

**Goal**: Human can navigate to a creation form, configure opponent type and decks, start a game, and be placed in the game board as the controlling player.

**Independent Test**: Navigate to `/ui/human-game/create`, select Heuristic opponent, pick decks, click Start Game → redirected to `/ui/human-game/{id}` with a game board showing the human as the active player.

- [X] T018 [US1] Implement `POST /human-game` endpoint in `mtg_engine/api/routers/human_game.py`: validate at least one seat is `"human"` (422 if not), create game via `GameManager.create_game()` using same pattern as `ai_game.py`, start `HybridGameLoop` in a daemon thread for the AI seat, return `HumanGameResponse` with game_id, human_player_name, and redirect_url `/ui/human-game/{game_id}`
- [X] T019 [US1] Register `human_game` router in `mtg_engine/api/main.py` alongside existing routers (add `app.include_router(human_game_router)`)
- [X] T020 [US1] Implement `HumanGameCreator.tsx` in `frontend/src/components/HumanGameCreator.tsx`: form with player type dropdowns (Human / AI / Heuristic) per seat, deck selection fields (reuse existing deck list pattern), "Start Game" button that POSTs to `/human-game` and navigates to the returned `redirect_url` on success
- [X] T021 [US1] Add routes to `frontend/src/App.tsx`: `/ui/human-game/create` → `HumanGameCreator`, `/ui/human-game/:gameId` → `HumanGameBoard`
- [X] T022 [US1] Add "Play vs AI" button to the game list page (`frontend/src/components/GameList.tsx`) linking to `/ui/human-game/create`
- [X] T023 [US1] Add backend test in `tests/api/test_human_game.py`: `POST /human-game` with valid human+heuristic request returns 200 with `game_id`; `POST /human-game` with no human seat returns 422; game appears in `GET /game` list after creation

**Checkpoint**: Human can create a game and land on the board page. The AI takes its turns automatically. Human priority windows show blank board for now (interactive controls added in Phase 4).

---

## Phase 4: User Story 2 — Human Player Takes a Turn (Priority: P1)

**Goal**: Human can play lands, cast spells, declare attackers, assign blockers, and pass priority through the UI.

**Independent Test**: Start a human vs heuristic game. On the human's first main phase, click a land in hand → land appears on battlefield. Click a castable spell → it resolves. In combat, click creatures to attack → confirm attackers → AI blocks. Click "Pass Priority" → turn ends.

- [X] T024 [US2] Implement `HumanGameBoard.tsx` in `frontend/src/components/HumanGameBoard.tsx`: poll game state via existing `useGameState` hook (1500ms), poll legal actions via `useLegalActions` (750ms), render the existing observer-style board (hand, battlefield, life totals, stack, phase tracker), conditionally render interactive overlay components when `isMyTurn`, check `is_game_over` each poll
- [X] T025 [US2] Implement `InteractiveHand.tsx` in `frontend/src/components/InteractiveHand.tsx`: receive `hand: Card[]`, `legalActionsByCard: Map<string, LegalAction[]>`, `onPlayLand(cardId)`, `onCastSpell(action, cardId)` props; render each card; highlight cards that appear in `legalActionsByCard`; clicking a land card in a legal "play_land" action calls `onPlayLand`; clicking a castable spell calls `onCastSpell` with the action details
- [X] T026 [US2] Wire land-play in `HumanGameBoard.tsx`: when `onPlayLand(cardId)` is called, invoke `submitAction("play-land", { card_id: cardId })` via `useHumanAction`; disable interactive hand while `isPending`
- [X] T027 [US2] Implement `ActionPanel.tsx` in `frontend/src/components/ActionPanel.tsx`: receive `phase`, `step`, `legalActions`, `isMyTurn`, `selectedAttackers`, `onPassPriority`, `onConfirmAttackers`, `onConfirmBlockers`, `autoPassPriority`, `onToggleAutoPass` props; render "Pass Priority" button always when `isMyTurn`; render "Confirm Attackers" button during `DECLARE_ATTACKERS` step when `selectedAttackers.size > 0`; render "Confirm Blocks" button during `DECLARE_BLOCKERS` step; render auto-pass toggle checkbox
- [X] T028 [US2] Implement `AttackerSelector.tsx` in `frontend/src/components/AttackerSelector.tsx`: receive `creatures: Permanent[]`, `legalAttackerIds: Set<string>`, `selectedAttackers: Set<string>`, `onToggle(permanentId)` props; render each creature with a visual "selected as attacker" state (red glow); clicking a legal attacker calls `onToggle`
- [X] T029 [US2] Wire attacker declaration in `HumanGameBoard.tsx`: manage `selectedAttackers: Set<string>` state; during `DECLARE_ATTACKERS` step render `AttackerSelector` overlay on battlefield; "Confirm Attackers" in `ActionPanel` calls `submitAction("declare-attackers", { attacker_ids: [...selectedAttackers] })`; clear `selectedAttackers` after submit
- [X] T030 [US2] Implement `BlockerAssigner.tsx` in `frontend/src/components/BlockerAssigner.tsx`: receive `myCreatures: Permanent[]`, `attackingCreatures: Permanent[]`, `assignments: Map<string, string>`, `onAssign(blockerId, attackerId)`, `onUnassign(blockerId)` props; clicking a blocker then an attacker creates an assignment; render assignment lines or badges; unassigning clears the pairing
- [X] T031 [US2] Wire blocker assignment in `HumanGameBoard.tsx`: manage `blockerAssignments: Map<string, string>` state; during `DECLARE_BLOCKERS` step render `BlockerAssigner`; "Confirm Blocks" in `ActionPanel` calls `submitAction("declare-blockers", { assignments: [...blockerAssignments.entries()].map(([blocker_id, attacker_id]) => ({ blocker_id, attacker_id })) })`
- [X] T032 [US2] Wire "Pass Priority" in `HumanGameBoard.tsx`: `ActionPanel` onPassPriority calls `submitAction("pass", {})`
- [X] T033 [US2] Handle spell casting (no-target spells) in `HumanGameBoard.tsx`: when `onCastSpell` is called for a spell with no required targets and no modal choices, directly call `submitAction("cast", { card_id, targets: [], mana_payment: null, x_value: null, face_index: 0 })`

**Checkpoint**: Human can play a full turn — land drop, spell cast (no-target), attackers, blockers, pass priority — all through UI clicks.

---

## Phase 5: User Story 3 — Responding to AI Actions (Priority: P2)

**Goal**: Human receives priority windows during the AI's turn and can respond with instants, flash creatures, or pass.

**Independent Test**: Load a deck with a counterspell. Have the AI cast a spell. Verify the UI shows the human's hand as interactive with the counterspell highlighted. Cast the counterspell → it goes on the stack. Click Pass Priority → original spell resolves.

- [X] T034 [US3] Implement `ChoiceModal.tsx` in `frontend/src/components/ChoiceModal.tsx` for target selection: detect when a cast spell's legal action has `valid_targets` array; render a modal listing target names (permanents + players); clicking a target completes the selection; "Cancel" clears the pending cast; wire into `HumanGameBoard.tsx` as `pendingCast` state
- [X] T035 [US3] Wire targeted spell casting in `HumanGameBoard.tsx`: when `onCastSpell` is called for a spell that has `valid_targets.length > 0` in its legal action, set `pendingCast` state to open `ChoiceModal`; on target selection call `submitAction("cast", { card_id, targets: [selectedTarget], mana_payment: null, x_value: null, face_index: 0 })`
- [X] T036 [US3] Add response window detection in `HumanGameBoard.tsx`: when `isMyTurn` is true but `gameState.active_player !== humanPlayerName` (it is the AI's turn but human has priority), show a "Response Window" indicator in `ActionPanel` header to distinguish responding from acting; interactive hand still shows instant-speed actions highlighted
- [X] T037 [US3] Implement auto-pass priority in `HumanGameBoard.tsx`: read `autoPassPriority` from localStorage; when `isMyTurn` and `autoPassPriority` is enabled and `legalActions` contains only `"pass"` (no instant-speed plays available), automatically call `submitAction("pass", {})` after a 300ms delay to give visual feedback; `ActionPanel` toggle persists the setting to localStorage

**Checkpoint**: Human can respond to AI spells with instants, or auto-pass when nothing is castable.

---

## Phase 6: User Story 4 — AI Observer Still Functions (Priority: P2)

**Goal**: Verify with zero code changes that the AI observer, verbose log, and commentary all continue to work in human vs AI games. This phase is a verification story — new tests only.

**Independent Test**: Start a human vs AI game with observer enabled. Play several turns as the human. Open `/ui/game/{id}` (existing observer view) in a parallel tab — commentary should appear. Check verbose log endpoint to confirm human actions are logged.

- [X] T038 [US4] Add observer regression test in `tests/api/test_human_game.py`: observer endpoints accessible for human games verified in test_observer_endpoints_accessible_for_human_game
- [X] T039 [US4] Add verbose log test in `tests/api/test_human_game.py`: game creation with verbose flag works; transcript accessible via export endpoint
- [ ] T040 [US4] Manual verification step (documented): start human game via UI, open observer board at `/ui/game/{id}` in a second tab, confirm commentary panel shows commentary after human plays a card — no code change needed, just mark done after manual check

**Checkpoint**: Observer and verbose log confirmed working for human games. No regressions.

---

## Phase 7: User Story 5 — Game Completion and Result (Priority: P3)

**Goal**: When the game ends, a clear win/loss screen is displayed with options to play again or return to the game list.

**Independent Test**: Play a game to completion (or use a test deck designed to win in 2 turns). Verify win/loss overlay appears with correct result and "Play Again" navigates back to the creator.

- [X] T041 [US5] Implement `GameResultOverlay.tsx` in `frontend/src/components/GameResultOverlay.tsx`: receive `isGameOver: boolean`, `winner: string | null`, `humanPlayerName: string`, `gameId: string` props; when `isGameOver` render a full-screen overlay with "Victory!" or "Defeat" heading (compare winner to humanPlayerName), a "Play Again" link to `/ui/human-game/create`, and a "Watch Replay" link to `/ui/game/{gameId}` (existing observer); show "Draw" if winner is null and game is over
- [X] T042 [US5] Wire `GameResultOverlay` into `HumanGameBoard.tsx`: pass `gameState.is_game_over`, `gameState.winner`, `humanPlayerName`, and `gameId` props; render overlay above all other components when `is_game_over` is true

**Checkpoint**: Human vs AI games have a clean end state with navigation options.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, UX improvements, and manual test validation across all stories.

- [X] T043 [P] Add error handling in `useHumanAction.ts`: on API error response (400/422/500), surface the error message to the user (inline error in `ActionPanel`) rather than silently failing
- [X] T044 [P] Disable interactive controls in `HumanGameBoard.tsx` while `isPending` is true (from `useHumanAction`) to prevent double-submission; `isPending` prop passed to `InteractiveHand` and `ActionPanel`
- [X] T045 [P] Handle mid-resolution choices beyond targeting in `ChoiceModal.tsx`: `MulliganModal`, `DiscardModal`, `ScryModal` implemented; mulligan and discard detection wired in `HumanGameBoard.tsx`
- [X] T046 [P] Add X-spell handling in `ChoiceModal.tsx`: `TargetChoiceModal` includes numeric X input when `action.x_value` is set
- [ ] T047 Run manual browser test checklist from `specs/023-human-vs-ai-play/quickstart.md`: full turn, response window, blocker assignment, target selection, auto-pass, win/loss overlay, observer panel — mark done after passing all items
- [X] T048 Run `python -m pytest tests/api/test_human_game.py -v` — 9 passed ✓

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — all tasks create empty stubs in parallel
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — MVP starting point
- **US2 (Phase 4)**: Depends on Phase 2 (hooks); benefits from US1 being done (game creation flow)
- **US3 (Phase 5)**: Depends on Phase 4 (interactive hand and action panel already exist)
- **US4 (Phase 6)**: Depends on Phase 3 (game creation) — observer tests need a real game
- **US5 (Phase 7)**: Depends on Phase 4 (HumanGameBoard.tsx exists)
- **Polish (Phase 8)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P1)**: Can start after Phase 2 — no dependencies on other stories (uses same game)
- **US3 (P2)**: Depends on US2 (Phase 4) — needs `ChoiceModal`, `ActionPanel`, `InteractiveHand` to exist
- **US4 (P2)**: Depends on US1 (Phase 3) — needs game creation to work; no code changes required
- **US5 (P3)**: Depends on US2 (Phase 4) — needs `HumanGameBoard.tsx` base to exist

### Within Each User Story

- Models/hooks before services/endpoints (T014–T017 must precede T018+)
- Backend endpoint (T018) before frontend creation form (T020)
- `HumanGameBoard.tsx` skeleton (T024) before interactive overlays (T025–T033)
- `ChoiceModal` base (T034) before targeted spell wiring (T035)

### Parallel Opportunities

- All Phase 1 stubs (T001–T013) can be created in parallel
- T015–T017 (Pydantic models + frontend hooks) can run in parallel after T001/T005/T006
- T020–T022 (frontend creator pages + routing) can run in parallel after T018
- T025–T033 interactive components can mostly run in parallel (different files) after T024

---

## Parallel Example: Phase 4 (User Story 2)

```bash
# After T024 (HumanGameBoard skeleton) is done, launch in parallel:
Task T025: "InteractiveHand.tsx in frontend/src/components/InteractiveHand.tsx"
Task T027: "ActionPanel.tsx in frontend/src/components/ActionPanel.tsx"
Task T028: "AttackerSelector.tsx in frontend/src/components/AttackerSelector.tsx"
Task T030: "BlockerAssigner.tsx in frontend/src/components/BlockerAssigner.tsx"

# Then wire them in (sequential, all touch HumanGameBoard.tsx):
Task T026: Wire land-play
Task T029: Wire attacker declaration
Task T031: Wire blocker assignment
Task T032: Wire pass priority
Task T033: Wire no-target spell casting
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (stubs)
2. Complete Phase 2: Foundational (HybridGameLoop + hooks)
3. Complete Phase 3: US1 (game creation + backend endpoint)
4. Complete Phase 4: US2 (full interactive turn)
5. **STOP and VALIDATE**: Human can play a full game turn end-to-end
6. Demo / share

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. + Phase 3 → Human can create and join a game (MVP entry point)
3. + Phase 4 → Human can play a full turn (core loop working)
4. + Phase 5 → Human can respond to AI at instant speed
5. + Phase 6 → Observer confirmed working (zero-code story)
6. + Phase 7 → Clean game endings
7. + Phase 8 → Polish and error handling

---

## Notes

- [P] tasks = different files, no dependencies on in-progress tasks
- [US*] label maps task to user story for traceability
- `HybridGameLoop` is the key backend unlock — everything flows from it
- The existing `GET /game/{id}/legal-actions` endpoint does all the heavy lifting for the frontend — the UI just reads `priority_player` and `legal_actions[]`
- All existing action endpoints (pass, play-land, cast, declare-attackers, etc.) are used unchanged; no action endpoint modifications needed
- Observer and verbose logging require zero code changes (US4 is verification only)
- Commit after each task or logical group; each phase checkpoint is a natural commit point

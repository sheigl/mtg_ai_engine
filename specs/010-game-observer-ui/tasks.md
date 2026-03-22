# Tasks: Game Observer Web UI

**Input**: Design documents from `/specs/010-game-observer-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are included only for the new backend endpoint (existing pytest conventions).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the React frontend project and configure build tooling

- [X] T001 Scaffold React + TypeScript project with Vite in frontend/ (package.json, tsconfig.json, vite.config.ts, index.html)
- [X] T002 Install frontend dependencies: react, react-dom, react-router-dom, @tanstack/react-query, framer-motion, and dev deps (typescript, @types/react, @types/react-dom, vite)
- [X] T003 Configure Vite dev server proxy to forward /game and /export requests to backend at localhost:8000 in frontend/vite.config.ts
- [X] T004 Create TypeScript type definitions mirroring engine Pydantic models in frontend/src/types/game.ts (GameState, PlayerState, Card, Permanent, StackObject, TranscriptEntry, GameSummary, Phase, Step enums)
- [X] T005 Create frontend entry point in frontend/src/main.tsx with QueryClientProvider and BrowserRouter

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend endpoint for game listing, static file serving, and shared frontend infrastructure that ALL user stories depend on

### Backend

- [X] T006 Add GameSummary Pydantic response model and GET /game list endpoint in mtg_engine/api/routers/game.py that iterates GameManager._games and returns summary projections
- [X] T007 Add StaticFiles mount for frontend/dist/ and SPA catch-all route at /ui/{path} in mtg_engine/api/main.py
- [X] T008 Add pytest test for GET /game endpoint in tests/api/test_game_list.py (empty list, single game, multiple games, includes format/turn/phase)

### Frontend Shared Infrastructure

- [X] T009 Create global CSS styles with dark theme and CSS variables (board colors, card dimensions, MTG color palette) in frontend/src/styles/index.css
- [X] T010 [P] Create card CSS styles with color-coded borders (W/U/B/R/G/multi/colorless), tapped rotation, mana cost badges in frontend/src/styles/card.css
- [X] T011 [P] Create board layout CSS with 3-row grid (opponent/center/player) in frontend/src/styles/board.css
- [X] T012 [P] Create zone transition animation keyframes (300-600ms durations) in frontend/src/styles/animations.css
- [X] T013 Create App.tsx with React Router routes: "/" for game list, "/game/:gameId" for board view, in frontend/src/App.tsx
- [X] T014 [P] Create ConnectionStatus component showing reconnecting indicator with automatic retry status in frontend/src/components/ConnectionStatus.tsx (FR-009)

**Checkpoint**: Backend serves game list + static files. Frontend scaffolding, routing, and shared styles ready. User story implementation can begin.

---

## Phase 3: User Story 1 - Live Game Board View (Priority: P1) 🎯 MVP

**Goal**: An observer sees a live, animated view of an AI game with both players' zones, life totals, battlefield permanents, stack, and animated card zone transitions.

**Independent Test**: Open the UI at /ui/game/{id} while an AI game is running. The board displays within 2 seconds and card movements are visibly animated.

### Implementation for User Story 1

- [X] T015 [US1] Create useGameState hook in frontend/src/hooks/useGameState.ts using TanStack Query to poll GET /game/{gameId} every 1500ms with state_hash dedup
- [X] T016 [P] [US1] Create CardView component in frontend/src/components/CardView.tsx rendering styled card element with name, type line, mana cost, power/toughness, color border, tapped rotation, and counters badge
- [X] T017 [P] [US1] Create Battlefield component in frontend/src/components/Battlefield.tsx with CSS Grid auto-fill layout and Framer Motion AnimatePresence + layoutId on each permanent for zone-change animations (FR-004, FR-005, FR-010)
- [X] T018 [P] [US1] Create PlayerZone component in frontend/src/components/PlayerZone.tsx displaying life total, hand card count, library count, graveyard count, exile count, mana pool, and commander zone (if format=commander) (FR-003, FR-008)
- [X] T019 [P] [US1] Create StackView component in frontend/src/components/StackView.tsx showing stack objects with card name, controller, and targets (FR-006)
- [X] T020 [P] [US1] Create PhaseTracker component in frontend/src/components/PhaseTracker.tsx displaying current turn number, phase, step, and active player indicator (FR-003)
- [X] T021 [US1] Create GameBoard component in frontend/src/components/GameBoard.tsx composing PlayerZone (x2, mirrored), Battlefield (x2), StackView, PhaseTracker, and ConnectionStatus in 3-row CSS Grid layout (FR-002)
- [X] T022 [US1] Wire GameBoard to useGameState hook with loading state, error state, game-over display (winner announcement), and 404 handling for deleted games (FR-009)
- [X] T023 [US1] Add commander-format support to GameBoard: display command zone cards, commander damage totals per opponent, and commander cast count/tax in PlayerZone (FR-008)

**Checkpoint**: Board view at /ui/game/{id} is fully functional — shows animated live game state with all zones, supports both standard and commander formats.

---

## Phase 4: User Story 2 - Game Selection and List View (Priority: P2)

**Goal**: An observer can see all running games and select one to watch.

**Independent Test**: Start two AI games, open /ui/. A list shows both games. Click one to open the board. Use back to return to the list.

### Implementation for User Story 2

- [X] T024 [US2] Create useGameList hook in frontend/src/hooks/useGameList.ts using TanStack Query to poll GET /game every 5000ms (FR-001)
- [X] T025 [US2] Create GameList component in frontend/src/components/GameList.tsx rendering list of active games with player names, format badge (standard/commander), turn number, and phase — each entry links to /game/{id} (FR-001)
- [X] T026 [US2] Add empty state ("No active games") and finished-game visual indicator (dimmed/strikethrough for is_game_over=true) to GameList component
- [X] T027 [US2] Add back-to-list navigation button in GameBoard component header that navigates to / using React Router

**Checkpoint**: Full observer flow works — list view → select game → board view → back to list. Game list auto-refreshes and handles empty/finished states.

---

## Phase 5: User Story 3 - Play-by-Play Action Log (Priority: P3)

**Goal**: A running sidebar log of game events in plain English alongside the board view.

**Independent Test**: Watch a game. The action log on the side updates with each action, auto-scrolls to latest, and filters out noisy events.

### Implementation for User Story 3

- [X] T028 [US3] Create useTranscript hook in frontend/src/hooks/useTranscript.ts using TanStack Query to poll GET /export/{gameId}/transcript every 2000ms, tracking lastSeenSeq for incremental updates
- [X] T029 [US3] Create ActionLog component in frontend/src/components/ActionLog.tsx rendering filtered transcript entries (show: cast, resolve, zone_change, damage, attack, block, life_change, game_end, trigger, activate, draw; skip: phase_change, priority_grant, choice_made, sba) with auto-scroll to bottom (FR-007)
- [X] T030 [US3] Integrate ActionLog as a right sidebar (~25% width) in GameBoard layout, only rendered when a game is selected

**Checkpoint**: Board view now includes action log sidebar with readable, auto-scrolling game events.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, error handling, and build verification

- [X] T031 Verify battlefield remains readable with 15 permanents per player — adjust CSS Grid minmax and card sizing in frontend/src/styles/card.css and frontend/src/styles/board.css (FR-010, SC-003)
- [X] T032 Add exponential backoff retry logic to useGameState and useGameList hooks for network failures, surfacing status via ConnectionStatus (FR-009, SC-005)
- [X] T033 Add Vite build script (npm run build) outputting to frontend/dist/ and verify FastAPI serves the built SPA correctly at /ui/
- [X] T034 Run full backend test suite (cd src && pytest) to verify new GET /game endpoint and StaticFiles mount don't break existing functionality
- [X] T035 Manual quickstart validation: start engine, build frontend, create a game, open /ui/, verify board loads with animations per quickstart.md scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational (Phase 2) completion
  - US1 (P1) can start after Phase 2
  - US2 (P2) can start after Phase 2 (independent of US1, but US1 provides the board that US2 navigates to)
  - US3 (P3) depends on US1 (integrates into GameBoard layout)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 only. Independently testable at /ui/game/{id}.
- **US2 (P2)**: Requires Phase 2 only for game list. Requires US1 for the board view that list items link to.
- **US3 (P3)**: Requires US1 (ActionLog integrates into GameBoard layout).

### Within Each User Story

- Hooks before components (data layer before UI)
- Leaf components (CardView, PhaseTracker) before composite components (GameBoard)
- All [P]-marked tasks within a story can run in parallel

### Parallel Opportunities

- T010, T011, T012 (CSS files) can all run in parallel
- T016, T017, T018, T019, T020 (leaf components for US1) can all run in parallel
- US1 and US2 hooks/components can be developed in parallel after Phase 2

---

## Parallel Example: User Story 1

```bash
# Launch all leaf components in parallel (different files, no dependencies):
Task: "Create CardView in frontend/src/components/CardView.tsx"
Task: "Create Battlefield in frontend/src/components/Battlefield.tsx"
Task: "Create PlayerZone in frontend/src/components/PlayerZone.tsx"
Task: "Create StackView in frontend/src/components/StackView.tsx"
Task: "Create PhaseTracker in frontend/src/components/PhaseTracker.tsx"

# Then compose them sequentially:
Task: "Create GameBoard in frontend/src/components/GameBoard.tsx" (depends on all above)
Task: "Wire GameBoard to useGameState hook" (depends on GameBoard + useGameState)
Task: "Add commander support to GameBoard" (depends on GameBoard wiring)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T014)
3. Complete Phase 3: User Story 1 (T015-T023)
4. **STOP and VALIDATE**: Navigate to /ui/game/{id} — board should show animated live game state
5. Demo with a running AI game

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 → Board view works → **MVP demo**
3. Add US2 → Game list + navigation → Multi-game support
4. Add US3 → Action log sidebar → Full observer experience
5. Polish → Edge cases, build verification → Production-ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable (except US3 which integrates into US1's GameBoard)
- The frontend/dist/ directory is gitignored — always rebuild with `npm run build`
- Total estimated scope: 35 tasks across 6 phases
- The backend changes are minimal (3 tasks: list endpoint, static files, test)

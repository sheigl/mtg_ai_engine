# Tasks: Observer AI Debug Panel

**Input**: Design documents from `specs/011-observer-ai-commentary/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in every task description

---

## Phase 1: Setup

**Purpose**: Create all new files and directories required by this feature before implementation begins.

- [X] T001 Create `mtg_engine/models/debug.py` (empty module with docstring)
- [X] T002 [P] Create `mtg_engine/export/debug_log.py` (empty module with docstring)
- [X] T003 [P] Create `mtg_engine/api/routers/debug.py` (empty module with docstring)
- [X] T004 [P] Create `ai_client/debug_forwarder.py` (empty module with docstring)
- [X] T005 [P] Create `ai_client/observer.py` (empty module with docstring)
- [X] T006 [P] Create `frontend/src/types/debug.ts` (empty file)
- [X] T007 [P] Create `frontend/src/hooks/useDebugLog.ts` (empty file)
- [X] T008 [P] Create `frontend/src/components/DebugPanel.tsx` (empty file)
- [X] T009 [P] Create `frontend/src/components/PromptResponseBlock.tsx` (empty file)
- [X] T010 [P] Create `frontend/src/components/CommentaryBlock.tsx` (empty file)
- [X] T011 [P] Create `frontend/src/styles/debug.css` (empty file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend debug log infrastructure that ALL user stories depend on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: All phases 3–6 depend on this phase being complete.

- [X] T012 Implement `DebugEntryType` enum and `DebugEntry`, `DebugEntryPatch` Pydantic v2 models in `mtg_engine/models/debug.py` per data-model.md (fields: entry_id, entry_type, source, turn, phase, step, timestamp, prompt, response, is_complete, rating, explanation, alternative)
- [X] T013 Implement `DebugLogRecorder` class in `mtg_engine/export/debug_log.py` with methods: `append_entry(entry)`, `patch_entry(entry_id, chunk, is_complete) → DebugEntry | None`, `get_all() → list[DebugEntry]`, `register_listener(callback)` — mirrors the pattern from `mtg_engine/export/transcript.py`
- [X] T014 Add `debug_log: DebugLogRecorder` field to `GameExportStore` in `mtg_engine/export/store.py`, initialized on game creation alongside existing `snapshots`, `transcript`, `rules_qa`
- [X] T015 Implement `POST /game/{game_id}/debug/entry` endpoint in `mtg_engine/api/routers/debug.py`: accepts `DebugEntry` body, appends to recorder, returns `{"data": {"entry_id": "..."}}` or 404 — per contracts/debug-api.md
- [X] T016 Implement `PATCH /game/{game_id}/debug/entry/{entry_id}` endpoint in `mtg_engine/api/routers/debug.py`: accepts `DebugEntryPatch` body, calls `recorder.patch_entry(...)`, returns updated entry or 404
- [X] T017 Implement `GET /game/{game_id}/debug` endpoint in `mtg_engine/api/routers/debug.py`: returns `{"data": {"game_id": ..., "entries": [...]}}` — per contracts/debug-api.md
- [X] T018 Register the debug router in `mtg_engine/api/main.py` alongside the existing game and export routers

**Checkpoint**: Engine accepts and stores debug entries. Verify with `curl -X POST http://localhost:8999/game/{id}/debug/entry` and `curl http://localhost:8999/game/{id}/debug`.

---

## Phase 3: User Story 1 — Real-Time Decision Commentary (Priority: P1) 🎯 MVP

**Goal**: Observer can enable a debug panel and see (a) the prompt + response for each playing AI action and (b) observer AI commentary rating each non-pass action. Panel is off by default.

**Independent Test**: Start a game with `python -m ai_client --debug ...`. Open the observer UI, enable the debug panel. Verify prompt/response blocks appear for each action and commentary blocks appear for each non-pass action with a rating and explanation.

### Implementation for User Story 1

- [X] T019 [P] [US1] Implement `DebugForwarder` class in `ai_client/debug_forwarder.py`: constructor takes `engine_url` and `game_id`; method `post_entry(entry: dict) → str` POSTs to `POST /game/{id}/debug/entry` via `httpx` and returns `entry_id`; method `patch_entry(entry_id, chunk, is_complete)` calls `PATCH /game/{id}/debug/entry/{entry_id}`
- [X] T020 [P] [US1] Add optional `debug_callback: Callable[[str, str, str], None] | None = None` parameter to `AIPlayer.__init__` in `ai_client/ai_player.py`; in `decide(prompt)`, if callback is set: call `callback("prompt", prompt, "")` before the LLM call and `callback("response", "", response_text)` after — keeps `AIPlayer` decoupled from HTTP
- [X] T021 [P] [US1] Implement `ObserverAI` class in `ai_client/observer.py`: constructor takes `client_config` (LLM base_url + model); method `analyze(game_state, chosen_action_desc, legal_actions, player_name, turn, phase, step) → dict` builds an observer prompt asking the LLM to rate the play (good/acceptable/suboptimal), explain why, and suggest a better alternative if suboptimal; calls LLM (non-streaming); returns dict with `rating`, `explanation`, `alternative`
- [X] T022 [US1] Wire `--debug` CLI flag and optional `--observer` flag into `ai_client/__main__.py`; when `--debug` is active: instantiate `DebugForwarder` and `ObserverAI`; register `DebugForwarder` callbacks on each `AIPlayer` via `debug_callback`; after each non-pass action resolves in `ai_client/game_loop.py`, call `observer.analyze(...)` and POST the commentary `DebugEntry` via `DebugForwarder.post_entry`
- [X] T023 [P] [US1] Implement TypeScript interfaces `DebugEntry`, `DebugLog`, `DebugEntryType`, `Rating` in `frontend/src/types/debug.ts` matching the Pydantic models from data-model.md
- [X] T024 [P] [US1] Implement `useDebugLog(gameId, enabled)` hook in `frontend/src/hooks/useDebugLog.ts`: when `enabled=false` returns empty entries; when `enabled=true` polls `GET /game/{gameId}/debug` via TanStack Query every 2s (same pattern as `useTranscript.ts`); returns `entries: DebugEntry[]`, `isLoading`, `isError`
- [X] T025 [P] [US1] Implement `PromptResponseBlock` component in `frontend/src/components/PromptResponseBlock.tsx`: renders a collapsible block showing `source` label + turn/step badge in the header; `prompt` text in a monospace box; `response` text below it; left border color keyed to source (use a simple map from source name → color); shows "(streaming…)" when `is_complete=false`
- [X] T026 [P] [US1] Implement `CommentaryBlock` component in `frontend/src/components/CommentaryBlock.tsx`: renders a collapsible block with "Observer AI" label + rating badge (green=good, yellow=acceptable, red=suboptimal) in the header; `explanation` text in the body; an optional "Better play:" section when `alternative` is non-null; amber left border to distinguish from playing AI blocks
- [X] T027 [P] [US1] Implement `DebugPanel` component in `frontend/src/components/DebugPanel.tsx`: a toggle button ("Debug Panel 🔍") that shows/hides the panel; panel renders a scrollable column of `DebugEntry` items sorted by `timestamp`, rendering each as `PromptResponseBlock` or `CommentaryBlock` depending on `entry_type`; shows "Debug panel off — click to enable" when disabled; shows "No debug data yet" when enabled but entries array is empty
- [X] T028 [P] [US1] Write debug panel CSS in `frontend/src/styles/debug.css`: panel layout (fixed width sidebar or collapsible drawer), block styles (header row, collapsible body, rating badge colors), scrollable container
- [X] T029 [US1] Integrate `DebugPanel` into `frontend/src/components/GameBoard.tsx`: import and render alongside the existing `ActionLog` sidebar; pass `gameId` and `enabled` state down; import `debug.css`

**Checkpoint**: Full US1 flow works end-to-end. Run `python -m ai_client --debug ...`, open UI, enable panel, verify prompt/response and commentary blocks appear for each non-pass action.

---

## Phase 4: User Story 2 — Streaming AI Prompt & Response Visibility (Priority: P2)

**Goal**: Prompt/response blocks update token-by-token as the AI responds (not all at once after it finishes). The frontend subscribes to SSE instead of polling during live games.

**Independent Test**: Watch a live game with the debug panel enabled. Verify the response text in a `PromptResponseBlock` grows character-by-character while the AI is deciding — not appearing all at once when it finishes. Verify the `is_complete` indicator changes when streaming ends.

### Implementation for User Story 2

- [X] T030 [P] [US2] Add SSE stream endpoint `GET /game/{game_id}/debug/stream` to `mtg_engine/api/routers/debug.py`: use FastAPI `StreamingResponse` with `media_type="text/event-stream"`; on connect, replay existing entries as `data:` events; register a `DebugLogRecorder` listener and push each new/patched entry as a `data:` event; send `:keepalive\n\n` comment every 15s; send `event: game_over\ndata: {"game_id":"..."}\n\n` when the game ends and close the stream
- [X] T031 [US2] Switch `AIPlayer.decide()` in `ai_client/ai_player.py` to use `stream=True` when a debug callback is registered: accumulate chunks for JSON parsing; call `callback("prompt_start", prompt, entry_id)` with the `entry_id` returned from the initial POST, then `callback("response_chunk", chunk, entry_id)` for each token, then `callback("response_done", "", entry_id)` on completion — update `DebugForwarder` in `ai_client/debug_forwarder.py` to handle these callback types by calling `PATCH` for each chunk
- [X] T032 [P] [US2] Update `useDebugLog` hook in `frontend/src/hooks/useDebugLog.ts` to use `EventSource` for live games: open `EventSource('/game/{gameId}/debug/stream')`; on each `message` event, upsert the parsed `DebugEntry` by `entry_id` into local state (append if new, merge `response` field if existing — handles streaming patches); on `game_over` event, close the `EventSource` and switch to a one-time `GET /game/{gameId}/debug` fetch via TanStack Query; keep the polling fallback from T024 for completed games where `is_game_over=true` on mount
- [X] T033 [US2] Update `PromptResponseBlock` in `frontend/src/components/PromptResponseBlock.tsx` to auto-scroll the response text box as new tokens arrive (similar to how `ActionLog` auto-scrolls); show a pulsing cursor indicator when `is_complete=false`; stop the cursor when `is_complete=true`
- [X] T034 [P] [US2] Add collapsible expand/collapse to both `PromptResponseBlock` and `CommentaryBlock`: clicking the header row toggles body visibility; blocks start expanded; add a ▼/▶ chevron in the header; collapsed state shows only the header with source + rating/type badge

**Checkpoint**: Watch token-by-token streaming in the panel during a live game. Verify blocks collapse and expand. Verify SSE reconnect works if the page reloads during a live game.

---

## Phase 5: User Story 3 — Per-Player Attributed History (Priority: P3)

**Goal**: Every block is labeled with source, turn, and step. Historical completed games show the full persisted log in chronological order.

**Independent Test**: Observe a 3-turn game to completion. Reload the page. Select the completed game. Enable the debug panel. Verify all prompt/response and commentary blocks are present, correctly labeled with player names, turns, and steps, in chronological order.

### Implementation for User Story 3

- [X] T035 [P] [US3] Update block headers in `frontend/src/components/PromptResponseBlock.tsx` and `frontend/src/components/CommentaryBlock.tsx` to display all label fields: source name, turn number, phase, and step — e.g. `"Llama — Turn 3 / precombat_main / main"` — using the `source`, `turn`, `phase`, `step` fields from `DebugEntry`
- [X] T036 [US3] Ensure `useDebugLog` in `frontend/src/hooks/useDebugLog.ts` correctly handles completed games on initial load: if `isGameOver` (from `useGameState`) is `true` when the panel is first enabled, skip EventSource and go directly to a single `GET /game/{gameId}/debug` fetch; return entries sorted by `timestamp` ascending
- [X] T037 [P] [US3] Add auto-scroll-to-bottom behaviour to `DebugPanel` in `frontend/src/components/DebugPanel.tsx`: when new entries are appended, scroll the panel to the bottom (same `useEffect` + `ref` pattern used in `frontend/src/components/ActionLog.tsx`)
- [X] T038 [P] [US3] Ensure the SSE endpoint in `mtg_engine/api/routers/debug.py` replays all existing entries in `timestamp` order on new client connections, so a browser that connects after several actions have already occurred sees the full history before live updates begin

**Checkpoint**: Complete a game to `game_over`. Reload the page. Select the game. Enable the debug panel. Verify all blocks appear with correct labels in turn order.

---

## Phase 6: User Story 4 — Alternative Play Suggestions for Suboptimal Actions (Priority: P4)

**Goal**: When the observer AI rates a play as "suboptimal", the commentary block shows a concrete "Better play:" suggestion naming a specific alternative action that was available.

**Independent Test**: Cause the AI to make a clearly suboptimal play (e.g., cast Giant Growth with no creatures on board — already prevented by BUG-11 fix, but others exist). Verify the commentary block shows a "Better play:" section with a specific named action.

### Implementation for User Story 4

- [X] T039 [P] [US4] Update the observer prompt in `ai_client/observer.py` to explicitly instruct the LLM: when rating a play as "suboptimal", it MUST name a specific alternative from the provided legal action list; format the legal actions as a numbered list in the prompt so the observer can reference them by description; instruct the LLM to respond in JSON: `{"rating": "...", "explanation": "...", "alternative": "..." | null}`
- [X] T040 [US4] Update `ObserverAI.analyze()` in `ai_client/observer.py` to parse the `alternative` field from the LLM JSON response and include it in the `DebugEntry` when non-null; if the play is rated `"good"` or `"acceptable"`, always set `alternative` to `null`
- [X] T041 [US4] Update `CommentaryBlock` in `frontend/src/components/CommentaryBlock.tsx` to render the "Better play:" section when `entry.alternative` is non-null: display it below the explanation in a visually distinct box (e.g., dashed border, muted background) with a "💡 Better play:" label

**Checkpoint**: Run a game with `--debug`. Find a commentary block rated "suboptimal". Verify the "Better play:" section is visible and names a specific card or action.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Reliability, UX polish, and validation across all user stories.

- [X] T042 [P] Add observer AI timeout handling in `ai_client/observer.py`: if the LLM call exceeds 15 seconds or raises an exception, POST a placeholder `DebugEntry` with `rating=null`, `explanation="Analysis unavailable"`, `is_complete=true` — satisfying FR-012
- [X] T043 [P] Persist the debug panel toggle preference in `localStorage` key `mtg_debug_panel_enabled` in `frontend/src/components/DebugPanel.tsx`; read on mount so preference survives page refresh
- [X] T044 [P] Add "No debug data for this game" empty-state message to `DebugPanel` in `frontend/src/components/DebugPanel.tsx`: shown when the panel is enabled and the `entries` array is empty (i.e., game was run without `--debug`)
- [X] T045 [P] Add `--observer` CLI arg to `ai_client/__main__.py` (separate LLM endpoint/model for observer AI); default to same endpoint as playing AIs if not provided — per quickstart.md
- [ ] T046 Run end-to-end validation per `specs/011-observer-ai-commentary/quickstart.md`: start engine, run `python -m ai_client --debug`, open UI, enable panel, verify all 4 user story behaviours work in a single game

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — all T001–T011 can start immediately and run in parallel
- **Foundational (Phase 2)**: Depends on Setup completion — T012–T018 must be sequenced as listed (models → recorder → store → endpoints → registration); **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational complete; T019–T022 (backend/AI client) can run in parallel with T023–T028 (frontend) since they touch different files; T029 depends on T022–T028
- **US2 (Phase 4)**: Depends on US1 complete; T030 (SSE endpoint) can run parallel with T031 (AI client streaming); T032–T034 depend on T030–T031
- **US3 (Phase 5)**: Depends on US1 complete; all of T035–T038 can run in parallel with each other
- **US4 (Phase 6)**: Depends on US1 complete (observer AI exists); T039–T041 are sequential
- **Polish (Phase 7)**: Depends on all desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational — no dependency on US2/US3/US4
- **US2 (P2)**: Depends on US1 (modifies existing AI client + hook + components)
- **US3 (P3)**: Depends on US1 (labels already in DebugEntry from Foundational; this phase adds their display and the historical view)
- **US4 (P4)**: Depends on US1 (extends ObserverAI; adds CommentaryBlock "Better play:" section)

US2, US3, US4 can proceed in parallel once US1 is complete (they touch different files).

### Within Each User Story

- Models/types before services
- Backend endpoints before frontend hooks that call them
- Hooks before components that use them
- Components before integration into GameBoard

### Parallel Opportunities

**Phase 1** (Setup): T001–T011 all parallel
**Phase 2** (Foundational): Sequential chain (T012→T013→T014→T015→T016→T017→T018)
**Phase 3** (US1): Backend cluster (T019, T020, T021) parallel; then T022; Frontend cluster (T023–T028) parallel with backend cluster; T029 depends on both clusters
**Phase 4** (US2): T030 and T031 parallel; then T032→T033→T034
**Phase 5** (US3): T035, T036, T037, T038 all parallel
**Phase 6** (US4): T039→T040→T041 sequential
**Phase 7** (Polish): T042, T043, T044, T045 all parallel; T046 depends on all

---

## Parallel Example: User Story 1

```bash
# These can run concurrently (different files):
Task T019: Implement DebugForwarder in ai_client/debug_forwarder.py
Task T020: Add debug_callback to AIPlayer in ai_client/ai_player.py
Task T021: Implement ObserverAI class in ai_client/observer.py
Task T023: Create TypeScript types in frontend/src/types/debug.ts
Task T024: Implement useDebugLog hook (polling) in frontend/src/hooks/useDebugLog.ts
Task T025: Implement PromptResponseBlock in frontend/src/components/PromptResponseBlock.tsx
Task T026: Implement CommentaryBlock in frontend/src/components/CommentaryBlock.tsx
Task T027: Implement DebugPanel container in frontend/src/components/DebugPanel.tsx
Task T028: Write debug.css in frontend/src/styles/debug.css

# Then sequentially:
Task T022: Wire --debug flag, DebugForwarder, ObserverAI in game_loop.py (depends on T019–T021)
Task T029: Integrate DebugPanel into GameBoard.tsx (depends on T022–T028)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T011)
2. Complete Phase 2: Foundational (T012–T018) — CRITICAL gate
3. Complete Phase 3: User Story 1 (T019–T029)
4. **STOP and VALIDATE**: Run a game with `--debug`, open UI, confirm panel shows prompts and commentary
5. Merge as MVP — the panel is functional even without token streaming, collapsible blocks, or historical view

### Incremental Delivery

1. Setup + Foundational → Backend accepts debug entries
2. **US1** → Panel toggle, basic prompt/response blocks, observer commentary ← **Demo here**
3. **US2** → Token-by-token streaming, SSE, collapsible blocks ← Better UX
4. **US3** → Labels, historical game view ← Full feature-complete
5. **US4** → Alternative suggestions in suboptimal commentary ← Nice-to-have
6. Polish → Timeout handling, localStorage, empty state, observer model flag

---

## Notes

- [P] tasks = different files, no shared state dependencies
- [Story] label maps each task to its user story for traceability
- Each user story is independently completable: US1 is a complete MVP; US2–US4 each add a distinct capability
- The SSE endpoint (T030) is the only materially new backend pattern; all other backend tasks follow existing FastAPI/Pydantic patterns in the codebase
- The `--debug` flag (T022) controls all overhead: without it, no debug entries are posted, no observer AI calls are made, and the SSE stream returns an empty log — zero impact on game performance
- Commit after each phase checkpoint to enable easy rollback per user story

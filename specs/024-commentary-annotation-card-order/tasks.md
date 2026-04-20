# Tasks: Commentary Annotations, Rating Override & Card Ordering

**Input**: Design documents from `/specs/024-commentary-annotation-card-order/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/debug-api.md ✓, quickstart.md ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. No tests were requested; test tasks are omitted.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project structure needed — all changes are additive modifications to existing files. This phase updates shared type definitions consumed by all three stories.

- [X] T001 Add `player_annotation: str | None = None` and `player_rating_override: str | None = None` fields to `DebugEntry` in `mtg_engine/models/debug.py`
- [X] T002 Add `player_annotation: string | null` and `player_rating_override: string | null` to the `DebugEntry` interface in `frontend/src/types/debug.ts`

**Checkpoint**: Both backend model and frontend type updated — all stories can now reference these fields

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend recorder methods and SSE emission — required by both US1 (annotations) and US2 (rating override) before any endpoint or UI work

- [X] T003 Add `annotate_entry(entry_id, text)` method to `DebugLogRecorder` in `mtg_engine/export/debug_log.py` — sets `player_annotation`, strips whitespace, sets to `None` for blank/null input, fires listener so SSE picks it up
- [X] T004 Add `rerate_entry(entry_id, rating)` method to `DebugLogRecorder` in `mtg_engine/export/debug_log.py` — sets `player_rating_override`, validates value is one of `good`/`acceptable`/`suboptimal`/`None`, never modifies `rating`, fires listener

**Checkpoint**: Recorder methods ready — endpoint and UI work for US1 and US2 can now begin

---

## Phase 3: User Story 1 — Annotate Observer & AI Commentary (Priority: P1) 🎯 MVP

**Goal**: Player can add, edit, and delete free-text annotations on completed debug entries; annotations appear in the panel and in the exported game log.

**Independent Test**: Start a game, wait for any commentary entry to complete, add annotation text, download game log, verify "Player Comment:" line appears inline with that entry.

### Backend — Annotation Endpoint & Export

- [X] T005 [US1] Add `PATCH /game/{game_id}/debug/entry/{entry_id}/annotate` endpoint in `mtg_engine/api/routers/debug.py` — calls `DebugLogRecorder.annotate_entry()`, returns 404 if entry not found, returns 409 if `is_complete` is False, returns 422 for whitespace-only text, emits SSE update with full entry
- [X] T006 [P] [US1] Extend `build_game_log()` in `mtg_engine/export/game_log.py` to accept an optional `debug_entries: list[dict]` parameter and merge observer commentary and AI prompt/response entries into the turn timeline, rendering `player_annotation` as "Player Comment: {text}" below each entry (omit line when `None`)
- [X] T007 [P] [US1] Update `export_game_log()` in `mtg_engine/api/routers/export.py` to fetch debug entries from the export store and pass them to `build_game_log()`

### Frontend — Annotation UI

- [X] T008 [US1] Add annotation input UI to `CommentaryBlock` in `frontend/src/components/CommentaryBlock.tsx` — show "Add Comment" button only when `entry.is_complete` is true; clicking opens an inline textarea with Save/Cancel; on Save, PATCH to `/game/{gameId}/debug/entry/{entry.entry_id}/annotate`; display saved annotation beneath the commentary block; show Edit/Delete controls when annotation exists
- [X] T009 [US1] Add annotation input UI to `PromptResponseBlock` in `frontend/src/components/PromptResponseBlock.tsx` — same pattern as T008 (Add Comment / inline textarea / Save/Cancel / display with Edit/Delete), no rating controls
- [X] T010 [US1] Add annotation input and display styles to `frontend/src/styles/debug.css` — annotation textarea, save/cancel buttons, saved annotation display, edit/delete inline controls

**Checkpoint**: User Story 1 complete — annotations visible in panel and game log export

---

## Phase 4: User Story 2 — Override Observer AI Rating (Priority: P2)

**Goal**: Player can override the Good/Acceptable/Suboptimal rating on a completed observer commentary entry; original AI rating is preserved; both appear in game log.

**Independent Test**: Start a game with observer enabled, wait for a commentary entry with a rating, click the rating badge, select a different rating, verify display shows override (visually distinct), download game log and verify both original and override appear.

### Backend — Rerate Endpoint & Export

- [X] T011 [US2] Add `PATCH /game/{game_id}/debug/entry/{entry_id}/rerate` endpoint in `mtg_engine/api/routers/debug.py` — calls `DebugLogRecorder.rerate_entry()`, returns 404 if entry not found, returns 422 if `entry_type != "commentary"` or rating value invalid, never modifies `rating` field, emits SSE update with full entry
- [X] T012 [US2] Extend the game log output in `mtg_engine/export/game_log.py` (in the function updated in T006) to render `player_rating_override` as "Player Rating Override: {value}" below the AI rating line (omit line when `None`); ensure original `rating` line is always rendered when present

### Frontend — Rating Override UI

- [X] T013 [US2] Add rating override picker to `CommentaryBlock` in `frontend/src/components/CommentaryBlock.tsx` — clicking the existing rating badge opens a 3-option picker (Good / Acceptable / Suboptimal) plus a "Reset" option; selecting an option PATCHes to `/game/{gameId}/debug/entry/{entry.entry_id}/rerate`; when `player_rating_override` is set, display override rating prominently with an "override" indicator badge and show original AI rating in a dimmed style beneath it
- [X] T014 [US2] Add override rating badge styles to `frontend/src/styles/debug.css` — override badge styling (distinct from AI badge), dimmed original rating, rating picker popup

**Checkpoint**: User Story 2 complete — rating overrides visible in panel (with original preserved) and in game log export

---

## Phase 5: User Story 3 — Reorder Cards in Hand and Battlefield (Priority: P3)

**Goal**: Player can drag cards within their hand or battlefield to change visual order; purely cosmetic, no server communication.

**Independent Test**: Start a game, wait for cards in hand and permanents on battlefield, drag a card to a new position, verify it stays there, play a card or have one die and verify remaining order is maintained.

### Hand Reordering

- [X] T015 [P] [US3] Add `handOrder` state (`string[]`) to `HumanGameBoard` in `frontend/src/components/HumanGameBoard.tsx` — initialize from `humanPlayer.hand` card IDs; reconcile on each game state update (remove missing IDs, append new IDs at end, preserve existing order); pass as prop to `InteractiveHand`
- [X] T016 [P] [US3] Update `InteractiveHand` in `frontend/src/components/InteractiveHand.tsx` — accept `handOrder: string[]` prop and `onReorder: (newOrder: string[]) => void` prop; sort rendered cards by `handOrder` before display; add intra-zone drag-to-reorder using a separate `reorderDragCardId` ref (distinct from the existing card-play drag); `onDragOver` on the container calculates the drop index and calls `onReorder` with the updated order; disable reorder drag when `isPending` is true

### Battlefield Reordering

- [X] T017 [P] [US3] Add `permanentOrder` state (`string[]`) to `HumanGameBoard` in `frontend/src/components/HumanGameBoard.tsx` — initialize from `humanPermanents` permanent IDs; reconcile on each game state update (same strategy as handOrder); pass as prop to the human `Battlefield`
- [X] T018 [P] [US3] Update `Battlefield` in `frontend/src/components/Battlefield.tsx` — accept optional `permanentOrder: string[]` prop and `onReorder?: (newOrder: string[]) => void` prop; when `permanentOrder` is provided, sort rendered permanents by that order before display; add intra-zone drag-to-reorder on non-opponent battlefield (guard with `!isOpponent`); drag uses HTML5 drag events, separate from card-play drag; disable when `isPending` (passed as new optional prop)

### Drag Disambiguation

- [X] T019 [US3] Update `HumanGameBoard` in `frontend/src/components/HumanGameBoard.tsx` to wire `onReorder` callbacks for both hand and battlefield — `handOrder` and `permanentOrder` setters passed to children; verify that the existing card-play `onDragStart`/`onDrop` on the battlefield div does not interfere with intra-zone reorder events (card-play drag only fires when `draggedCardId` is set by `InteractiveHand`'s play-drag handler, which is distinct from the reorder drag)

**Checkpoint**: User Story 3 complete — hand and battlefield reordering work independently of game mechanics

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 [P] Verify all three features work together in a single game session: annotate an entry, override its rating, reorder hand, verify game log export includes annotation and both ratings
- [X] T021 [P] Run `python -m pytest tests/ -v` from project root to confirm no regressions in existing tests
- [X] T022 [P] Run `cd frontend && npm run build` to confirm no TypeScript errors from new props and type fields
- [X] T023 Verify `player_annotation` and `player_rating_override` fields are `None` by default in all existing tests and existing entry serialization (no regression in `GET /game/{game_id}/debug` or SSE stream shape)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS US1 and US2 backend work
- **Phase 3 (US1)**: Depends on Phase 2; T006 and T007 can run in parallel after T005
- **Phase 4 (US2)**: Depends on Phase 2; T012 depends on T006 (same function); T011 and T013 can start after Phase 2
- **Phase 5 (US3)**: Independent of Phases 3 and 4 — can start after Phase 1 (no backend changes needed)
- **Phase 6 (Polish)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 foundational methods
- **US2 (P2)**: Depends on Phase 2 foundational methods; T012 adds to the game log function updated in T006 (coordinate or sequence)
- **US3 (P3)**: Depends only on Phase 1 type update (T002); fully independent of US1 and US2

### Parallel Opportunities

- T001 and T002 (Phase 1) can run in parallel — different files
- T003 and T004 (Phase 2) can run in parallel — different methods in same file (coordinate)
- T006 and T007 (US1 backend) can run in parallel — different files
- T008 and T009 (US1 frontend) can run in parallel — different components
- T015 and T016 (US3 hand) can run in parallel with T017 and T018 (US3 battlefield)
- T020, T021, T022 (Polish) can all run in parallel

---

## Parallel Example: User Story 1

```
After Phase 2 completes:
  [parallel] T006 — Extend build_game_log() in mtg_engine/export/game_log.py
  [parallel] T007 — Update export_game_log() in mtg_engine/api/routers/export.py
  [parallel] T008 — Annotation UI in CommentaryBlock.tsx
  [parallel] T009 — Annotation UI in PromptResponseBlock.tsx
  [parallel] T010 — Annotation styles in debug.css
Then: T005 — /annotate endpoint (calls recorder methods from Phase 2)
```

## Parallel Example: User Story 3

```
After T002 completes (frontend type):
  [parallel group A]
    T015 — handOrder state in HumanGameBoard.tsx
    T016 — InteractiveHand reorder support
  [parallel group B]
    T017 — permanentOrder state in HumanGameBoard.tsx
    T018 — Battlefield reorder support
Then: T019 — wire callbacks + verify drag disambiguation in HumanGameBoard.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: T001, T002
2. Complete Phase 2: T003, T004
3. Complete Phase 3 (US1): T005 → T006, T007, T008, T009, T010 (parallel) 
4. **STOP and VALIDATE**: Add annotation in panel → download log → verify "Player Comment:" line
5. Usable training-data capture is live

### Incremental Delivery

1. Phase 1 + 2 → shared foundation ready
2. Phase 3 (US1) → annotations in panel + game log (MVP)
3. Phase 4 (US2) → rating override (T011 + T012 + T013 + T014)
4. Phase 5 (US3) → card reordering (fully independent, can be done anytime after Phase 1)
5. Phase 6 → polish + regression check

---

## Notes

- [P] tasks operate on different files; no write conflicts
- US3 (card reordering) is fully independent of US1/US2 and can be worked on in any order after Phase 1
- T012 (game log rerate rendering) extends the same function modified by T006 — sequence or coordinate these two tasks to avoid conflicts
- Original `rating` field on `DebugEntry` must never be set or modified by T003, T005, T011, or T013 — this is the core training-data invariant
- Commit after each checkpoint to keep history clean

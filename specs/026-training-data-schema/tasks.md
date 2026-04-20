# Tasks: Training Data Schema — Decision-Centric MongoDB Persistence

**Input**: Design documents from `/specs/026-training-data-schema/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project structure is required — this is an existing Python/FastAPI project. This phase is minimal.

- [X] T001 Read and confirm the full data-model.md document so the implementation uses correct field names throughout all phases

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model changes and infrastructure that ALL user stories depend on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: Complete all tasks in this phase before starting Phase 3+.

- [X] T002 Add `snapshot_id: str | None = None` and `related_entry_id: str | None = None` fields to `DebugEntry` in `mtg_engine/models/debug.py`; no other changes to this file

- [X] T003 [P] Add `decision_id: str | None = None` field to `QAPair` in `mtg_engine/export/rules_qa.py`; update all `_qa_*` template functions and `_base_ctx` to propagate `decision_id` when present

- [X] T004 [P] Add three new collection getter functions to `mtg_engine/persistence/mongo_client.py`: `get_decisions_collection()`, `get_rules_qa_collection()`, `get_transcript_collection()` — each mirrors the pattern of `get_games_collection()` but targets `decisions`, `rules_qa`, and `transcript` collection names; also add an async `ensure_indexes()` function that creates all indexes defined in research.md section 10 using `create_index`

- [X] T005 Call `await ensure_indexes()` inside the `lifespan` context manager in `mtg_engine/api/main.py` immediately after MongoDB is confirmed configured; import from `mtg_engine.persistence.mongo_client`

- [X] T006 Add `current_snapshot_id: str | None = None` attribute to `GameExportStore` in `mtg_engine/export/store.py`; update `get_export_store()` to instantiate `MongoGamePersister` with all four collections (`get_games_collection()`, `get_decisions_collection()`, `get_rules_qa_collection()`, `get_transcript_collection()`) by passing them to the constructor

- [X] T007 Rewrite `MongoGamePersister` in `mtg_engine/persistence/game_persister.py` with the following normalized behavior:
  - Constructor accepts `game_id`, `games_col`, `decisions_col`, `rules_qa_col`, `transcript_col`
  - `init_game_document()`: writes metadata-only `games` doc (no embedded arrays: no `transcript`, `snapshots`, `debug_entries`, `rules_qa` fields)
  - `_on_snapshot_finalized(snap)`: upserts a `decisions` document using `snap.snapshot_id` as `_id`, setting `game_id`, `snapshot_id`, `sequence_number` (via per-game `_sequence_counter`), `turn`, `phase`, `step`, `active_player` (from `snap.game_state["priority_holder"]`), `board_state`, `legal_actions`, `action_taken`, `action_taken_by`, `created_at`; uses `$setOnInsert` for immutable fields and `$set` for action fields
  - `_on_debug_entry(entry)` when `is_complete=True` and `entry.snapshot_id` is not None: if `entry_type == "prompt_response"`, upsert `decisions.llm_reasoning` sub-doc; if `entry_type == "commentary"`, upsert `decisions.observer_evaluation` sub-doc; both via `$set` using `entry.snapshot_id` as filter `_id`
  - `_on_transcript_entry(entry)`: inserts to `transcript` collection with `game_id` and `sequence_number` = `entry.seq`; triggers `_finalize_game()` on `game_end` event
  - `_on_rules_qa_entry(entry)`: inserts to `rules_qa` collection (includes `decision_id` field already on `QAPair`)
  - `_finalize_game()`: sets `games.is_complete`, `games.completed_at`, `games.outcome`; then bulk-updates all `decisions` for the game with `outcome_context` using MongoDB aggregation-pipeline update: `[{ "$set": { "outcome_context": { "winner": winner, "winning_player": winning_player, "total_turns": total_turns, "active_player_won": { "$eq": ["$active_player", winner] } } } }]`
  - `update_debug_entry(entry)`: updates `decisions.llm_reasoning.player_annotation` and `decisions.llm_reasoning.player_rating_override` using `entry.snapshot_id` as the filter on `decisions._id`

- [X] T008 Update `GET /game/{game_id}/legal-actions` in `mtg_engine/api/routers/game.py`: store the returned `Snapshot.snapshot_id` into `store.current_snapshot_id` and include `"snapshot_id": snap.snapshot_id` in the response `data` dict

**Checkpoint**: Foundation complete — model changes, MongoDB collections, persister, and API response all updated. All user stories can now be built on this foundation.

---

## Phase 3: User Story 1 — Retrieve a Complete Training Example (Priority: P1) 🎯 MVP

**Goal**: A single `decisions` document fetch returns everything needed to train a model — no secondary queries.

**Independent Test**: After a completed game with an LLM player and observer, fetch `GET /games/records/{game_id}/decisions`, pick the first result, and verify it contains `board_state`, `legal_actions`, `action_taken`, `llm_reasoning` (non-null), `observer_evaluation` (non-null), and `outcome_context` — all in one document.

- [X] T009 [US1] Add `GET /games/records/{game_id}/decisions` endpoint to `mtg_engine/api/routers/game_records.py`: queries `decisions` collection with `{ game_id: game_id }` filter sorted by `sequence_number` ascending; returns `{ data: { game_id, decisions: [...], count: N } }`; returns 404 if no decisions found for the game_id; returns 503 if MongoDB not configured

- [X] T010 [US1] Update `GET /games/records/{game_id}` in `mtg_engine/api/routers/game_records.py` to query the `games` collection only (metadata fields; no embedded `transcript`, `snapshots`, `debug_entries`, `rules_qa` — those no longer exist in the document)

- [X] T011 [US1] Update `GET /games/records` (list endpoint) in `mtg_engine/api/routers/game_records.py` to remove references to embedded arrays in the projection (remove `"snapshots": 0` default exclusion since that field no longer exists); ensure the `fields` query parameter still works for valid game metadata fields

**Checkpoint**: A data scientist can fetch all training examples for a game from a single endpoint. Verify US1 acceptance scenario 1 and 2 pass (heuristic game has `llm_reasoning: null`).

---

## Phase 4: User Story 2 — Filter Training Data by Player and Outcome (Priority: P2)

**Goal**: Decisions can be filtered by `active_player` and `outcome_context.active_player_won` using indexed queries.

**Independent Test**: Run a completed game as Alice vs Bob. Query `GET /games/records/{game_id}/decisions?active_player=Alice` and verify every result has `active_player == "Alice"` and `outcome_context.active_player_won` correctly reflects whether Alice won.

- [X] T012 [US2] Add optional query parameters `active_player: str | None` and `won: bool | None` to `GET /games/records/{game_id}/decisions` in `mtg_engine/api/routers/game_records.py`; when `active_player` is provided, add `{ "active_player": active_player }` to the MongoDB query filter; when `won` is provided, add `{ "outcome_context.active_player_won": won }` to the filter

- [X] T013 [US2] Add cross-game decisions list endpoint `GET /games/decisions` to `mtg_engine/api/routers/game_records.py` with optional query params: `active_player: str | None`, `won: bool | None`, `observer_rating: str | None`, `limit: int = 100`; queries `decisions` collection directly; returns `{ data: { decisions: [...], count: N } }`; this endpoint enables training set construction across multiple games

**Checkpoint**: Researcher can enumerate all winning Alice decisions across all games with a single query. Verify US2 acceptance scenarios pass.

---

## Phase 5: User Story 3 — Observer Evaluation Linked to Decision (Priority: P3)

**Goal**: Observer evaluations are stored inside the decision document; annotate/rerate updates target the correct decisions doc; filtering by `observer_evaluation.rating` works.

**Independent Test**: After a game where the observer rated some decisions as `suboptimal`, query `GET /games/decisions?observer_rating=suboptimal` and verify each result contains both `llm_reasoning` and `observer_evaluation` in the same document.

- [X] T014 [US3] Update `ai_client/game_loop.py`: (a) store `snapshot_id` from the `legal-actions` response into a local variable before creating the player debug entry; (b) include `"snapshot_id": snapshot_id` in the player debug entry dict passed to `self._forwarder.post_entry()`; (c) pass `snapshot_id` and the player's `_debug_entry_id` as `related_entry_id` into `_observe_action()`; (d) in `_observe_action()`, include `"snapshot_id": snapshot_id` and `"related_entry_id": player_entry_id` in the observer entry dict

- [X] T015 [US3] Update `ai_client/hybrid_game_loop.py` with the same `snapshot_id` propagation pattern applied in T014, wherever debug entries are created

- [X] T016 [US3] Update `PATCH /game/{game_id}/debug/entry/{entry_id}/annotate` in `mtg_engine/api/routers/debug.py`: after calling `store.debug_log.annotate_entry()`, call `store.persister.update_debug_entry(updated)` using the entry's `snapshot_id` (not the embedded array path); the persister method already handles this via `decisions._id == entry.snapshot_id`

- [X] T017 [US3] Update `PATCH /game/{game_id}/debug/entry/{entry_id}/rerate` in `mtg_engine/api/routers/debug.py` with the same persister call pattern as T016

- [X] T018 [US3] Add `observer_rating` query param support to `GET /games/records/{game_id}/decisions` and `GET /games/decisions` in `mtg_engine/api/routers/game_records.py`; when provided, add `{ "observer_evaluation.rating": observer_rating }` to the filter

**Checkpoint**: Observer evaluations appear embedded in decisions. Annotation updates persist. Rating filter works. Verify US3 acceptance scenarios pass including the manual annotation scenario.

---

## Phase 6: User Story 4 — Rules Q&A in Context (Priority: P4)

**Goal**: Each `rules_qa` document has a `decision_id` linking it to the priority grant during which it was triggered.

**Independent Test**: After a game where a rules Q&A was triggered (SBA, trample, deathtouch, etc.), query `GET /games/records/{game_id}/rules-qa` (or MongoDB directly) and verify each entry has a non-null `decision_id` that matches an existing `decisions._id`.

- [X] T019 [US4] Update `RulesQARecorder` in `mtg_engine/export/rules_qa.py`: add `decision_id` parameter (defaulting to `None`) to `on_sba()`, `on_damage()`, `on_trample()`, `on_layer_interaction()`, `on_replacement()` — pass it through to each `_qa_*` template call so `QAPair.decision_id` is set

- [X] T020 [US4] Update all call sites in the engine that invoke `rules_qa.on_sba()`, `on_damage()`, `on_trample()`, `on_layer_interaction()`, `on_replacement()` to pass `decision_id=store.current_snapshot_id` — search for these call sites with `grep -rn "rules_qa\.on_" mtg_engine/` and update each one

- [X] T021 [US4] Add `GET /games/records/{game_id}/rules-qa` endpoint to `mtg_engine/api/routers/game_records.py` that queries the `rules_qa` collection with `{ game_id: game_id }` filter, sorted by `decision_id`; returns `{ data: { game_id, rules_qa: [...], count: N } }`

**Checkpoint**: Rules Q&A entries are linked to specific decisions. Verify US4 acceptance scenario: Q&A `decision_id` matches corresponding `decisions._id`.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 [P] Update `GET /export/{game_id}/game-log` in `mtg_engine/api/routers/export.py` to remove the MongoDB fallback path that reads `doc.get("transcript")`, `doc.get("snapshots")`, `doc.get("debug_entries")` from the `games` document (those embedded arrays are gone); the in-memory fallback (`store.transcript.to_json()` etc.) is the only path needed now

- [X] T023 [P] Add `GET /games/records/{game_id}/transcript` endpoint to `mtg_engine/api/routers/game_records.py` that queries the `transcript` collection with `{ game_id: game_id }` sorted by `sequence_number` ascending; returns `{ data: { game_id, transcript: [...], count: N } }`

- [X] T024 Register the `game_records` router in `mtg_engine/api/main.py` if it is not already registered; verify `GET /games/records`, `GET /games/records/{game_id}`, `GET /games/records/{game_id}/decisions`, `GET /games/decisions` are all reachable

- [X] T025 Run `python -m pytest tests/ -v` and fix any test failures caused by the schema changes; particularly `tests/api/test_api.py` which tests the existing game endpoints and may need updates for the new `legal-actions` response format (added `snapshot_id` field)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: No story dependencies — BLOCKS all user story phases
  - T002 and T003/T004 can run in parallel
  - T005 depends on T004
  - T006 depends on T002, T003, T004
  - T007 depends on T002, T003, T004, T006
  - T008 depends on T006
- **Phase 3 (US1)**: Depends on Phase 2 complete
- **Phase 4 (US2)**: Depends on Phase 3 complete (adds params to US1 endpoint)
- **Phase 5 (US3)**: Depends on Phase 2 complete; independent of Phase 3/4
- **Phase 6 (US4)**: Depends on T003 (rules_qa collection), T006 (persister writes); independent of Phase 3/4/5
- **Phase 7 (Polish)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 foundational — implement first
- **US2 (P2)**: Depends on US1 (extends the decisions endpoint)
- **US3 (P3)**: Depends on Phase 2 foundational — can run in parallel with US1
- **US4 (P4)**: Depends on T003 + T007 only — can run in parallel with US1 and US3

### Parallel Opportunities Within Phase 2

```bash
# These three can run in parallel:
T002: Add snapshot_id/related_entry_id to DebugEntry
T003: Add QAPair.decision_id + update templates
T004: Add collection getters + ensure_indexes() to mongo_client.py
```

---

## Parallel Example: Phase 2 Foundation

```bash
# Run in parallel (different files):
Task T002: "Add snapshot_id, related_entry_id to DebugEntry in mtg_engine/models/debug.py"
Task T003: "Add decision_id to QAPair in mtg_engine/export/rules_qa.py"
Task T004: "Add collection getters + ensure_indexes to mtg_engine/persistence/mongo_client.py"

# Sequential after T002/T003/T004:
Task T005: "Call ensure_indexes() in lifespan in mtg_engine/api/main.py"
Task T006: "Update GameExportStore wiring in mtg_engine/export/store.py"
Task T007: "Rewrite MongoGamePersister in mtg_engine/persistence/game_persister.py"
Task T008: "Update legal-actions to return snapshot_id in mtg_engine/api/routers/game.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T008) — critical path
3. Complete Phase 3: User Story 1 (T009–T011)
4. **STOP and VALIDATE**: Start a game, run AI client, fetch `GET /games/records/{game_id}/decisions`, confirm self-contained documents
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → normalized schema live, all collections written
2. US1 → decisions endpoint — ML engineers can start pulling training data
3. US2 → add outcome filtering — stratified training sets
4. US3 → observer evaluation + annotations — quality filtering and human feedback loop
5. US4 → rules Q&A linkage — context-aware Q&A training data

---

## Notes

- All MongoDB writes remain fire-and-forget (`_schedule` pattern) — game execution is never blocked
- The aggregation-pipeline `update_many` in `_finalize_game()` requires MongoDB 4.2+ (motor 3.x supports this)
- `snapshot_id` is `None` for heuristic players (no debug entry) but the `decisions` document is still created from the snapshot
- `active_player_won` is computed server-side via aggregation pipeline — no Python-side loop over decisions needed
- The `export.py` game-log endpoint intentionally keeps in-memory fallback only; MongoDB transcript collection is for training data, not live game display

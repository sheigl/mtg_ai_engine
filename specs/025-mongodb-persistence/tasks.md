# Tasks: MongoDB Game Data Persistence

**Input**: Design documents from `/specs/025-mongodb-persistence/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/persistence-api.md ✓, quickstart.md ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. No tests were requested; test tasks are omitted.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the only new dependency and create the new module directory.

- [X] T001 Add `motor>=3.3.0` to `requirements.txt`
- [X] T002 Create `mtg_engine/persistence/__init__.py` (empty file — establishes the new persistence module)

**Checkpoint**: Dependency declared, module directory ready — foundational code can now be written

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: MongoDB client, the persister class, and the hooks into existing recorders — required by all three user stories before any endpoint or integration work.

- [X] T003 Create `mtg_engine/persistence/mongo_client.py` — read `MONGODB_URL` env var (fallback to `MONGODB_DATABASE` and `MONGODB_COLLECTION` overrides); expose `is_configured() -> bool`, `get_games_collection() -> AsyncIOMotorCollection | None`, and a module-level `AsyncIOMotorClient` singleton initialized lazily on first call; return `None` for all functions when not configured
- [X] T004 Add listener support to `SnapshotRecorder` in `mtg_engine/export/snapshots.py` — add `self._listeners: list[Callable[[Snapshot], None]] = []`, `register_listener(fn)`, `unregister_listener(fn)`, and `_notify_finalized(snap)` (same pattern as `TranscriptRecorder`); call `_notify_finalized(snap)` at the end of `finalize_snapshot()` after appending to `_snapshots`
- [X] T005 Create `mtg_engine/persistence/game_persister.py` — implement `MongoGamePersister` with: `__init__(game_id, collection)`; `register_on_store(store: GameExportStore)` registers self as listener on `store.transcript`, `store.snapshots`, `store.debug_log`, and `store.rules_qa`; `init_game_document(player_1_name, player_1_type, player_2_name, player_2_type, format)` does `insert_one` (upsert by `_id=game_id`) with metadata + empty arrays + `is_complete: False`; `_on_transcript_entry(entry)` fires `asyncio.create_task(_push_transcript(entry))`; if `entry.event_type == "game_end"` also schedules `_finalize_game()`; `_on_snapshot_finalized(snap)` fires `asyncio.create_task(_push_snapshot(snap))`; `_on_debug_entry(entry)` fires `asyncio.create_task(_push_debug_entry(entry))` only when `entry.is_complete` is True; `_on_rules_qa_entry(entry)` fires `asyncio.create_task(_push_rules_qa(entry))`; `_finalize_game()` does `update_one($set: {is_complete: True, completed_at: utcnow()})` — outcome is fetched from in-memory `GameManager` inside this coroutine; `update_debug_entry(entry)` does `update_one` with `arrayFilters` targeting `entry_id` to `$set` `player_annotation` and `player_rating_override`; all async write helpers catch exceptions and log at WARNING level without re-raising; `_finalized` bool flag guards against duplicate finalization
- [X] T006 Add `persister: MongoGamePersister | None = None` attribute to `GameExportStore` in `mtg_engine/export/store.py` — in `get_export_store()`, after creating the store, if `is_configured()` is True, create `MongoGamePersister(game_id, get_games_collection())` and assign to `store.persister` (but do NOT call `register_on_store` here — that happens after player types are known)
- [X] T007 Add `player_1_type: str = "ai"` and `player_2_type: str = "ai"` optional params to `GameManager.create_game()` in `mtg_engine/api/game_manager.py` — after the export store is retrieved and the transcript recorder is set up, if `store.persister` is not None, call `store.persister.register_on_store(store)` then `store.persister.init_game_document(player1_name, player_1_type, player2_name, player_2_type, format)` via `asyncio.create_task()`; `has_human_player` is set to `True` in the document if either type is `"human"`

**Checkpoint**: MongoDB client ready, persister built, recorder hooks in place, game creation wires the persister — US1, US2, and US3 work can begin

---

## Phase 3: User Story 1 — Live Game Data Capture (Priority: P1) 🎯 MVP

**Goal**: All game events are persisted to MongoDB automatically as they occur during any game, without any user interaction.

**Independent Test**: Start a game (human-vs-AI or AI-vs-AI), play several turns. Query MongoDB directly (`db.games.findOne({game_id: "..."})`) and confirm transcript entries are present, `is_complete: False` during play, `is_complete: True` and `outcome` populated after game ends.

- [X] T008 [P] [US1] Update `mtg_engine/api/routers/human_game.py` — in the endpoint that calls `GameManager.create_game()`, identify which player is the human (from request body or route parameter) and pass the correct `player_1_type`/`player_2_type` args (e.g., if human is player 2: `player_2_type="human"`); read the existing router to determine the exact call site and player ordering before editing
- [X] T009 [P] [US1] Update `mtg_engine/api/routers/debug.py` — in `annotate_debug_entry()` after `recorder.annotate_entry()` succeeds, call `get_export_store(game_id).persister.update_debug_entry(updated)` if persister is not None; same in `rerate_debug_entry()` after `recorder.rerate_entry()` succeeds

**Checkpoint**: User Story 1 complete — query MongoDB during/after any game to see live-persisted data

---

## Phase 4: User Story 2 — Training Data Export & Query (Priority: P2)

**Goal**: Training pipelines can query completed game records via REST API without downloading files.

**Independent Test**: After completing several games, call `GET /games/records?is_complete=true&has_human_player=true` and verify returned records contain full transcript and debug entries. Call `GET /games/records/{game_id}` for a specific game and verify full record including snapshots.

- [X] T010 [US2] Create `mtg_engine/api/routers/game_records.py` — `GET /games/records` accepts query params `format` (optional), `has_human_player` (optional bool), `is_complete` (optional bool, default True), `from_dt` (optional ISO datetime, aliased to `from`), `to_dt` (optional ISO datetime, aliased to `to`), `limit` (int 1–1000, default 100), `fields` (optional comma-separated field projection); builds MongoDB filter dict from params; does `find()` with projection (default excludes `snapshots` for bandwidth; `fields=snapshots` adds them back); returns 503 with `{"error": "MongoDB not configured"}` if `not is_configured()`; `GET /games/records/{game_id}` returns the full document by `_id` or 404; strips MongoDB `_id` from responses
- [X] T011 [US2] Register `game_records` router in `mtg_engine/api/main.py` — import and `app.include_router(game_records_router.router)` with no prefix (routes defined as `/games/records` and `/games/records/{game_id}` in the router)

**Checkpoint**: User Story 2 complete — training pipelines can query persisted game data via API

---

## Phase 5: User Story 3 — Backward-Compatible File Export (Priority: P3)

**Goal**: Existing `GET /export/{game_id}/game-log` download works unchanged; health endpoint reports MongoDB status.

**Independent Test**: Complete a game, download the game log via `GET /export/{game_id}/game-log`, verify the plain-text format is identical to pre-feature output. Hit `GET /health` and verify it includes a `mongodb` field.

- [X] T012 [P] [US3] Update `export_game_log()` in `mtg_engine/api/routers/export.py` — if `is_configured()` and the game record exists in MongoDB (`is_complete: True`), load `transcript`, `snapshots`, and `debug_entries` arrays from the MongoDB document and pass to `build_game_log()`; otherwise fall back to existing in-memory store logic; no change to response format or media type
- [X] T013 [P] [US3] Extend `GET /health` in `mtg_engine/api/main.py` to be an async endpoint; if `is_configured()`, attempt a `ping` command on the client and return `"mongodb": "connected"` on success or `"mongodb": "error"` on exception; if not configured, return `"mongodb": "not_configured"`; health always returns 200

**Checkpoint**: User Story 3 complete — existing download workflow unaffected; health check reports MongoDB status

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T014 Add MongoDB index creation at app startup in `mtg_engine/api/main.py` — use FastAPI `lifespan` context manager (or `@app.on_event("startup")` if lifespan not already in use); if `is_configured()`, create indexes: `[("created_at", -1)]`, `[("is_complete", 1), ("created_at", -1)]`, `[("has_human_player", 1), ("is_complete", 1), ("created_at", -1)]`, `[("format", 1), ("is_complete", 1), ("created_at", -1)]`; use `create_index(..., background=True)` so startup is non-blocking
- [X] T015 [P] Run `python -m pytest tests/ -v` from project root to confirm no regressions from new persistence module and modified files
- [X] T016 [P] Verify engine starts cleanly without `MONGODB_URL` set — `uvicorn mtg_engine.api.main:app` must start without errors and `GET /health` must return `{"status": "ok", "mongodb": "not_configured"}`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (T001 must complete before motor can be imported); tasks T003–T007 are sequential within the phase (each depends on the previous)
- **Phase 3 (US1)**: Depends on Phase 2 complete — T008 and T009 are parallel (different files)
- **Phase 4 (US2)**: Depends on Phase 2 complete — can run in parallel with Phase 3; T011 depends on T010
- **Phase 5 (US3)**: Depends on Phase 2 complete — T012 and T013 are parallel; T013 may need T014 context but can be written independently
- **Phase 6 (Polish)**: Depends on all desired stories being complete

### Task Sequencing Within Phase 2

T003 → T004 → T005 → T006 → T007 (each depends on the previous)

- T003 must exist before T005 imports it
- T004 must add `register_listener` before T005 calls it
- T005 must exist before T006 instantiates it
- T006 must set `store.persister` before T007 calls methods on it

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 (the full persister + recorder hooks are ready)
- **US2 (P2)**: Depends on Phase 2 (needs `is_configured()` and collection access); independent of US1
- **US3 (P3)**: Depends on Phase 2 (needs `is_configured()`); independent of US1 and US2

---

## Parallel Execution Examples

### Phase 3 (US1) — after Phase 2 complete

```
T008 — human_game.py player type params   (parallel)
T009 — debug.py annotate/rerate persist   (parallel)
```

### Phase 4 (US2) — after Phase 2 complete, can overlap with Phase 3

```
T010 — game_records.py query router       (sequential: T010 then T011)
T011 — main.py router registration
```

### Phase 5 (US3) — after Phase 2 complete

```
T012 — export.py MongoDB-aware game-log   (parallel)
T013 — main.py health endpoint extension  (parallel)
```

### Phase 6 (Polish) — after all stories complete

```
T014 — startup index creation in main.py  (sequential first — others depend on it being written)
T015 — pytest regression run              (parallel with T016)
T016 — no-mongo startup verification      (parallel with T015)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: T001, T002
2. Complete Phase 2: T003 → T004 → T005 → T006 → T007
3. Complete Phase 3 (US1): T008 + T009 (parallel)
4. **STOP and VALIDATE**: Start engine with `MONGODB_URL` set, play a game, query MongoDB directly — confirm events appear live
5. Training data capture is live

### Incremental Delivery

1. Phase 1 + 2 → persister wired into all recorders
2. Phase 3 (US1) → live persistence working (MVP — training data flows automatically)
3. Phase 4 (US2) → query API online (training pipelines can read via REST)
4. Phase 5 (US3) → health check + file export compatibility confirmed
5. Phase 6 → indexes created at startup, regression tests pass

---

## Notes

- T003–T007 within Phase 2 are strictly sequential — do not parallelize them
- T008 and T009 are safe to parallelize — they touch `human_game.py` and `debug.py` respectively
- `motor` writes are always `asyncio.create_task()` — never `await` inside sync listener callbacks
- The `_finalized` flag on `MongoGamePersister` prevents duplicate `$set` on game completion if `game_end` is received multiple times
- T012 reads from MongoDB only for completed games (`is_complete: True`); in-progress game logs always use in-memory data
- All MongoDB writes use `upsert=True` so a failed `init_game_document` does not corrupt subsequent pushes

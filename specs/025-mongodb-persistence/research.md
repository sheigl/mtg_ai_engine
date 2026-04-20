# Research: MongoDB Game Data Persistence (Feature 025)

## Decision 1: MongoDB Driver — motor (async) vs pymongo (sync)

**Decision**: Use `motor` (the official async MongoDB driver) via `AsyncIOMotorClient`.

**Rationale**: The game engine runs on FastAPI with asyncio. `motor` integrates natively with asyncio, enabling non-blocking writes that do not stall the game loop or API request handling. Sync `pymongo` calls on the asyncio thread would block the event loop, violating FastAPI's async model.

**Alternatives considered**:
- `pymongo` in a thread pool — possible but requires `asyncio.to_thread()` wrapper on every write; adds boilerplate and latency overhead.
- `beanie` (ODM on top of motor) — adds a full ORM abstraction. Unnecessary for our use case where documents map directly to existing Pydantic models.

**Implementation note**: `motor` is the only new dependency. Pin version: `motor>=3.3.0`.

---

## Decision 2: MongoDB Document Schema — One Document Per Game

**Decision**: One document per game in a `games` collection, using the `game_id` as the MongoDB `_id`. Arrays of sub-documents store transcript entries, snapshots, and debug entries.

**Rationale**:
- All training data for a game is naturally accessed together. A single-document model means a training pipeline fetches one game with one query — no joins.
- MongoDB's `$push` operator allows atomic append of new events without rewriting the full document.
- Array sizes for a typical MTG game are bounded: ~200–500 transcript entries, ~200–400 snapshots, ~5–50 debug entries. Well within MongoDB's 16MB document limit.

**Schema**:
```json
{
  "_id": "<game_id>",
  "game_id": "<game_id>",
  "format": "standard|commander",
  "player_1": { "name": "...", "type": "human|ai" },
  "player_2": { "name": "...", "type": "human|ai" },
  "has_human_player": true,
  "created_at": "<ISO timestamp>",
  "completed_at": null,
  "is_complete": false,
  "outcome": null,
  "transcript": [],
  "snapshots": [],
  "debug_entries": [],
  "rules_qa": []
}
```

**Alternatives considered**:
- Separate collections per data type (transcripts, snapshots, debug_entries) — complicates training queries (requires multi-collection aggregation) and removes the self-contained training record property.
- One document per event (event-sourced) — maximizes write granularity but requires aggregation to reconstruct a game, adding pipeline complexity.

---

## Decision 3: Write Strategy — Async Fire-and-Forget via Listener Pattern

**Decision**: Register a `MongoGamePersister` as a listener on each recorder (`TranscriptRecorder`, `SnapshotRecorder`, `DebugLogRecorder`, `RulesQARecorder`). On each listener callback, fire an async `update_one` with `$push` to append the new record to the appropriate array. Use `asyncio.create_task()` to schedule the write without blocking the caller.

**Rationale**:
- All four recorders already have a listener registration pattern. Adding MongoDB persistence requires zero changes to the engine or game loop — only additive hook registration.
- `asyncio.create_task()` ensures writes are non-blocking; the game loop never waits for MongoDB.
- Errors are caught and logged per-write; a MongoDB failure silently skips the write without interrupting gameplay.

**Listener callbacks by recorder**:
- `TranscriptRecorder` → `$push` new TranscriptEntry on every `_notify_listeners()` call
- `SnapshotRecorder` → listener added to `finalize_snapshot()`; `$push` when snapshot is finalized (has `action_taken` set). Pending (unfinalized) snapshots are not yet pushed.
- `DebugLogRecorder` → `$push` only when `is_complete=True` on a patch; prior streaming chunks are not persisted mid-stream (the final entry is what matters for training).
- `RulesQARecorder` → `$push` on each new entry.

**Note for SnapshotRecorder**: The existing `SnapshotRecorder` has no listener mechanism. A lightweight listener list will be added (same pattern as `TranscriptRecorder`) and fired from `finalize_snapshot()`.

**Alternatives considered**:
- Background polling thread that periodically reads in-memory state — adds complexity and race conditions; does not guarantee sub-2-second write latency.
- Direct write inside recorder methods — couples persistence to recording logic; makes testing harder and violates SRP.

---

## Decision 4: Graceful Degradation — Optional MongoDB

**Decision**: MongoDB is optional. If `MONGODB_URL` environment variable is not set, persistence is silently skipped. The `MongoGamePersister` is only created and registered when MongoDB is configured. All existing gameplay and export functionality continues unchanged.

**Rationale**:
- The existing in-memory system works well for development and testing. Requiring MongoDB for all environments would break CI and local dev workflows.
- Training teams can opt into persistence by setting the environment variable; other users are unaffected.

**Reconnection**: `motor` has built-in connection pooling and automatic reconnection. If the server temporarily loses connection, pending writes fail silently (logged at WARNING level) and the game continues. No retry queue is implemented in v1.

---

## Decision 5: Game Record Initialization — On Game Create

**Decision**: When a new game is created in `GameManager.create_game()`, if MongoDB is configured, insert the initial game document (with empty arrays and metadata). All subsequent writes use `update_one` with `upsert=True` so that a missing initial document does not cause write failures.

**Rationale**: Inserting upfront establishes the game record immediately. The `upsert=True` guard handles the edge case where the initial insert failed but subsequent pushes arrive.

---

## Decision 6: Query Interface — New REST Endpoint + Direct Collection Access

**Decision**: Add `GET /games/records` endpoint with query parameters for training pipelines running within the same infrastructure. Training scripts can also connect directly to MongoDB using the same `MONGODB_URL`. No additional query service is needed.

**Query parameters for `GET /games/records`**:
- `format`: filter by game format (`standard`, `commander`)
- `has_human_player`: filter human-vs-AI games (`true`/`false`)
- `is_complete`: filter completed games (`true`/`false`)
- `from`: ISO timestamp lower bound on `created_at`
- `to`: ISO timestamp upper bound on `created_at`
- `limit`: max records (default 100, max 1000)
- `fields`: comma-separated list of top-level fields to include (e.g., `outcome,transcript`); default returns all except `snapshots` (large)

**Indexes required**:
- `game_id` (unique, primary — this is `_id`)
- `created_at` (descending — most frequent sort key)
- `is_complete` + `created_at` (compound — most common training query pattern)
- `has_human_player` + `is_complete` + `created_at` (compound — human-vs-AI training filter)

---

## Decision 7: Game Completion — Persisting the Outcome

**Decision**: When a game ends (detected via `record_game_end` in TranscriptRecorder), the `MongoGamePersister` calls a `finalize_game()` method that sets `is_complete: true`, `completed_at: <timestamp>`, and `outcome: <GameOutcome dict>` using `$set` on the game document.

**Rationale**: The outcome is not a push — it's a single set operation at game end. The `game_end` event type in the transcript is the signal for finalization.

**How game_end is detected**: The `MongoGamePersister` listens to `TranscriptRecorder`. When a `TranscriptEntry` with `event_type == "game_end"` is received, `finalize_game()` is scheduled. The `GameManager` already has access to the `GameState` at that point, which is used to build `GameOutcome`.

---

## Decision 8: Player Type Tracking

**Decision**: Add `player_type` metadata to the initial game document. The `GameManager.create_game()` does not currently track whether a player is human or AI. The human player name is stored in `localStorage` on the frontend and in the `human_game` router — we'll pass player type info when creating the game.

**Approach**: Extend `GameManager.create_game()` with optional `player_1_type: str = "ai"` and `player_2_type: str = "ai"` parameters (values: `"human"` or `"ai"`). The `human_game` router already knows which player is human and can pass this.

**Alternative**: Infer from game type at query time — but this requires cross-referencing which is error-prone.

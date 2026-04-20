# Research: Training Data Schema (026)

## 1. Decision Document Assembly — Arrival Order Problem

**Decision**: Upsert-based incremental assembly using `snapshot_id` as the `_id` of the `decisions` document.

**Rationale**: Three independent events contribute data to one decision document: (a) snapshot finalization (board_state, legal_actions, action_taken), (b) player DebugEntry completion (llm_reasoning), (c) observer DebugEntry completion (observer_evaluation). These arrive in undefined order and asynchronously. Upsert with `$set` on individual sub-fields — never a full document replace — handles any arrival order without coordination.

**Alternatives considered**:
- Buffer all three before writing: adds coordination complexity and a staging dict; still fails if game ends mid-buffer.
- Write snapshot first (guaranteed first event) then update sub-fields: identical to chosen approach but semantically clearer. Chosen approach is this, with `$setOnInsert` for initial frame fields and `$set` for incremental fields.

---

## 2. snapshot_id Propagation to AI Client

**Decision**: Return `snapshot_id` from `GET /game/{game_id}/legal-actions` response. AI client passes it in the debug entry body. `DebugEntry` model gains `snapshot_id: str | None = None`.

**Rationale**: The snapshot_id is generated inside the engine at `record_snapshot()` time. The AI client is a separate process. The only clean propagation path is the legal-actions HTTP response → client stores it → client includes it in the debug entry POST.

**Alternatives considered**:
- Generate snapshot_id in the AI client: snapshot and debug entry would use different IDs — breaks correlation.
- Store snapshot_id in a server-side session keyed by player: fragile with concurrent games and requires extra API call.

---

## 3. Observer Entry Linkage

**Decision**: Observer `DebugEntry` gains `related_entry_id: str | None` pointing to the player's `entry_id`. The game loop passes the player's `_debug_entry_id` when creating the observer entry. The persister uses `snapshot_id` (not `related_entry_id`) as the primary correlation key for the `decisions` document; `related_entry_id` is stored on the entry for downstream analysis.

**Rationale**: The `decisions` document groups by `snapshot_id`. Observer entries must also carry `snapshot_id` (same as the player entry for the same priority grant) so the persister can upsert into the same decision document. `related_entry_id` is additional metadata for tracing.

**How**: The game loop already has access to `_debug_entry_id` when calling `_observe_action()`. Pass it as `related_entry_id`; also pass the current `snapshot_id` received from the legal-actions response.

---

## 4. Rules Q&A Linkage to Decision

**Decision**: `QAPair` gains `decision_id: str | None = None`. The `GameExportStore` tracks `current_snapshot_id` (updated every time `record_snapshot()` is called). When `RulesQARecorder.on_sba()` (or other triggers) fires, it accepts an optional `decision_id` kwarg — callers that have the current snapshot_id pass it in.

**Rationale**: Rules Q&A events fire during action resolution (inside the engine, not from the AI client). The store has the current snapshot_id available. Passing it through the existing call chain is minimal-invasive.

**Alternatives considered**:
- Store snapshot_id on the recorder: introduces statefulness into a formerly stateless component. Acceptable but slightly less clean.
- Lookup by timestamp: fragile, not reliable under load.

---

## 5. sequence_number Strategy

**Decision**: The persister maintains a per-game `_sequence_counter: int` that increments on each `_on_snapshot_finalized` call. The counter is set when the decision document is initially created (via `$setOnInsert`).

**Rationale**: The spec requires gapless ordered sequence for each game. The persister is the single writer for a given game_id so a simple integer counter is safe without atomic coordination.

---

## 6. Games Collection — Metadata Only

**Decision**: The `games` document stores only scalar metadata. Arrays (`transcript`, `snapshots`, `debug_entries`, `rules_qa`) are removed entirely. Outcome is still embedded since it is a single sub-document.

**Current state**: `game_persister.py` currently `$push`es to embedded arrays. These array push handlers are deleted and replaced with writes to the separate collections.

**Transcript and rules_qa collections**: Each entry becomes an independent document with `game_id` + `sequence_number` (for transcript) or `game_id` + `decision_id` (for rules_qa). Indexes support filtering by game.

---

## 7. game_records API Router Redesign

**Decision**: Add new endpoint `GET /games/records/{game_id}/decisions` that queries the `decisions` collection sorted by `sequence_number`. Update existing `GET /games/records` to project from the `games` collection (metadata only — much smaller). Remove references to embedded arrays from existing endpoints.

**Export router**: `export.py`'s `game-log` endpoint currently reads embedded arrays from the `games` document. After the redesign, it should fall back to in-memory store (already the fallback path) since the game-log is typically called on a live or recently-completed game.

---

## 8. MongoDB Collection Names

| Collection | Description |
|-----------|-------------|
| `games` | One document per game, metadata only |
| `decisions` | One document per priority grant (training unit) |
| `rules_qa` | One document per Q&A pair |
| `transcript` | One document per transcript event |

Collection names are stored as constants in `mongo_client.py`. The database name remains `mtg_training` (from URL path) or `MONGODB_DATABASE` env var.

---

## 9. Annotation / Re-rate Updates (FR-013)

**Decision**: `annotate_debug_entry` and `rerate_debug_entry` endpoints in `debug.py` currently update the embedded array in `games`. After redesign, they must update `decisions.llm_reasoning.player_annotation` and `decisions.llm_reasoning.player_rating_override` using the entry's `snapshot_id` to locate the document.

**How**: `DebugEntry` now has `snapshot_id`. The persister's `update_debug_entry(entry)` method uses `snapshot_id` to find the decisions document and updates the `llm_reasoning` sub-document fields.

---

## 10. Indexes Required (FR-008)

```javascript
// Primary access pattern: enumerate decisions for a game in order
db.decisions.createIndex({ game_id: 1, sequence_number: 1 })

// Per-player filtering for training set construction  
db.decisions.createIndex({ game_id: 1, active_player: 1 })

// Outcome filtering across all games
db.decisions.createIndex({ "outcome_context.active_player_won": 1 })

// Observer quality filtering
db.decisions.createIndex({ "observer_evaluation.rating": 1 })

// Rules Q&A by game
db.rules_qa.createIndex({ game_id: 1, decision_id: 1 })

// Transcript replay
db.transcript.createIndex({ game_id: 1, sequence_number: 1 })
```

Indexes are created on application startup in `mongo_client.py` via `ensure_indexes()` called from `lifespan`.

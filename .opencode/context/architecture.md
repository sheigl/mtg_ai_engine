# Architecture Notes

## Deck Building AI (APP-02)

### Pipeline Architecture
The deck builder is a **stateless, pure-function pipeline** that takes a card pool and produces an optimized deck. No game state or database interaction — all logic is deterministic given the same inputs.

**Four-stage pipeline:**
1. **Filter**: Remove banned cards (format-specific), deduplicate for singleton formats, enforce Commander color identity constraints
2. **Score**: Composite score = `baseline_quality × strategy_multiplier × cmc_curve_bonus` using existing `estimate_card_quality()` from `card_eval.py`
3. **Select**: Sort by score descending, greedily pick top N respecting format constraints (deck size minimums, max copies per card), fill sideboard to 15 for non-Commander formats
4. **Validate**: Run FMT-01's `validate_deck()` on constructed deck entries

### Strategy System
Strategy weights table maps strategy → category → multiplier:
- **Aggro**: favors low-CMC creatures (1.5x), ramp (1.2x)
- **Control**: favors removal/counterspells (1.5x each), board wipes (1.4x), draw (1.3x)
- **Midrange**: balanced across categories, slight preference for mid-CMC creatures and draw
- **Combo**: favors high-CMC creatures (1.4x), draw (1.5x), ramp (1.3x)

CMC curve bonuses provide additional multipliers based on card CMC ranges per strategy.

### Determinism
Tie-breaking uses `random.Random(seed)` where seed is derived from SHA-256 hash of `(format + strategy + sorted card pool names)` or a user-provided seed. This ensures reproducible results for the same inputs.

### Format Handling
- **Singleton formats** (Legacy/Vintage/Commander/Brawl): max 1 copy per card name in both filter and selection stages; basic lands exempt from dedup (CR 905.2)
- **Non-singleton formats**: allow up to 4 copies, duplicates kept through filter stage for scoring
- **Pauper**: only common-rarity cards pass the filter stage (CR 109.5)
- **Commander**: color identity filtering during filter stage via `get_color_identity()` (derives from mana cost/oracle text); commanders locked into deck first during select stage; no sideboard
- **Brawl**: uses 60-card minimum (not 100), singleton rules apply, no sideboard

### Land Balancing
The selection phase reserves ~24% of deck slots for lands: it counts available land copies in the pool before greedy selection, then stops adding non-land cards once `greedy_target = deck_min - land_reserve` is reached. A post-greedy pass fills remaining slots with highest-scoring lands to ensure a playable mana base.

### API Layer
The router converts request Pydantic models (`CardPoolEntry`) to `Card` model objects, calls the engine pipeline, then converts results back to response models. The endpoint is mounted at `/ai/deck/build`.

## Card Search (APP-01)

### Query Strategy
The card search uses SQLite's built-in JSON functions to filter on the `data_json` blob column without requiring schema migrations. This keeps the cache format simple while enabling rich filtering.

**Two-query pagination pattern:**
1. `SELECT COUNT(*) FROM cards WHERE <filters>` — for accurate total count
2. `SELECT data_json FROM cards WHERE <filters> ORDER BY ... LIMIT ? OFFSET ?` — for page results

### Filter Implementation
All filters combine with AND logic using parameterized queries:
- Free-text (`q`): `LOWER(name) LIKE '%' || LOWER(?) || '%' OR LOWER(COALESCE(json_extract(data_json, '$.oracle_text'), '')) LIKE '%' || LOWER(?) || '%'`
- Type: `json_extract(data_json, '$.type_line') LIKE '%?%'`
- Colors (AND): For each color, `json_extract(data_json, '$.colors') LIKE '%"W"%'` — card must contain ALL specified colors
- CMC range: `CAST(json_extract(data_json, '$.cmc') AS REAL) >= ?` / `<= ?`
- Mana cost: exact match on `json_extract(data_json, '$.mana_cost') = ?`
- Keyword: case-insensitive quoted keyword in JSON array `LOWER(json_extract(data_json, '$.keywords')) LIKE '%"keyword"%'`
- Rarity: case-insensitive equality
- Set code: exact match

### API Layer
The router uses a singleton ScryfallClient (lazy-initialized) to share the SQLite connection across requests. The `_bad()` helper returns structured error responses with `error_code` for client-side handling.

FastAPI's built-in query parameter validation handles page/per_page bounds (`ge=1`, `le=100`). Invalid sort_by/sort_order values are caught by the engine layer and returned as HTTP 400.

## Game Replay (APP-03)

### Stateless Design
The replay system is entirely stateless — no server-side session tracking. Clients pass `from_event_seq` to indicate their current position, and the engine reconstructs board state from scratch for each request. This avoids session management complexity and scales trivially.

### Two-Tier Board State Reconstruction
Board state at any event position uses a hybrid approach:

1. **Snapshot anchors**: The existing `SnapshotRecorder` captures full serialized `GameState` objects at every priority grant. These are stored in the `GameExportStore.snapshots`. When reconstructing board state at seq N, find the nearest snapshot at or before seq N and deserialize it as the starting point.
2. **Incremental replay**: Apply transcript events between the snapshot anchor and target seq to update the reconstructed state. Only certain event types affect board state: `zone_change`, `life_change`, `damage`, `draw`, `cast`/`resolve`.

If no snapshot exists before the target (very early game), start from minimal initial state (20 life each, empty battlefield) and replay all events from seq 1.

### Data Flow
```
Client request → API router → get_export_store(game_id) → replay_engine functions → structured dict response
```

The engine module (`mtg_engine/export/replay_engine.py`) operates on `GameExportStore` objects (transcript + snapshots). It has no FastAPI dependencies — pure functions returning dicts. The API router wraps these with HTTP semantics, Pydantic models, and error handling.

### Endpoint Structure
- `GET /replay/{game_id}/info` — Metadata: total_events, turns, winner, loser, format
- `GET /replay/{game_id}/events?page=&per_page=` — Paginated transcript entries with has_next/has_prev
- `POST /replay/{game_id}/step` — Step forward/backward one event; returns event + reconstructed board state
- `GET /replay/{game_id}/timeline` — Condensed timeline grouped by turn/phase with event counts

### seq=0 Convention
Event sequence 0 means "before game starts." Forward from 0 yields event seq 1. Backward from 0 returns HTTP 400 (can't go before the beginning). Board state at seq 0 shows initial conditions (20 life, starting hands if snapshots exist).

### Lossy Reconstruction Limitations
Transcript events don't capture full state — they record what happened but not everything about the board. Hand card identities are unknown (only hand sizes are tracked), and stack contents are approximate. The API documents this limitation; snapshot anchors provide accurate states at priority grants, while incremental replay between snapshots provides reasonable approximations for intermediate steps.

## WebSocket Spectator (APP-04)

### Pub/Sub Architecture
The spectator system is a pure API-layer concern — no engine code modifications required beyond adding `unregister_listener()` to `TranscriptRecorder`. It uses the existing listener pattern from `TranscriptRecorder`, `SnapshotRecorder`, and `DebugLogRecorder` to tap into game events in real-time.

**Per-connection isolation**: Each WebSocket client gets its own `asyncio.Queue[dict]` (maxsize=256) and dedicated listener callback registered on the game's `TranscriptRecorder`. This isolates slow clients from fast ones — a backlogged queue for one spectator doesn't block event delivery to others.

### Data Flow
```
Game Event (cast, damage, phase_change, etc.)
    │
    ▼
TranscriptRecorder._entry(event_type, ...)
    │
    ▼
TranscriptRecorder._notify_listeners(entry)  ← iterates all registered listeners
    │
    ├──► Listener A → queue_A.put_nowait(event_dict) ─┐
    ├──► Listener B → queue_B.put_nowait(event_dict) ─┼─ Fan-out to all spectators
    └──► Listener C → queue_C.put_nowait(event_dict) ─┘
                            │
                            ▼
                  WebSocket send loop (per connection):
                    await asyncio.wait_for(queue.get(), timeout=1.0)
                    ws.send_json(msg)
```

### Sync→Async Bridging
Listener callbacks run synchronously (called from `_notify_listeners` which iterates the listeners list). They use `queue.put_nowait()` to push events into an async queue, decoupling the sync engine thread from the async WebSocket send loop. The main event loop drains the queue with `await asyncio.wait_for(queue.get(), timeout=1.0)`. Never call `websocket.send_json()` directly from a listener callback — it's async and would deadlock or require `asyncio.run_coroutine_threadsafe()`.

### Connection Lifecycle
1. **Validate**: Check game exists and is active via `GameManager.get(game_id)`. Reject with code 4004 if not found or completed (close before accept).
2. **Setup**: Create per-connection queue, register listener on TranscriptRecorder, add to `_spectators` registry as `(ws, queue, listener)` tuple.
3. **Initial state**: Send `{ type: "initial_state", data: <GameState.model_dump(mode="json")>, timestamp }` immediately after accept.
4. **Event loop**: Drain queue (1s timeout) → send JSON → check game-over via GameManager → repeat. On idle timeout, also check for game deletion or completion.
5. **Cleanup** (finally block): Unregister listener, remove from registry by queue identity, delete empty game entries.

### Registry Structure
Module-level `_spectators: dict[str, list[tuple[WebSocket, asyncio.Queue, Any]]]` in `mtg_engine/api/routers/spectate.py`. Uses list (not set) because dataclass instances aren't hashable. Cleanup uses identity-based matching (`s[1] is not queue`) to find and remove the correct tuple.

### Game-Over Detection
After each event and on idle timeout, the loop checks `GameManager.get(game_id).is_game_over`. If true, sends `{ type: "game_end", data: {winner, loser, reason}, timestamp }` and closes with code 1000. If game was deleted (KeyError), sends similar message with `reason: "game_deleted"`.

### No Heartbeat Task
Initial design included a background heartbeat task sending periodic ping/pong JSON messages. This was removed because `_heartbeat()` called `ws.receive_json()` competing with the main event loop for incoming messages, causing deadlocks in TestClient scenarios. The simplified single-receive-path approach is more reliable and sufficient for current use cases.

### Code Review Fixes
- **Game-over detection** (`_check_game_over_and_notify`): replaced dead function with real implementation — checks `is_game_over`, sends game_end notification, closes connection. Prevents orphaned connections after game ends.
- **Exception handling**: added `(WebSocketDisconnect, OSError, RuntimeError)` around send operations to prevent orphaned listeners on broken pipes.
- **Typed listeners**: replaced `Any` with `ListenerType = Callable[[TranscriptEntry], None]`.
- **Logging**: added `logger.info("Spectator connected/disconnected: game=%s")` lifecycle logging.
- **Constants**: defined `_SPECTATOR_QUEUE_MAX = 256` and `_IDLE_CHECK_INTERVAL_S = 1.0`.

### Endpoint
- `WebSocket /ws/game/{game_id}` — Real-time spectator feed. Read-only; no game actions accepted via this endpoint. Mounted in `main.py` alongside existing REST routers.

## Test Results
- All 16 spectate tests pass, all 2553 regression tests pass (3 skipped, 13 xfailed), 0 regressions

## Draft / Sealed Simulation (APP-05)

### Session Architecture
The draft system uses an in-memory session store (`_draft_sessions: dict[str, DraftSession]`) that mirrors the `GameManager` singleton pattern but is scoped to draft operations only. Each session tracks player state, pack distribution, pick order, and results independently of any live game state.

**Session lifecycle:**
1. **PICKING**: Active picks in progress. Human players submit picks via API; bot players auto-pick using scoring logic.
2. **BUILDING**: All picks complete. APP-02's `build_deck()` is called for each player's drafted pool.
3. **COMPLETE**: Results ready. Clients can retrieve final decklists, sideboards, and draft statistics.

### Pack Generation Algorithm
Packs are generated from Scryfall set data via the SQLite cache:

1. Fetch all cards with matching `set_code` using `ScryfallClient.search_cards(set_code=..., per_page=100)`
2. If fewer than 50 cards found (set not loaded), fall back to randomized format-legal pool from entire cache
3. Apply rarity-weighted sampling: common ~80%, uncommon ~15%, rare ~4.5%, mythic ~0.5%
4. Deduplicate by name within each pack (standard limited rules)
5. Return exactly 15 cards per pack

### Draft Pick Mechanics
**Standard Limited passing:**
- Odd rounds (1, 3, 5...): Pass left — pick order is `[0, 1, 2, ..., N-1]`
- Even rounds (2, 4, 6...): Pass right — pick order is `[N-1, N-2, ..., 1, 0]`

Each round, every player picks exactly 1 card from the pack currently in front of them. After all players pick, packs rotate according to passing direction for the next round.

**Human-in-the-loop:** If `human_player_name` is provided during session creation, that player's turns wait for an API call (`POST /ai/draft/{id}/pick`). Bot players auto-pick immediately when their turn arrives.

### Bot Auto-Pick Scoring
Bots score each available card using a composite of:
1. **Base quality**: `estimate_card_quality()` from `card_eval.py` (0-10 range)
2. **Strategy multiplier**: From `STRATEGY_WEIGHTS` in `deck_builder.py`, applied based on player's strategy preference
3. **Color synergy bonus**: +1.0 per matching color in already-drafted cards' color identity
4. **CMC curve fit**: Bonus if card's CMC fills a gap in the drafted pool's curve (e.g., early game needs low-CMC, late game needs high-CMC)

Bot selects the highest-scoring card from the available pack. Tie-breaking uses `random.Random(seed)` for determinism.

### Sealed Mode
Sealed mode is simpler — no pick orchestration needed:
1. Generate one 15-card pack per player (same algorithm as draft packs)
2. Immediately call APP-02's `build_deck()` for each player's pool
3. Return results with pools, decks, and sideboards

### Data Flow
```
Client request → API router → DraftSession engine functions → structured dict response
```

The engine module (`mtg_engine/ai/draft.py`) operates on `DraftSession` objects (dataclasses). It has no FastAPI dependencies — pure functions returning session state. The API router wraps these with HTTP semantics, Pydantic models, and error handling.

### Endpoint Structure
- `POST /ai/draft/start` — Create draft session; returns session_id and initial state
- `GET /ai/draft/{id}/state` — Current round, pick order, available cards, player draft states
- `POST /ai/draft/{id}/pick` — Human-in-the-loop pick; validates card is in available pack
- `GET /ai/draft/{id}/results` — Final results after all picks done (decks, sideboards, stats)
- `POST /ai/sealed/start` — Create sealed session; returns immediate pools + decks

### Memory Management
Sessions are stored in a module-level dict with no TTL-based cleanup for MVP. Process restart clears all sessions. Future enhancement: add `_cleanup_expired_sessions()` helper that discards sessions older than 1 hour, called periodically or on new session creation.

### Integration Points
- **APP-02 Deck Builder**: Post-draft deck construction delegates to `build_deck(card_pool, format_name, strategy, seed)` — no duplication of Filter→Score→Select→Validate pipeline
- **Scryfall Client**: Pack generation uses `search_cards(set_code=...)` from SQLite cache; falls back to format-legal pool if set not loaded
- **Card Evaluation**: Bot auto-pick reuses `estimate_card_quality()` and `STRATEGY_WEIGHTS` from existing modules

## Player Stats / ELO (APP-06)

### Persistence Architecture
Player stats are stored in MongoDB collection `player_stats` with two indexes: unique on `player_name` and descending on `elo`. This is the first feature to require MongoDB — all other features work without it.

**Data model:**
```json
{
  "player_name": "Alice",
  "elo": 1250,
  "wins": 6,
  "losses": 4,
  "formats": {
    "standard": {"wins": 3, "losses": 2},
    "commander": {"wins": 3, "losses": 2}
  },
  "matchups": {
    "Bob": {"opponent": "Bob", "wins": 4, "losses": 1},
    "Charlie": {"opponent": "Charlie", "wins": 2, "losses": 3}
  },
  "updated_at": "2026-07-15T..."
}
```

### ELO Calculation
Standard ELO formula with K=32:
```python
expected = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 400))
new_elo = current_elo + K * (actual_score - expected)
# actual_score: 1.0 for win, 0.0 for loss
```

### Game Completion Hook
Stats are updated automatically when a game is deleted via `DELETE /game/{game_id}`. The flow:

1. **Sync handler** (`delete_game()` in `game.py`): Removes game from GameManager, extracts winner/loser/format from final GameState
2. **Async bridge**: Calls `asyncio.run_coroutine_threadsafe(update_stats_for_game_completion(...), loop)` to run MongoDB operations on the event loop
3. **Stats update** (`update_stats_for_game_completion()` in `player_stats.py`): Fetches both players' stats, calls pure `update_player_stats()`, writes back via MongoDB upserts

If MongoDB is not configured, stats updates are silently skipped (logged at debug level). If either player has no existing profile, an auto-created profile with elo=1200 is used.

### API Endpoints
- **`GET /stats/player/{player_name}`** — Returns full player stats including win_rate and total_games computed fields
- **`POST /stats/player/{player_name}`** — Idempotent profile creation; returns existing stats if already present, creates with elo=1200 if not
- **`GET /stats/player/{player_name}/matchups`** — Per-opponent breakdown sorted by most games played
- **`GET /stats/leaderboard?format=&limit=10`** — Top players by ELO descending; optional format filter uses aggregation pipeline to project per-format records

### Error Handling
- MongoDB not configured → HTTP 503 with `{ "error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED" }`
- Player not found (GET) → HTTP 404
- All other errors → HTTP 500 with error message

### Pure Transform Pattern
`update_player_stats()` in `engine/stats.py` follows the project convention of pure transforms: it takes a `PlayerStats` object and returns a new one via `model_copy(update={...})`. The original is never mutated. This allows safe testing and potential future use in non-MongoDB contexts (e.g., in-memory stats for local play).


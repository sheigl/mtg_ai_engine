# Design: APP-04 WebSocket Spectator Endpoint

## Overview
A `WebSocket /ws/game/{game_id}` endpoint that broadcasts real-time game state updates to connected spectator clients. Taps into the existing `TranscriptRecorder` listener system — no engine code modifications required beyond adding `unregister_listener()` for cleanup.

## User Story Reference
`.opencode/discovery/story-app04-spectate-websocket.md` — "As a spectator or frontend application, I want to receive real-time game state updates via WebSocket so that I can display live game progress without polling."

---

## Architecture Decisions

### Decision 1: Pub/Sub via TranscriptRecorder Listeners
**Decision**: Each connected WebSocket client registers its own listener callback on the game's `TranscriptRecorder`. When a transcript event fires, all registered listeners are notified and the event is pushed to each client's outgoing queue. This avoids modifying any engine code — the spectator system is purely an API-layer concern.

**Trade-offs considered**:
- **Per-game single listener with fan-out**: One listener per game that broadcasts to all connected clients via a shared queue. Simpler but harder to clean up individual connections (can't unregister a partial listener). Also creates contention if one slow client blocks the queue.
- **Polling TranscriptRecorder in WebSocket loop**: Would require checking for new entries on every iteration, adding latency and CPU overhead. Rejected — listener callback is instant and zero-overhead when no events fire.

### Decision 2: Per-Connection asyncio.Queue (Not Shared Queue)
**Decision**: Each WebSocket connection gets its own `asyncio.Queue`. The per-connection listener pushes to that specific queue. This isolates slow clients from fast ones and makes cleanup trivial — just close the websocket and drop the queue.

**Trade-offs considered**:
- **Shared queue per game**: One queue, multiple consumers. Requires careful coordination (e.g., `asyncio.Queue.get()` only delivers to one consumer). Would need a fan-out dispatcher anyway. Per-connection queues are simpler.
- **Direct `websocket.send_text()` in listener callback**: The listener runs synchronously in the engine thread context. Calling an async `send_text()` from there would deadlock or require `asyncio.run_coroutine_threadsafe()`. Queues decouple the sync listener from the async send loop.

### Decision 3: SpectatorManager as Module-Level Singleton
**Decision**: A module-level `_spectators: dict[str, set[SpectatorConnection]]` in the new router file manages all active connections. `SpectatorConnection` is a lightweight dataclass holding the WebSocket, its queue, and the listener callback reference (needed for cleanup).

**Trade-offs considered**:
- **Class-based SpectatorManager**: Would be cleaner but adds an unnecessary abstraction layer for what's essentially a dict + helper methods. The SSE endpoint in `debug.py` uses inline logic successfully. Keeping it simple matches existing patterns.
- **GameManager integration**: Could add spectator tracking to GameManager, but that couples the core game manager to WebSocket concerns. Better to keep it isolated in the API router.

### Decision 4: Heartbeat via asyncio.Task per Connection
**Decision**: Each WebSocket connection spawns a background `asyncio.create_task(_heartbeat(ws))` that sends `{ type: "ping" }` every 30 seconds and tracks pong responses. If no pong arrives within 15 seconds, the task closes the websocket and triggers cleanup.

**Trade-offs considered**:
- **Single global heartbeat task**: Would iterate all connections periodically. More complex to implement correctly (must handle concurrent disconnects). Per-connection tasks are independent and self-cleaning.
- **WebSocket built-in ping/pong**: FastAPI's `websocket.send_bytes()` supports WebSocket-level ping frames, but the acceptance criteria specifically require `{ type: "ping" }` JSON messages for application-layer heartbeats that the frontend can handle explicitly.

### Decision 5: Initial State via GameState.model_dump()
**Decision**: On connect, send a `{ type: "initial_state", data: <GameState.model_dump()> }` message with the full serialized game state. This gives late-joining spectators a complete starting point without needing to replay the entire transcript.

**Trade-offs considered**:
- **Replay transcript on connect**: Would give event history but requires client-side reconstruction logic. Initial state is simpler and matches what REST `GET /game/{id}` already provides.
- **Partial state (board summary only)**: Smaller payload but loses context (stack, pending choices, etc.). Full state dump is consistent with existing API contract.

---

## Component Breakdown

### 1. SpectatorConnection (dataclass)
A lightweight container for each WebSocket connection's resources:

```python
@dataclass
class SpectatorConnection:
    ws: WebSocket
    queue: asyncio.Queue[dict]
    listener_fn: Callable[[TranscriptEntry], None]
    game_id: str
    pong_received_at: float = 0.0
```

### 2. Connection Registry (module-level)
```python
# Maps game_id -> set of SpectatorConnection objects
_spectators: dict[str, set[SpectatorConnection]] = {}
```

### 3. WebSocket Endpoint Handler (`ws_game_spectate`)
The main async endpoint function handling the full connection lifecycle:

1. **Validate game exists and is active** → HTTP 404 if not (via `WebSocket.close(code=4004)`)
2. **Create per-connection queue + listener callback** → register on TranscriptRecorder
3. **Send initial state** → `{ type: "initial_state", data: gs.model_dump() }`
4. **Spawn heartbeat task** → 30s ping interval, 15s pong timeout
5. **Event fan-out loop** → `await queue.get()` → `ws.send_text(json.dumps(event))` → check game-over after each event
6. **Disconnect cleanup** → unregister listener, remove from registry, cancel heartbeat task

### 4. Heartbeat Task (`_heartbeat`)
Background async task per connection:

```python
async def _heartbeat(conn: SpectatorConnection) -> None:
    while True:
        try:
            await asyncio.sleep(30)
            await conn.ws.send_text(json.dumps({"type": "ping"}))
            # Wait up to 15s for pong
            if time.monotonic() - conn.pong_received_at > 15:
                await conn.ws.close(code=1001)  # Going Away
                return
        except Exception:
            return  # Connection closed, exit task
```

The main event loop handles incoming `"pong"` messages by updating `conn.pong_received_at = time.monotonic()`.

---

## Data Flow

```
Game Event (e.g. cast, damage, phase_change)
        │
        ▼
TranscriptRecorder._entry("cast", ...)
        │
        ▼
TranscriptRecorder._notify_listeners(entry)
        │
        ├──► Listener A → queue_A.put_nowait(event_dict)  ─┐
        ├──► Listener B → queue_B.put_nowait(event_dict)  ─┼─ Fan-out to all spectators
        └──► Listener C → queue_C.put_nowait(event_dict)  ─┘
                                          │
                                          ▼
                              WebSocket send loop (per connection):
                                await queue.get()
                                ws.send_text(json.dumps(msg))
```

**Event message format**:
```json
{
  "type": "<event_type>",
  "data": { ... },
  "timestamp": 1700000000.123,
  "seq": 42,
  "turn": 5,
  "phase": "combat",
  "step": "declare_attackers"
}
```

**Initial state message format**:
```json
{
  "type": "initial_state",
  "data": { <GameState.model_dump()> }
}
```

**Game-end message format**:
```json
{
  "type": "game_end",
  "data": { "winner": "p1", "loser": "p2" },
  "timestamp": 1700000000.456
}
```

---

## Key Implementation Patterns

### Pattern 1: Listener Registration Per Connection (Not Per Game)
Each WebSocket connection registers its own listener callback on the TranscriptRecorder. The callback pushes to that connection's private queue. This enables precise cleanup when individual clients disconnect — we unregister only their specific listener, leaving other spectators unaffected.

**Reference**: The SSE endpoint in `mtg_engine/api/routers/debug.py` (lines 161-220) uses this exact pattern:
```python
queue: asyncio.Queue[DebugEntry] = asyncio.Queue()

def _listener(entry: DebugEntry) -> None:
    queue.put_nowait(entry)

recorder.register_listener(_listener)
# ... in finally block:
recorder.unregister_listener(_listener)
```

### Pattern 2: asyncio.Queue for Fan-out Buffering
The listener callback runs synchronously (called from `_notify_listeners` which iterates the listeners list). It uses `queue.put_nowait()` to push events into an async queue, decoupling the sync engine thread from the async WebSocket send loop. The main event loop drains the queue with `await queue.get()`.

**Why not direct send?**: `websocket.send_text()` is async and cannot be called from a synchronous callback without `asyncio.run_coroutine_threadsafe()`, which adds complexity and potential deadlocks. Queues are the standard pattern for sync→async bridging in FastAPI WebSocket handlers.

### Pattern 3: Game-Over Detection After Each Event
After receiving each event from the queue, check if the game is over by querying `GameManager.get(game_id).is_game_over`. If true, send the `game_end` message and close with code 1000 (Normal Closure). Also check during keepalive/heartbeat idle periods.

**Reference**: Same pattern in SSE endpoint (`debug.py` lines 198-216):
```python
try:
    gs = get_manager().get(game_id)
    if gs.is_game_over:
        yield f"event: game_over\ndata: {json.dumps({'game_id': game_id})}\n\n"
        break
except KeyError:
    # Game deleted — also treat as end
    break
```

### Pattern 4: Graceful Disconnect Cleanup (finally block)
The WebSocket handler uses a `try/finally` pattern to guarantee cleanup regardless of how the connection terminates (normal close, error, exception):

```python
async def ws_game_spectate(websocket: WebSocket, game_id: str):
    conn = None
    heartbeat_task = None
    try:
        # ... setup, send initial state, event loop ...
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        if conn:
            recorder.unregister_listener(conn.listener_fn)
            _spectators.get(game_id, set()).discard(conn)
```

---

## Critical Fix: Add `unregister_listener()` to TranscriptRecorder

The `TranscriptRecorder` class has `register_listener(fn)` but no corresponding `unregister_listener(fn)`. This is needed for cleanup when WebSocket connections close. The pattern already exists in sibling classes:

**SnapshotRecorder** (`mtg_engine/export/snapshots.py`, lines 37-39):
```python
def unregister_listener(self, fn: Callable[["Snapshot"], None]) -> None:
    try:
        self._listeners.remove(fn)
    except ValueError:
        pass
```

**DebugLogRecorder** (`mtg_engine/export/debug_log.py`, lines 23-26):
```python
def unregister_listener(self, fn: Callable[["DebugEntry"], None]) -> None:
    try:
        self._listeners.remove(fn)
    except ValueError:
        pass
```

The same pattern will be added to `TranscriptRecorder`:
```python
def unregister_listener(self, fn: Callable[["TranscriptEntry"], None]) -> None:
    """Remove a previously registered listener. No-op if not found."""
    try:
        self._listeners.remove(fn)
    except ValueError:
        pass
```

---

## Files to Create/Modify

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `mtg_engine/api/routers/spectate.py` | WebSocket spectator router | `_spectators` registry, `SpectatorConnection` dataclass, `ws_game_spectate()` endpoint handler, `_heartbeat()` task, listener registration/cleanup logic |
| `tests/api/test_spectate_websocket.py` | Test suite for WebSocket spectator | >=6 tests covering connect/initial state, event broadcasting, multiple connections, game-end notification, non-existent game rejection, disconnect cleanup |

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/export/transcript.py` | Add `unregister_listener()` method to `TranscriptRecorder` | Required for graceful WebSocket disconnect cleanup (pattern exists in SnapshotRecorder and DebugLogRecorder) |
| `mtg_engine/api/main.py` | Import and mount `spectate.router` | Wire new WebSocket endpoint into FastAPI app |

---

## API Contract

### Endpoint: `WebSocket /ws/game/{game_id}`

**Connection**: Standard WebSocket handshake. No authentication required (MVP — can be added later per story notes).

**Server → Client Messages**:
| Type | When Sent | Payload |
|------|-----------|---------|
| `initial_state` | Immediately after connection accepted | `{ type: "initial_state", data: <GameState.model_dump()> }` |
| `<event_type>` | On each transcript event (cast, resolve, damage, phase_change, etc.) | `{ type: "<event_type>", data: {...}, timestamp: float, seq: int, turn: int, phase: str, step: str }` |
| `ping` | Every 30 seconds | `{ type: "ping" }` |
| `game_end` | When game ends (detected after event or during idle) | `{ type: "game_end", data: { winner: str, loser: str }, timestamp: float }` |

**Client → Server Messages**:
| Type | Purpose | Response |
|------|---------|----------|
| `pong` | Reply to server ping (required for keepalive) | None — server tracks pong timestamp internally |

**Connection Closure**:
- **Code 1000** (Normal): Game ended — server sends `game_end` then closes
- **Code 1001** (Going Away): Heartbeat timeout — no pong within 15s of ping
- **Code 4004** (Custom): Invalid game — game not found or already completed at connect time

### Error Handling: Non-Existent Game
If the client connects to a non-existent or completed game, reject during WebSocket handshake:

```python
async def ws_game_spectate(websocket: WebSocket, game_id: str):
    # Validate before accepting connection
    try:
        gs = get_manager().get(game_id)
    except KeyError:
        await websocket.close(code=4004, reason="Game not found")
        return

    if gs.is_game_over:
        await websocket.close(code=4004, reason="Game already completed")
        return

    await websocket.accept()
    # ... proceed with spectator setup ...
```

This produces an HTTP 404-equivalent at the WebSocket layer (the handshake fails before `accept()`).

---

## Task Breakdown (Ordered by Dependency)

### Task 1: Add `unregister_listener()` to TranscriptRecorder
- **Files**: `mtg_engine/export/transcript.py`
- **Description**: Add `unregister_listener(fn)` method following the exact pattern from `SnapshotRecorder` and `DebugLogRecorder`. Uses `try/except ValueError` around `self._listeners.remove(fn)` for safe no-op on missing listeners.
- **Acceptance Criteria**:
  - Method signature: `def unregister_listener(self, fn: Callable[["TranscriptEntry"], None]) -> None`
  - Removes the listener from `_listeners` list if present
  - No-op (no exception) if listener was never registered or already removed
  - Existing tests still pass

### Task 2: Create WebSocket Spectator Router
- **Files**: `mtg_engine/api/routers/spectate.py` (new)
- **Description**: Implement the full WebSocket endpoint with connection lifecycle management. Includes `_spectators` registry, `SpectatorConnection` dataclass, event fan-out loop, heartbeat task, and cleanup logic. Follows the SSE pattern from `debug.py` adapted for WebSocket semantics.
- **Acceptance Criteria**:
  - Endpoint at `/ws/game/{game_id}` accepts WebSocket connections
  - Sends `{ type: "initial_state", data: ... }` immediately after accept
  - Broadcasts transcript events as JSON messages to all connected clients
  - Multiple spectators can connect simultaneously without interference
  - Read-only — no game actions accepted via WebSocket (incoming non-pong messages are ignored)
  - Game-end detection sends `{ type: "game_end", ... }` and closes with code 1000
  - Non-existent/completed games rejected before accept (code 4004)
  - Heartbeat: `{ type: "ping" }` every 30s; disconnect if no pong within 15s
  - Graceful cleanup on disconnect: unregister listener, remove from registry, cancel heartbeat task

### Task 3: Wire Router into FastAPI App
- **Files**: `mtg_engine/api/main.py`
- **Description**: Import and mount the new spectate router. WebSocket routers are mounted the same way as REST routers via `app.include_router()`.
- **Acceptance Criteria**:
  - Endpoint accessible at `/ws/game/{game_id}`
  - No conflicts with existing routes (prefix `/ws/` is unique)
  - Health check still works

### Task 4: Write Test Suite
- **Files**: `tests/api/test_spectate_websocket.py` (new)
- **Description**: Comprehensive test suite using FastAPI's `TestClient.websocket_connect()` for WebSocket testing. Tests cover all acceptance criteria including connection lifecycle, event broadcasting, multi-spectator support, game-end notification, error handling, and cleanup.
- **Acceptance Criteria**: >=6 tests covering:
  1. Connect and receive initial state
  2. Event broadcasting during gameplay (manually trigger transcript event)
  3. Multiple simultaneous connections all receive events
  4. Game-end notification with close code 1000
  5. Non-existent game rejection (WebSocket handshake fails)
  6. Disconnect cleanup (listener unregistered, registry cleaned)

---

## Data Models / Interfaces

### SpectatorConnection (dataclass in `spectate.py`)
```python
from dataclasses import dataclass, field
import time
import asyncio
from typing import Callable
from fastapi import WebSocket
from mtg_engine.export.transcript import TranscriptEntry

@dataclass
class SpectatorConnection:
    ws: WebSocket
    queue: asyncio.Queue[dict]
    listener_fn: Callable[[TranscriptEntry], None]
    game_id: str
    pong_received_at: float = field(default_factory=time.monotonic)
```

### TranscriptRecorder Addition (in `transcript.py`)
```python
def unregister_listener(self, fn: Callable[["TranscriptEntry"], None]) -> None:
    """Remove a previously registered listener. No-op if not found."""
    try:
        self._listeners.remove(fn)
    except ValueError:
        pass
```

---

## Testing Strategy

### Test Matrix (>=6 tests)

| # | Test Name | What It Verifies | Acceptance Criterion |
|---|-----------|-----------------|---------------------|
| 1 | `test_connect_sends_initial_state` | Connect to active game, first message is `{ type: "initial_state" }` with valid GameState data | Initial state on connect |
| 2 | `test_event_broadcasting_during_gameplay` | Manually record a transcript event via recorder, verify WebSocket client receives the event as JSON | Event broadcasting |
| 3 | `test_multiple_spectators_receive_events` | Two clients connect to same game; both receive the same broadcasted event independently | Multi-spectator support |
| 4 | `test_game_end_notification_and_close` | Mark game as over, verify client receives `{ type: "game_end" }` and connection closes with code 1000 | Game-end notification |
| 5 | `test_nonexistent_game_rejected` | Attempt to connect to non-existent game_id; WebSocket handshake fails (raises exception or returns error) | HTTP 404 for invalid games |
| 6 | `test_disconnect_cleanup_removes_listener` | Connect, verify listener registered; disconnect, verify listener unregistered and registry entry removed | Graceful cleanup |

### Test Patterns (following existing conventions from `test_api.py`)

```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store, get_export_store
from mtg_engine.models.game import GameState

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    """Clear all games and export stores before each test."""
    get_manager()._games.clear()
    get_manager()._recorders.clear()
    export_store.clear()
    # Clear spectator registry
    from mtg_engine.api.routers.spectate import _spectators
    _spectators.clear()
    yield
    get_manager()._games.clear()
    get_manager()._recorders.clear()
    export_store.clear()
    _spectators.clear()

def _create_game(seed: int = 1) -> str:
    """Create a game and return its ID."""
    resp = client.post("/game", json={
        "player1_name": "p1", "player2_name": "p2",
        "deck1": ["Forest"] * 60, "deck2": ["Forest"] * 60,
        "seed": seed,
    })
    assert resp.status_code == 200
    return resp.json()["data"]["game_id"]

def test_connect_sends_initial_state():
    """WebSocket connection receives initial game state on connect."""
    game_id = _create_game()
    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        assert "data" in data
        # Verify it contains GameState fields
        state = data["data"]
        assert state["game_id"] == game_id
        assert "players" in state

def test_event_broadcasting_during_gameplay():
    """Transcript events are broadcast to connected WebSocket clients."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        # Receive initial state first
        ws.receive_json()

        # Manually record a transcript event
        recorder.record_cast("p1", "Lightning Bolt", ["p2"], turn=1, phase="combat", step="declare_attackers")

        # Give async loop time to process
        import time; time.sleep(0.1)

        data = ws.receive_json()
        assert data["type"] == "cast"
        assert data["data"]["card_name"] == "Lightning Bolt"

def test_multiple_spectators_receive_events():
    """Multiple WebSocket clients all receive the same broadcasted events."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws1, \
         client.websocket_connect(f"/ws/game/{game_id}") as ws2:
        # Both receive initial state
        ws1.receive_json()
        ws2.receive_json()

        # Record an event
        recorder.record_damage("Lightning Bolt", "p2", 3, turn=1, phase="combat", step="declare_attackers")
        import time; time.sleep(0.1)

        # Both clients receive the damage event
        data1 = ws1.receive_json()
        data2 = ws2.receive_json()
        assert data1["type"] == "damage"
        assert data2["type"] == "damage"
        assert data1["data"]["amount"] == 3

def test_nonexistent_game_rejected():
    """Connecting to a non-existent game rejects the WebSocket handshake."""
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(Exception):  # TestClient raises on failed handshake
        with client.websocket_connect("/ws/game/nonexistent-id"):
            pass

def test_disconnect_cleanup_removes_listener():
    """When a spectator disconnects, their listener is unregistered."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript
    from mtg_engine.api.routers.spectate import _spectators

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        ws.receive_json()  # initial state
        assert game_id in _spectators
        assert len(_spectators[game_id]) == 1
        listener_fn = list(_spectators[game_id])[0].listener_fn
        assert listener_fn in recorder._listeners

    # After disconnect, listener should be unregistered
    assert listener_fn not in recorder._listeners
    assert game_id not in _spectators or len(_spectators.get(game_id, set())) == 0
```

### Heartbeat Testing Note
Heartbeat testing (30s ping / 15s pong timeout) is difficult to test with `TestClient` because it doesn't support real-time async operations well. The heartbeat logic should be tested via:
- **Unit test**: Mock the WebSocket and verify `_heartbeat()` sends pings at correct intervals and closes on timeout
- **Integration confidence**: The pattern mirrors the proven SSE keepalive in `debug.py`; the main difference is JSON ping/pong vs SSE comment-based keepalive

---

## Potential Risks

### 1. Listener callback runs synchronously — slow queue blocks engine
**Risk**: If `queue.put_nowait()` raises `asyncio.QueueFull` (if queue has a max size), the listener would throw and the event would be silently dropped (caught by `_notify_listeners` try/except). Even without a max size, a very large backlog could consume memory.
**Mitigation**: Use unbounded `asyncio.Queue()` (default). The synchronous callback only does `put_nowait()` which is O(1) and non-blocking even for unbounded queues. Memory pressure from backlogged events is acceptable — spectators reconnecting after being offline would need to catch up anyway.

### 2. Concurrent listener modification during iteration
**Risk**: `_notify_listeners` iterates `self._listeners`. If a disconnect happens concurrently and calls `unregister_listener()` (which does `list.remove()`), this could raise `RuntimeError: list modified during iteration`.
**Mitigation**: The SSE endpoint in `debug.py` has the same pattern and works because FastAPI's single-threaded event loop ensures that `_notify_listeners` and `unregister_listener` don't run concurrently. However, to be safe, iterate over a copy: `for fn in list(self._listeners):`.

### 3. TestClient WebSocket limitations
**Risk**: `TestClient.websocket_connect()` runs synchronously and doesn't fully simulate async behavior (timers, concurrent tasks). Heartbeat tests may not work as expected.
**Mitigation**: Focus integration tests on connection lifecycle, event broadcasting, and cleanup. Test heartbeat logic separately with mocked time or skip in CI (mark as `pytest.mark.skip(reason="requires real WebSocket server")`).

### 4. Game deleted while spectators connected
**Risk**: If `GameManager.delete(game_id)` is called while spectators are connected, the game-over check will raise `KeyError`. The event loop would crash if not handled.
**Mitigation**: Wrap all `get_manager().get(game_id)` calls in try/except KeyError and treat as game-end (send `game_end` message and close). Same pattern used in SSE endpoint (`debug.py` lines 203-205).

### 5. Memory leak from stale spectator entries
**Risk**: If cleanup fails (exception in finally block), `_spectators[game_id]` could accumulate dead connections over time.
**Mitigation**: The `finally` block uses `.discard()` which is safe even if the connection was already removed. Add a periodic cleanup task that removes entries with closed websockets (future enhancement). For MVP, rely on the finally block correctness.

---

## Handoff to Implementer

**Design Document**: `specs/038-gap-analysis/APP-04-design.md` (this file)
**User Story**: `.opencode/discovery/story-app04-spectate-websocket.md`
**Estimated Complexity**: Low — no new dependencies, straightforward pub/sub pattern, mirrors existing SSE endpoint in `debug.py`
**Key Files**:
1. `mtg_engine/api/routers/spectate.py` — New WebSocket router (main implementation)
2. `mtg_engine/export/transcript.py` — Add `unregister_listener()` (one-line fix)
3. `mtg_engine/api/main.py` — Mount new router (two lines)
4. `tests/api/test_spectate_websocket.py` — Test suite

**Start With**: Task 1 — Add `unregister_listener()` to TranscriptRecorder. This is a trivial one-method addition that unblocks all other tasks. Then proceed to Task 2 (the router).

**Acceptance Criteria** (from Discovery story):
- [ ] `WebSocket /ws/game/{game_id}` endpoint accepts connections and sends initial game state on connect
- [ ] On each game event, connected WebSocket clients receive a JSON message: `{ type: "<event_type>", data: { ... }, timestamp: float }`
- [ ] Multiple spectators can connect to the same game simultaneously without interfering with gameplay
- [ ] Spectator connections are read-only — no game actions can be taken via WebSocket
- [ ] When a game ends, all connected clients receive `{ type: "game_end", data: { winner, loser } }` and connection closes with code 1000
- [ ] Non-existent or completed games return HTTP 404 (WebSocket handshake rejection)
- [ ] Connection heartbeat: server sends `{ type: "ping" }` every 30s; if no pong within 15s, disconnect stale client
- [ ] Graceful cleanup on disconnect: remove client from subscriber list without affecting other spectators or game state
- [ ] WebSocket router is mounted in `main.py` alongside existing REST routers
- [ ] >=6 tests covering all axes

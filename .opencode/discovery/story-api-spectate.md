# Story: Spectate WebSocket (APP-04)

## User Story
As a spectator, I want to watch a live game in real-time via WebSocket, seeing game state updates as they happen, so that I can follow along without participating.

## Context
**Status: ✅ Complete**

Implemented as APP-04. Real-time game state streaming for spectators via WebSocket:

- **`WS /ws/game/{game_id}`**: WebSocket endpoint accepting spectator connections.
- **Pub/Sub pattern**: Each connected WebSocket registers a listener callback on the game's `TranscriptRecorder`. Events are pushed to per-connection `asyncio.Queue`.
- **Initial state on connect**: Sends full GameState snapshot immediately after accept.
- **Event streaming**: All transcript event types streamed in real-time (cast, resolve, trigger, sba, zone_change, damage, phase_change, priority_grant).
- **Game-end detection**: Sends `game_end` notification, closes with code 1000.
- **Per-connection isolation**: Each spectator has own queue — slow clients don't block others.
- **No heartbeat task**: Uses `queue.get(timeout=IDLE_INTERVAL)` for disconnect detection instead.

## Acceptance Criteria
- [x] `WS /ws/game/{game_id}` WebSocket endpoint
- [x] Initial state snapshot sent on connect
- [x] Real-time event streaming via pub/sub listener on TranscriptRecorder
- [x] Game-end notification with winner/loser
- [x] Rejects connections to non-existent/completed games (close code 4004)
- [x] Read-only: incoming non-pong messages silently ignored
- [x] Per-connection asyncio.Queue for isolated event delivery
- [x] Graceful disconnect cleanup (unregister listener, remove from registry)
- [x] 16 tests covering connect, event streaming, multiple connections, game-end, rejection cases, cleanup

## Dependencies
- None (uses existing TranscriptRecorder + asyncio; no new dependencies)

## Priority: Medium | Effort: Completed ✅

## Notes
- Key file: `mtg_engine/api/routers/spectate.py`
- Test file: `tests/api/test_spectate_ws.py`
- Uses `TranscriptRecorder.register_listener()` / `unregister_listener()` for lifecycle
- Listener callbacks are synchronous — use `queue.put_nowait()` to bridge sync→async
- Module-level `_spectators: dict[str, set[SpectatorConnection]]` registry
- Max queue size 256; slow clients have events dropped (QueueFull silently caught)

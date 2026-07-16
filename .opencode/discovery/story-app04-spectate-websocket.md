# Story: Spectate / WebSocket (APP-04)

## User Story
As a spectator or frontend application, I want to receive real-time game state updates via WebSocket so that I can display live game progress without polling.

## Context
The engine currently uses REST-only communication: clients poll `GET /game/{id}` and `GET /game/{id}/legal-actions` to get current state. The `GameManager` in `mtg_engine/api/game_manager.py` maintains an in-memory dict of active games (`_games: dict[str, GameState]`).

FastAPI has native WebSocket support via `fastapi.WebSocket`. This story adds a WebSocket endpoint that broadcasts game state changes (phase transitions, casts, damage, life changes, etc.) to connected spectators. The existing `TranscriptRecorder` already fires events for every meaningful game action — these can be tapped into for real-time broadcasting.

## Acceptance Criteria
- [ ] `WebSocket /ws/game/{game_id}` endpoint accepts connections and sends initial game state on connect
- [ ] On each game event (phase change, cast, resolve, damage, life change, zone change, priority grant), connected WebSocket clients receive a JSON message: `{ type: "<event_type>", data: { ... }, timestamp: float }`
- [ ] Multiple spectators can connect to the same game simultaneously without interfering with gameplay
- [ ] Spectator connections are read-only — no game actions can be taken via WebSocket (actions still go through REST endpoints)
- [ ] When a game ends, all connected clients receive a `{ type: "game_end", data: { winner, loser } }` message and the connection is closed with code 1000
- [ ] If a client connects to a non-existent or completed game, return HTTP 404 (WebSocket handshake rejection)
- [ ] Connection heartbeat: server sends `{ type: "ping" }` every 30s; if no pong received within 15s, disconnect the stale client
- [ ] Graceful cleanup on disconnect: remove client from subscriber list without affecting other spectators or game state
- [ ] The WebSocket router is mounted in `main.py` alongside existing REST routers
- [ ] >= 6 tests covering: connect and receive initial state, event broadcasting during gameplay, multiple simultaneous connections, game-end notification, non-existent game rejection, disconnect cleanup

## Dependencies
- None (FastAPI has built-in WebSocket support; GameManager already tracks active games)

## Priority: Medium

## Notes
- The WebSocket endpoint should NOT be the primary interface for human players — it supplements REST. Human actions still go through `POST /game/{id}/choice`, `POST /game/{id}/cast`, etc.
- Consider using a pub/sub pattern: register a listener on `TranscriptRecorder` that fans out events to all connected WebSocket clients for that game_id. This avoids modifying engine code.
- The subscriber list should be keyed by game_id: `dict[str, set[WebSocket]]`. Clean up entries when the last client disconnects or the game ends.
- For production use, consider adding authentication/authorization later (e.g., only allow spectating games you're a player in).

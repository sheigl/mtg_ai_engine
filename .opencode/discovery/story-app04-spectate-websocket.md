# Story: Spectate / WebSocket (APP-04)

## User Story
As a spectator or frontend application, I want to receive real-time game state updates via WebSocket so that I can display live game progress without polling.

## Context
The engine currently uses REST-only communication: clients poll `GET /game/{id}` and `GET /game/{id}/legal-actions` to get current state. The `GameManager` in `mtg_engine/api/game_manager.py` maintains an in-memory dict of active games (`_games: dict[str, GameState]`).

FastAPI has native WebSocket support via `fastapi.WebSocket`. This story adds a WebSocket endpoint that broadcasts game state changes (phase transitions, casts, damage, life changes, etc.) to connected spectators. The existing `TranscriptRecorder` already fires events for every meaningful game action — these can be tapped into for real-time broadcasting.

## Acceptance Criteria
- [x] `WebSocket /ws/game/{game_id}` with initial state on connect
- [x] Event broadcasting via pub/sub TranscriptRecorder listeners
- [x] Multiple simultaneous spectators supported
- [x] Read-only — no game actions via WebSocket
- [x] Game-end notification with winner/loser
- [x] Non-existent/completed games rejected (close code 4004)
- [x] Graceful cleanup on disconnect
- [x] 16 tests covering: connect, event streaming, multi-connection, game-end, rejection, cleanup

## Dependencies
- None (FastAPI has built-in WebSocket support; GameManager already tracks active games)

## Status: ✅ Complete

Implemented with 16 tests. Pub/sub via TranscriptRecorder listeners, per-connection asyncio.Queue, initial state on connect, game-end detection.

## Priority: Medium

## Notes
- The WebSocket endpoint should NOT be the primary interface for human players — it supplements REST. Human actions still go through `POST /game/{id}/choice`, `POST /game/{id}/cast`, etc.
- Consider using a pub/sub pattern: register a listener on `TranscriptRecorder` that fans out events to all connected WebSocket clients for that game_id. This avoids modifying engine code.
- The subscriber list should be keyed by game_id: `dict[str, set[WebSocket]]`. Clean up entries when the last client disconnects or the game ends.
- For production use, consider adding authentication/authorization later (e.g., only allow spectating games you're a player in).

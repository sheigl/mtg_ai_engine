# Story: Game Replay (APP-03)

## User Story
As a player or analyst, I want to step through a completed game replay from its transcript so that I can review key moments, understand game flow, and analyze decisions.

## Context
The engine already has `TranscriptRecorder` in `mtg_engine/export/transcript.py` with full event recording: phase_change, cast, resolve, trigger, sba, zone_change, damage, priority_grant, choice_made, attack, block, play_land, activate, life_change, draw, game_end. Each entry has seq, event_type, description, data, turn, phase, step.

The export system (`mtg_engine/export/`) also produces snapshots (board state at each priority grant) and rules Q&A pairs. Currently these are available as bulk exports via `GET /export/{game_id}/transcript` but there's no structured replay interface for stepping through events one at a time.

This story adds a replay engine that reconstructs game state from transcript entries, allowing callers to step forward/backward through the game and inspect the board state at each event boundary.

## Acceptance Criteria
- [x] `GET /replay/{game_id}/info` endpoint returns replay metadata
- [x] `GET /replay/{game_id}/events` returns paginated transcript entries with navigation links
- [x] Board state reconstruction via two-tier approach (snapshot anchors + incremental event replay)
- [x] `GET /replay/{game_id}/timeline` returns condensed timeline grouped by turn/phase
- [x] Replay data sourced from in-memory export store (no MongoDB dependency)
- [x] Deleted games return HTTP 404
- [x] Multiple tests covering: forward/backward stepping, pagination, timeline, board state accuracy, error handling

## Dependencies
- None (TranscriptRecorder and export system already exist)

## Status: ✅ Complete

Implemented with two-tier board reconstruction (snapshot anchors + incremental event replay). Timeline grouping, paginated events, stateless client-driven navigation.

## Priority: Medium

## Notes
- Board state reconstruction from transcript alone is lossy — the transcript records events but not full snapshots. The replay should leverage existing snapshot data (`SnapshotRecorder`) when available for accurate board states, falling back to event-based reconstruction for intermediate steps.
- Consider adding a `replay_step` field to GameState that tracks current position during active replay sessions, or keep it stateless and require the client to pass `from_event_seq`.
- The router will be part of the existing export router (`mtg_engine/api/routers/export.py`) under `/export/{game_id}/replay/*` paths for consistency.

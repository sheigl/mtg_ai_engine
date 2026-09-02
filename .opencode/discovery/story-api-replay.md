# Story: Game Replay (APP-03)

## User Story
As a player or analyst, I want to step through a completed game replay from its transcript so that I can review key moments, understand game flow, and analyze decisions.

## Context
**Status: ✅ Complete**

Implemented as APP-03. Two-tier board state reconstruction from transcript data:

- **Snapshot anchors**: Full GameState dumps captured at priority grants (via `/legal-actions`) provide exact state at known points.
- **Incremental event replay**: Between snapshots, reconstructs intermediate states by applying transcript events sequentially.
- **`GET /replay/{game_id}/info`**: Returns replay metadata (game_id, total_events, turns, winner, loser, format).
- **`GET /replay/{game_id}/events?page=1&per_page=25`**: Paginated transcript entries with has_next/has_prev navigation.
- **`POST /replay/{game_id}/step`**: Navigate forward/backward returning board state snapshot at event boundary.
- **`GET /replay/{game_id}/timeline`**: Condensed timeline grouped by turn/phase with event counts.
- **Board state includes**: battlefield permanents (P/T, tapped, counters), player life totals, hand sizes, graveyard top cards, stack contents.

## Acceptance Criteria
- [x] `GET /replay/{game_id}/info` returns replay metadata
- [x] `GET /replay/{game_id}/events` with pagination and has_next/has_prev
- [x] `POST /replay/{game_id}/step` with direction (forward/backward) and from_event_seq
- [x] Board state reconstruction from snapshot anchors + incremental event replay
- [x] `GET /replay/{game_id}/timeline` grouped by turn/phase with event counts
- [x] Data sourced from in-memory export store (no MongoDB dependency)
- [x] HTTP 404 for deleted/non-existent games
- [x] Human-readable event descriptions from TranscriptRecorder

## Dependencies
- None (TranscriptRecorder and export system already exist)

## Priority: Medium | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/api/routers/export.py` (replay sub-endpoints), `mtg_engine/export/transcript.py`, `mtg_engine/export/store.py`
- Snapshot recording happens at each priority grant in `/legal-actions`
- Stateless design — client passes `from_event_seq` for navigation
- Board state reconstruction is lossy between snapshots; snapshot anchors provide exact state

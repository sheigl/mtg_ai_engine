# Story: Game Replay (APP-03)

## User Story
As a player or analyst, I want to step through a completed game replay from its transcript so that I can review key moments, understand game flow, and analyze decisions.

## Context
The engine already has `TranscriptRecorder` in `mtg_engine/export/transcript.py` with full event recording: phase_change, cast, resolve, trigger, sba, zone_change, damage, priority_grant, choice_made, attack, block, play_land, activate, life_change, draw, game_end. Each entry has seq, event_type, description, data, turn, phase, step.

The export system (`mtg_engine/export/`) also produces snapshots (board state at each priority grant) and rules Q&A pairs. Currently these are available as bulk exports via `GET /export/{game_id}/transcript` but there's no structured replay interface for stepping through events one at a time.

This story adds a replay engine that reconstructs game state from transcript entries, allowing callers to step forward/backward through the game and inspect the board state at each event boundary.

## Acceptance Criteria
- [ ] `GET /replay/{game_id}/info` endpoint returns replay metadata: `{ data: { game_id, total_events, turns, winner, loser, format } }`
- [ ] `GET /replay/{game_id}/events?page=1&per_page=25` returns paginated transcript entries with navigation links (has_next, has_prev)
- [ ] `POST /replay/{game_id}/step` accepts `{ direction: "forward" | "backward", from_event_seq: int }` and returns the next/previous event along with a reconstructed board state snapshot at that point
- [ ] Board state reconstruction includes: battlefield permanents (with power/toughness, tapped status, counters), player life totals, hand sizes, graveyard top cards, stack contents
- [ ] `GET /replay/{game_id}/timeline` returns a condensed timeline grouped by turn/phase with event counts per phase for quick navigation
- [ ] Replay data is sourced from the in-memory export store (same as existing `/export/{game_id}/transcript`) — no MongoDB dependency required
- [ ] If game has been deleted (not in memory), replay endpoints return HTTP 404
- [ ] Event descriptions are human-readable natural language (already provided by TranscriptRecorder)
- [ ] >= 8 tests covering: replay info retrieval, forward stepping through events, backward stepping, pagination of events, timeline generation, board state reconstruction accuracy, game-not-found handling, multi-turn game replay

## Dependencies
- None (TranscriptRecorder and export system already exist)

## Priority: Medium

## Notes
- Board state reconstruction from transcript alone is lossy — the transcript records events but not full snapshots. The replay should leverage existing snapshot data (`SnapshotRecorder`) when available for accurate board states, falling back to event-based reconstruction for intermediate steps.
- Consider adding a `replay_step` field to GameState that tracks current position during active replay sessions, or keep it stateless and require the client to pass `from_event_seq`.
- The router will be part of the existing export router (`mtg_engine/api/routers/export.py`) under `/export/{game_id}/replay/*` paths for consistency.

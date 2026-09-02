# Story: Player Stats / ELO (APP-06)

## User Story
As a player, I want to track my win/loss record, ELO rating, and matchup statistics so that I can measure improvement over time and understand my strengths and weaknesses.

## Context
**Status: ✅ Complete**

Implemented as APP-06. Persistent player statistics and ELO ratings via MongoDB:

- **Player profiles**: Win/loss record, total games, ELO rating per player.
- **ELO calculation**: Standard ELO formula with K=32, initialized at 1200 for new players.
- **Matchup tracking**: Per-opponent and per-format statistics.
- **Format-specific stats**: Track win/loss broken down by format.
- **Automatic updates**: Stats updated atomically on game completion via `update_stats_for_game_completion()`.

## Acceptance Criteria
- [x] `POST /stats/player/{name}` — create/update player profile (idempotent, HTTP 201/200)
- [x] `GET /stats/player/{name}` — full stats: wins, losses, win_rate, elo_rating, total_games, formats, matchups
- [x] `GET /leaderboard` — top players by ELO descending (optional format filter and limit)
- [x] `GET /stats/player/{name}/matchups` — per-opponent stats sorted by most games
- [x] ELO initialized at 1200; updated after each completed game with K=32
- [x] Atomic MongoDB operations (`$inc`, `$set` upsert) for race-condition safety
- [x] Stats stored in MongoDB collection `player_stats`
- [x] HTTP 503 when MongoDB unconfigured
- [x] 39 tests (13 engine + 12 API + 5 game completion hook + 9 integration)

## Dependencies
- MongoDB persistence (`mtg_engine/persistence/mongo_client.py`)

## Priority: Low | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/models/stats.py`, `mtg_engine/engine/stats.py`, `mtg_engine/api/routers/player_stats.py`
- Test files: `tests/api/test_player_stats.py` and related engine tests
- ELO update hooked into game completion via `run_coroutine_threadsafe()` in `game.py` DELETE handler
- Per-player try/except isolation prevents one failed update from corrupting others
- Future enhancement: Glicko-2 (with RD and volatility) instead of basic ELO

# Story: Player Stats / ELO (APP-06)

## User Story
As a player, I want to track my win/loss record, ELO rating, and matchup statistics so that I can measure improvement over time and understand my strengths and weaknesses.

## Context
The engine already has `game_records.py` with MongoDB-backed game metadata queries (`GET /games/records`, `GET /games/records/{game_id}`). Game records include: player names, winner, loser, format, turn count, created_at timestamp, is_complete flag. The persistence layer uses `mtg_engine/persistence/mongo_client.py`.

This story adds a dedicated stats system with:
1. **Player profiles**: win/loss record, total games played, ELO rating
2. **ELO calculation**: standard Glicko-2 simplified (K-factor based) after each completed game
3. **Matchup tracking**: per-opponent and per-format statistics

## Acceptance Criteria
- [x] `GET /stats/player/{name}` returns wins, losses, win_rate, elo, formats, matchups
- [x] ELO rating: starts at 1200, standard ELO formula with K=32
- [x] `GET /stats/player/{name}/matchups` returns per-opponent stats sorted by games played
- [x] `POST /stats/player/{name}` idempotent create/update (HTTP 201/200)
- [x] Auto-update on game completion via `run_coroutine_threadsafe()` in DELETE handler
- [x] `GET /leaderboard` returns top players by ELO, optional format filter and limit
- [x] MongoDB-backed with atomic $inc/$set operations; HTTP 503 when MongoDB unavailable
- [x] 39 tests covering: engine, API, game completion hook

## Dependencies
- Game recording system (already exists via `game_records.py` and MongoDB persistence)

## Status: ✅ Complete

Implemented with 39 tests (13 engine + 12 API + 5 game completion hook). MongoDB-backed with ELO calculation, format tracking, matchup records, leaderboard endpoint.

## Priority: Low

## Notes
- ELO update should be triggered atomically with game completion. The cleanest approach is to add the stats update to the existing `DELETE /game/{id}` handler in `game.py`, which already writes game metadata to MongoDB.
- Consider using atomic MongoDB operations (`$inc` for wins/losses, `$set` for ELO) to avoid race conditions when multiple games complete simultaneously.
- The `PlayerStats` model should be defined in `mtg_engine/models/stats.py` following the existing Pydantic v2 patterns.
- Future enhancement: add Glicko-2 (with RD and volatility) instead of basic ELO, but start with simple ELO for MVP.

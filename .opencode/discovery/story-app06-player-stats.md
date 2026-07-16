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
- [ ] `GET /stats/player/{player_name}` returns: `{ data: { player, wins, losses, win_rate, elo_rating, total_games, formats: { format_name: { wins, losses } }, recent_games: [{ game_id, opponent, result, date }] } }`
- [ ] ELO rating initialized at 1200 for new players; updated after each completed game using standard ELO formula with K=32
- [ ] `GET /stats/player/{player_name}/matchups` returns per-opponent stats: `{ opponent, wins, losses, win_rate }` sorted by most games played
- [ ] `POST /stats/player/{player_name}` creates a new player profile if one doesn't exist (idempotent — no error if already exists)
- [ ] Stats are automatically updated when a game is recorded to MongoDB (hook into the existing game deletion/export flow in `game.py` DELETE handler, or via a background task)
- [ ] `GET /stats/leaderboard?format=commander&limit=10` returns top players by ELO rating for an optional format filter
- [ ] Stats stored in MongoDB collection `player_stats` with document structure: `{ player_name, elo, wins, losses, formats: { ... }, matchups: { opponent: { wins, losses } }, updated_at }`
- [ ] If MongoDB is not configured, stats endpoints return HTTP 503 (consistent with game_records.py pattern)
- [ ] >= 8 tests covering: new player creation, ELO update after win/loss, win rate calculation, matchup tracking between two players, leaderboard ordering, format-filtered stats, non-existent player handling, MongoDB-unavailable error

## Dependencies
- Game recording system (already exists via `game_records.py` and MongoDB persistence)

## Priority: Low

## Notes
- ELO update should be triggered atomically with game completion. The cleanest approach is to add the stats update to the existing `DELETE /game/{id}` handler in `game.py`, which already writes game metadata to MongoDB.
- Consider using atomic MongoDB operations (`$inc` for wins/losses, `$set` for ELO) to avoid race conditions when multiple games complete simultaneously.
- The `PlayerStats` model should be defined in `mtg_engine/models/stats.py` following the existing Pydantic v2 patterns.
- Future enhancement: add Glicko-2 (with RD and volatility) instead of basic ELO, but start with simple ELO for MVP.

# Feature 034: Game State Persistence and Resume

## Problem
Games are stored entirely in memory. If the server restarts or the browser is closed, all active games are lost permanently. There is no mechanism to save in-progress game state to durable storage or to restore games upon server startup.

## Current State
- `GameManager._games` is a Python dict — all game state lives in memory
- `MongoGamePersister` writes **training/analysis data** (decisions, transcripts) to MongoDB but never writes the recoverable game state
- `GameState.model_dump()` / `GameState.model_validate()` round-trip correctly (Pydantic v2)
- Game list endpoint only reads from in-memory dict
- Series config (`GameManager._series`) is not persisted

## Spec

### Requirements
1. **Save game state to MongoDB on every state change** — after each action (cast, attack, pass, etc.), persist the full `GameState` to a `game_states` collection
2. **Restore games on server startup** — when the server starts, load all non-completed games from MongoDB back into `GameManager._games`
3. **Resume browser sessions** — when a user navigates to a game URL, the game is available even after a server restart
4. **Persist series state** — `SeriesConfig` objects are saved alongside game state
5. **Cleanup completed games** — completed games that have been persisted don't need to stay in memory forever; they can be removed from the in-memory dict after a configurable delay

### Design Decisions
- Use `pymongo` (synchronous) for writes — game state saves happen in request handlers which are sync
- Use a dedicated `game_states` MongoDB collection (separate from `games` metadata collection used by `MongoGamePersister`)
- Save only the latest state (upsert by `game_id`) — no history of intermediate states (decisions already capture that)
- On startup, load all non-completed games from MongoDB
- Debounce saves — don't save on every single internal state change, only on user-facing actions
- If MongoDB is unavailable, fall back to in-memory only (games are lost on restart, same as current behavior)

## Implementation Plan

### Phase 1: Backend — Save Game State on Every Action

1. **`mtg_engine/persistence/game_state_store.py`** — New module with `GameStateStore` class:
   - `upsert(game_id, state_dict, series_config=None)` — Save game state dict to `game_states` collection
   - `load(game_id) -> (state_dict, series_config) | None` — Load a game state
   - `load_all_active() -> list[(game_id, state_dict, series_config)]` — Load all non-completed games
   - `delete(game_id)` — Remove a game state
   - Uses `pymongo` (sync), same pattern as `ScryfallClient` and `DeckCache`
   - Creates indexes on `game_id` (unique) and `is_complete`

2. **`mtg_engine/api/game_manager.py`** — Add persistence methods:
   - Add `_store: GameStateStore | None` field
   - `save_game(game_id)` — Serializes `GameState` via `model_dump()` and calls `store.upsert()`
   - `delete_game(game_id)` — Also calls `store.delete()`
   - Modify `update()` to optionally persist after each update
   - `restore_games()` — On startup, calls `store.load_all_active()` and reconstructs `GameState` objects

3. **`mtg_engine/api/routers/game.py`** — After any action that modifies game state:
   - Call `mgr.save_game(game_id)` after: cast, activate, pass, declare_attackers, declare_blockers, choice, mulligan, draw, play_land, etc.
   - This is the most natural place since all state mutations go through this router

4. **`mtg_engine/api/routers/ai_game.py`** and **`human_game.py`** — After game creation:
   - Call `mgr.save_game(game_id)` immediately after `create_game()`

### Phase 2: Backend — Restore Games on Startup

5. **`mtg_engine/api/main.py`** — In the `lifespan` context manager:
   - After MongoDB connection is confirmed, call `mgr.restore_games()`
   - This loads all non-completed games back into memory

6. **`mtg_engine/api/game_manager.py`** — `restore_games()`:
   - For each saved game state dict, reconstruct `GameState` via `GameState.model_validate(state_dict)`
   - Reconstruct `SeriesConfig` from saved dict
   - Store in `self._games`, `self._series`, etc.

### Phase 3: Frontend — Resume UX

7. **No frontend changes needed** — The game list endpoint already returns all games. After a server restart, restored games will appear in the list naturally. Navigating to `/game/{id}` or `/human-game/{id}` already works because it fetches game state from the API.

### Phase 4: Cleanup

8. **Auto-cleanup** — On game end, mark the game as complete in MongoDB. Optionally remove completed games from memory after a delay.

## Files to Create/Modify

| File | Action |
|---|---|
| `mtg_engine/persistence/game_state_store.py` | **CREATE** — `GameStateStore` class with upsert/load/delete |
| `mtg_engine/api/game_manager.py` | **MODIFY** — Add `save_game()`, `restore_games()`, wire up `_store` |
| `mtg_engine/api/routers/game.py` | **MODIFY** — Add `mgr.save_game()` calls after state mutations |
| `mtg_engine/api/routers/ai_game.py` | **MODIFY** — Save after game creation |
| `mtg_engine/api/routers/human_game.py` | **MODIFY** — Save after game creation |
| `mtg_engine/api/main.py` | **MODIFY** — Call `mgr.restore_games()` on startup |
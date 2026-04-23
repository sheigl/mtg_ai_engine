# Implementation Plan: Game Series Mode (Best-of-N)

**Branch**: `032-game-series` | **Date**: 2026-04-21 | **Spec**: `/specs/032-game-series/spec.md`
**Input**: Feature specification from `/specs/032-game-series/spec.md`

## Summary

Add a "series count" option to game creation that automatically spawns consecutive games with identical settings when each game ends. The feature touches the backend (series registry, game loop hooks, game list API) and frontend (creation forms, game list cards).

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5.x, React 18
**Primary Dependencies**: FastAPI, Pydantic, React Query
**Storage**: In-memory (GameManager)
**Testing**: Manual browser + backend pytest
**Target Platform**: Modern browsers
**Project Type**: Web SPA (Vite + React) + FastAPI backend
**Performance Goals**: Series games spawn within 1s of the previous game ending
**Constraints**: Must not break single-game flow; must work for both AI vs AI and human vs AI
**Scale/Scope**: Backend + frontend; ~8 files touched

## Constitution Check

- No new external dependencies.
- Series state is in-memory only (no database migration).
- Minimal changes to existing game loop logic.

## Project Structure

### Documentation (this feature)

```text
specs/032-game-series/
├── spec.md              # Feature specification
├── plan.md              # This file
```

### Source Code Changes

```text
backend:
mtg_engine/api/game_manager.py           # ADD: Series registry + create_series_game helper
mtg_engine/api/routers/ai_game.py        # UPDATE: Accept series_count, wire series creation
mtg_engine/api/routers/human_game.py     # UPDATE: Accept series_count, wire series creation
mtg_engine/api/routers/game.py           # UPDATE: list_games includes series info
mtg_engine/models/game.py                # UPDATE: GameState.series_id field
ai_client/game_loop.py                   # UPDATE: After game ends, spawn next series game

frontend:
frontend/src/types/game.ts               # UPDATE: GameSummary with series fields
frontend/src/components/CreateGameForm.tsx # UPDATE: Series count input
frontend/src/components/HumanGameCreator.tsx # UPDATE: Series count input
frontend/src/components/GameList.tsx     # UPDATE: Show series progress on cards
frontend/src/hooks/useGameList.ts        # (no change — same endpoint)
```

## Implementation Tasks

### Phase 1: Backend Core

1. **Add `series_id` to `GameState`** — optional string field.
2. **Add `SeriesConfig` and `_series_registry` to `GameManager`**:
   ```python
   class SeriesConfig:
       series_id: str
       total_games: int
       completed_games: int
       settings: dict  # frozen copy of creation params
       results: list[SeriesResult]
       active_game_id: str | None
   ```
3. **Add `create_series_game` to `GameManager`** — creates the next game in a series using stored settings but a new random seed.
4. **Add `record_series_result` to `GameManager`** — when a game ends, record winner and increment counter.

### Phase 2: Backend Endpoints

1. **Update `AIGameRequest`** — add `series_count: int = 1`.
2. **Update `create_ai_game`** — if series_count > 1, create series config, set `series_id` on the game, and store in registry.
3. **Update `HumanGameRequest`** — add `series_count: int = 1`.
4. **Update `create_human_game`** — same as above.
5. **Update `list_games`** — include `series_id`, `series_game_number`, and `series_total` in `GameSummary`.

### Phase 3: Game Loop Hooks

1. **Update `GameLoop.run`** — after `print_game_summary`, check if `game_id` is part of a series. If yes and more games remain, call `create_series_game` and start a new loop thread.
2. **Update `HybridGameLoop`** — same check after game ends.

### Phase 4: Frontend Forms

1. **Update `CreateGameForm`** — add "Series count" number input (min 1, default 1).
2. **Update `HumanGameCreator`** — add "Series count" number input.
3. **Send `series_count` in POST body**.

### Phase 5: Frontend Game List

1. **Update `GameSummary` type** — add optional `series_id`, `series_game_number`, `series_total`, `series_score`.
2. **Update `GameList`** — group series games visually or show series badge with score.

### Phase 6: Build & Verify

- TypeScript compilation
- Vite build
- Backend tests pass
- Manual test: create 3-game AI series, verify all complete

## Test Plan

- [ ] Create single AI game (series_count=1) — behaves normally
- [ ] Create 3-game AI series — all 3 games complete automatically
- [ ] Create 2-game human vs AI series — human can play both
- [ ] Game list shows "Game 2 of 3" and score for series games
- [ ] Series games have independent seeds (different opening hands)
- [ ] Draws count toward total but not win count
- [ ] Deleting an active series game stops the series

## Rollback

Revert all file changes; series state is in-memory only so no persistent data to clean up.

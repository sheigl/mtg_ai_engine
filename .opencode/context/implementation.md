# Implementation Notes

## APP-06 Code Review R3 Fixes (2026-07-15)

### Files Modified
- `mtg_engine/api/routers/player_stats.py` — exception handler split, type hint added
- `tests/api/test_player_stats.py` — 2 new game completion tests

### Changes Summary

#### player_stats.py
1. **CRITICAL #1 (exception handler):** Split single try/except wrapping both winner+loser updates into two independent try/except blocks with `winner_updated`/`loser_updated` flags. Only retry failed ones via full `$set` replace, preventing overwrites of already-successful updates.
2. **MINOR #4 (type hint):** Added `gs: GameState` type annotation to `update_stats_for_game_completion()` signature; added `GameState` import from `mtg_engine.models.game`.

#### test_player_stats.py
1. **MAJOR #2 (both players new):** Added `test_game_completion_both_players_new` — empty docs list, both players upserted via `$set`, verifies positive ELO for winner and loser.
2. **MAJOR #3 (format None fallback):** Added `test_game_completion_format_none_fallback` — sets `gs.format = None`, verifies stats stored under `"standard"` key in formats dict.

### Test Results
- 30 player stats tests pass (was 28, +2 new)
- 2640 total regression tests pass (was 2638), 0 regressions

## APP-06 Code Review R2 Fixes (2026-07-15)

### Files Modified
- `mtg_engine/api/routers/player_stats.py` — 4 fixes + documentation
- `tests/api/test_player_stats.py` — mock extension + 3 new tests

### Changes Summary

#### player_stats.py
1. **CRITICAL #1 ($inc upsert bug):** Split update logic into two paths: existing players get atomic `$inc`, new players get full `$set` with computed stats. Previously, `$inc` with `upsert=True` would initialize missing fields to 0, causing negative ELO for new losers (e.g., `0 + (-16) = -16`).
2. **MAJOR #4 (narrow exception):** Changed `except Exception:` to `except (WriteError, OperationFailure):` from pymongo.errors. Added import at top of file.
3. **MINOR #6 (format fallback):** Changed `gs.format` to `getattr(gs, "format", None) or "standard"` to prevent `"formats.None"` MongoDB key.
4. **TODO documentation:** Added comment near ELO delta computation documenting stale-delta race condition as architectural limitation.

#### test_player_stats.py
1. **MAJOR #3 (mock $inc support):** Extended `_mock_col.update_one()` to handle both `$set` and `$inc`, including dotted paths like `formats.commander.wins`. For upsert with `$inc`, simulates MongoDB behavior of initializing missing fields from 0 + delta.
2. **MAJOR #5 (game completion tests):** Added `TestGameCompletionStatsUpdate` class with 3 sync tests using `asyncio.run()`:
   - `test_game_completion_both_players_exist` — verifies $inc path for existing players
   - `test_game_completion_new_player_upsert` — verifies $set path catches critical bug #1
   - `test_game_completion_no_winner_skips` — verifies early return when winner is None

### Test Results
- 28 player stats tests pass (was 25, +3 new)
- 2638 total regression tests pass (was 2635), 0 regressions

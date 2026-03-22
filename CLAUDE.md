# mtg_ai_engine Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-21

## Active Technologies
- Python 3.11 (matches existing codebase) + `httpx` (HTTP to engine API), `openai` (OpenAI-compatible LLM client), `argparse` (stdlib CLI parsing) (008-ai-cli-client)
- None — stateless client; game state lives in the engine (008-ai-cli-client)
- Python 3.11 (matches existing codebase) + FastAPI, Pydantic v2, httpx, openai (all existing) (009-commander-format)
- In-memory game state (existing); SQLite Scryfall cache extended with `color_identity` (009-commander-format)
- Python 3.11 (backend, matches existing) + TypeScript 5.x (frontend) (010-game-observer-ui)
- N/A (reads from existing in-memory game state) (010-game-observer-ui)

- Python 3.11 + FastAPI, Pydantic v2, standard `logging` module (007-play-by-play-log)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes
- 010-game-observer-ui: Added Python 3.11 (backend, matches existing) + TypeScript 5.x (frontend)
- 009-commander-format: Added Python 3.11 (matches existing codebase) + FastAPI, Pydantic v2, httpx, openai (all existing)
- 008-ai-cli-client: Added Python 3.11 (matches existing codebase) + `httpx` (HTTP to engine API), `openai` (OpenAI-compatible LLM client), `argparse` (stdlib CLI parsing)


<!-- MANUAL ADDITIONS START -->
## Play-by-Play Verbose Logging (007)

Enable per-game play-by-play output by passing `"verbose": true` to `POST /game`.
Toggle mid-game with `POST /game/{game_id}/verbose` body `{"enabled": true/false}`.

Verbose output goes to the **`mtg_engine.verbose`** Python logger at `INFO` level.
Configure it separately from the application logger if needed:
```python
logging.getLogger("mtg_engine.verbose").setLevel(logging.INFO)
```

Key components:
- `mtg_engine/engine/verbose_log.py` — `VerboseLogger` class + global zone-change listener
- `mtg_engine/export/transcript.py` — `TranscriptRecorder` with listener registration
- `GameManager.get_recorder(game_id)` — retrieve per-game recorder
- `GameManager.set_verbose(game_id, enabled)` — toggle logging at runtime
<!-- MANUAL ADDITIONS END -->

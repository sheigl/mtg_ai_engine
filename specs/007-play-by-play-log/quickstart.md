# Quickstart: Play-by-Play Game Log

**Feature**: 007-play-by-play-log
**Date**: 2026-03-21

## Enable at Game Creation

Pass `"verbose": true` when creating a game via the API:

```bash
curl -X POST http://localhost:8000/game \
  -H "Content-Type: application/json" \
  -d '{
    "player1_name": "Alice",
    "player2_name": "Bob",
    "deck1": ["Forest", "Forest", "Llanowar Elves", ...],
    "deck2": ["Mountain", "Mountain", "Goblin Guide", ...],
    "verbose": true
  }'
```

The server will begin emitting play-by-play output to its log stream immediately. No further API calls are needed.

## Toggle Mid-Game

To enable or disable verbose logging for an already-running game:

```bash
# Enable
curl -X POST http://localhost:8000/game/{game_id}/verbose \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Disable
curl -X POST http://localhost:8000/game/{game_id}/verbose \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## View the Output

Verbose output goes to the `mtg_engine.verbose` Python logger. When running the server in development:

```bash
# Docker
docker compose logs -f

# Direct
uvicorn mtg_engine.api.main:app --log-level info
```

You will see output interleaved with normal application logs:

```
INFO:mtg_engine.verbose:═══ Turn 1 — Alice ════════════════
INFO:mtg_engine.verbose:  [Beginning / Draw]
INFO:mtg_engine.verbose:    Alice draws a card.
INFO:mtg_engine.verbose:  [Pre-combat Main]
INFO:mtg_engine.verbose:    Alice plays Forest.
...
```

## Disable by Default (Batch Simulations)

The `verbose` flag defaults to `false`. All batch simulation games run silently with no performance overhead unless explicitly enabled.

## Running Tests

```bash
pytest tests/rules/test_verbose_log.py -v
```

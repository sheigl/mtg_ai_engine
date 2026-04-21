# Quickstart: Player Default Settings

**Feature**: 028-player-default-settings
**Date**: 2026-04-20

## Prerequisites

- MongoDB must be configured via the `MONGODB_URL` environment variable (same as Feature 025).
- The backend must be running (`python -m mtg_engine.api.main` or equivalent).

## Save Defaults for a Player Type

```bash
curl -X PUT http://localhost:8000/player-defaults/ai \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "base_url": "http://localhost:8080/v1",
      "model": "gpt-4",
      "enable_thinking": true
    }
  }'
```

## Save Defaults for Heuristic Players

```bash
curl -X PUT http://localhost:8000/player-defaults/heuristic \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "personality": {
        "name": "aggro",
        "chance_to_attack_into_trade": 0.80,
        "attack_into_trade_when_tapped_out": true,
        "chance_to_counter_cmc_1": 0.00,
        "chance_to_counter_cmc_2": 0.25,
        "token_generation_chance": 0.90
      }
    }
  }'
```

## Retrieve Defaults

```bash
# Single type
curl http://localhost:8000/player-defaults/ai

# All types
curl http://localhost:8000/player-defaults
```

## Delete Defaults

```bash
curl -X DELETE http://localhost:8000/player-defaults/ai
```

## Verify Defaults Are Applied

1. Save defaults for a player type (e.g., `heuristic`).
2. Create a game via `POST /human-game` or `POST /game` without specifying the settings that were defaulted.
3. The AI player should behave according to the saved defaults.

Example: if you saved `heuristic` defaults with `personality.name = "aggro"`, create a game with `player2_type = "heuristic"` and observe aggressive combat behavior.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `503 MongoDB not configured` | `MONGODB_URL` not set | Set the environment variable and restart the server. |
| `404 DEFAULTS_NOT_FOUND` | No defaults saved for that type | `PUT` defaults first, or the game will use hardcoded fallbacks. |
| `422 INVALID_SETTINGS` | Settings payload doesn't match the player type's schema | Check the Pydantic model for that player type and correct the keys/values. |
| Defaults not applied to game | Request explicitly provided the same field | This is expected — request values override defaults. Omit the field in the request to let the default apply. |

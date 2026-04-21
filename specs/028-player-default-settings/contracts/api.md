# API Contracts: Player Default Settings

**Feature**: 028-player-default-settings
**Date**: 2026-04-20

## Overview

All endpoints return JSON in the envelope `{"data": ...}` on success, or standard FastAPI HTTPException responses on error.

Base path: `/player-defaults`

---

## GET /player-defaults

List all configured default settings.

### Request

```
GET /player-defaults
```

### Response 200

```json
{
  "data": {
    "defaults": [
      {
        "player_type": "human",
        "settings": {
          "auto_tap": true,
          "confirm_combat": false
        },
        "updated_at": "2026-04-20T12:00:00Z"
      },
      {
        "player_type": "heuristic",
        "settings": {
          "personality": {
            "name": "default",
            "chance_to_attack_into_trade": 0.40,
            ...
          }
        },
        "updated_at": "2026-04-20T12:05:00Z"
      }
    ]
  }
}
```

### Response 503

```json
{
  "detail": {
    "error": "MongoDB not configured",
    "error_code": "MONGODB_NOT_CONFIGURED"
  }
}
```

---

## GET /player-defaults/{player_type}

Retrieve default settings for a specific player type.

### Request

```
GET /player-defaults/human
```

### Response 200

```json
{
  "data": {
    "player_type": "human",
    "settings": {
      "auto_tap": true,
      "confirm_combat": false
    },
    "updated_at": "2026-04-20T12:00:00Z"
  }
}
```

### Response 404

```json
{
  "detail": {
    "error": "Default settings not found for player type 'heuristic'",
    "error_code": "DEFAULTS_NOT_FOUND"
  }
}
```

### Response 422

```json
{
  "detail": {
    "error": "player_type must be one of {'human', 'ai', 'heuristic'}",
    "error_code": "INVALID_PLAYER_TYPE"
  }
}
```

### Response 503

MongoDB not configured.

---

## PUT /player-defaults/{player_type}

Create or replace default settings for a player type.

### Request

```
PUT /player-defaults/ai
Content-Type: application/json

{
  "settings": {
    "base_url": "http://localhost:8080/v1",
    "model": "gpt-4",
    "enable_thinking": true
  }
}
```

### Response 200 (updated)

```json
{
  "data": {
    "player_type": "ai",
    "settings": {
      "base_url": "http://localhost:8080/v1",
      "model": "gpt-4",
      "enable_thinking": true
    },
    "updated_at": "2026-04-20T12:10:00Z"
  }
}
```

### Response 201 (created)

Same body shape as 200, but returned when the document did not previously exist.

### Response 422

```json
{
  "detail": {
    "error": "Invalid settings for player type 'ai': base_url must be a valid URL",
    "error_code": "INVALID_SETTINGS"
  }
}
```

### Response 503

MongoDB not configured.

---

## DELETE /player-defaults/{player_type}

Delete default settings for a player type.

### Request

```
DELETE /player-defaults/human
```

### Response 204

No body.

### Response 404

```json
{
  "detail": {
    "error": "Default settings not found for player type 'human'",
    "error_code": "DEFAULTS_NOT_FOUND"
  }
}
```

### Response 503

MongoDB not configured.

---

## Game Creation Integration

The following existing endpoints are modified to apply defaults. No new endpoints are added for game creation.

### POST /game

**Behavior change**: Before creating the game, if MongoDB is configured and defaults exist for each player's type, merge defaults into the request. Request values take precedence over defaults.

**No contract change**: Request/response shapes remain identical.

### POST /human-game

**Behavior change**: Same as POST /game. Defaults are merged before `GameManager.create_game` is called.

**No contract change**: Request/response shapes remain identical.

### POST /ai-game

**Behavior change**: Same as POST /game. Defaults are merged before `GameManager.create_game` is called.

**No contract change**: Request/response shapes remain identical.

# Contract: AI Game API

**Feature**: 015-ui-game-creator
**Endpoint**: `POST /ai-game`

## Purpose

Start a fully autonomous AI vs AI game. The engine creates the game, starts the AI decision loop in a background thread, and returns the game ID immediately. The caller navigates to the game board to observe progress.

---

## Request

**Method**: `POST`
**Path**: `/ai-game`
**Content-Type**: `application/json`

### Body Schema

```json
{
  "player1": {
    "name": "Alice",
    "player_type": "llm",
    "base_url": "http://localhost:11434/v1",
    "model": "devstral"
  },
  "player2": {
    "name": "Bob",
    "player_type": "heuristic",
    "base_url": "",
    "model": ""
  },
  "deck1": [],
  "deck2": [],
  "format": "standard",
  "commander1": null,
  "commander2": null,
  "verbose": false,
  "max_turns": 200,
  "debug": false,
  "observer_url": null,
  "observer_model": null
}
```

### Field Rules

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `player1.name` | string | yes | Non-empty |
| `player1.player_type` | `"llm"\|"heuristic"` | yes | |
| `player1.base_url` | string | when llm | Must start with `http://` or `https://` |
| `player1.model` | string | when llm | Non-empty |
| `player2.*` | same as player1 | yes | |
| `deck1` | string[] | no | Empty = use default deck |
| `deck2` | string[] | no | Empty = use default deck |
| `format` | `"standard"\|"commander"` | no | Default: `"standard"` |
| `commander1` | string\|null | when commander | Required if format=commander |
| `commander2` | string\|null | when commander | Required if format=commander |
| `verbose` | bool | no | Default: `false` |
| `max_turns` | int | no | Default: `200`; `0` = unlimited |
| `debug` | bool | no | Default: `false` |
| `observer_url` | string\|null | no | Must start with `http://` or `https://` if provided |
| `observer_model` | string\|null | no | Required if `observer_url` is set |

**Cross-field rules**:
- `player1.name` ≠ `player2.name`
- `commander1` and `commander2` required (non-null, non-empty) when `format == "commander"`

---

## Responses

### 200 OK — Game started

```json
{
  "data": {
    "game_id": "a3f8c21d-4b2e-4f9a-bf01-123456789abc"
  }
}
```

### 422 Unprocessable Entity — Validation error

```json
{
  "error": "Commander format requires commander1 and commander2",
  "error_code": "INVALID_REQUEST"
}
```

```json
{
  "error": "player1 has player_type=llm but base_url is missing or invalid",
  "error_code": "INVALID_PLAYER_CONFIG"
}
```

```json
{
  "error": "Card 'Boltning Ligght' not found in card database",
  "error_code": "DECK_LOAD_ERROR"
}
```

```json
{
  "error": "player1 and player2 must have different names",
  "error_code": "DUPLICATE_PLAYER_NAME"
}
```

---

## Behaviour Notes

- The endpoint returns as soon as the game is created and the background thread is started. The game loop runs independently.
- If the LLM endpoint is unreachable, the game loop falls back to passing priority (matching existing CLI fallback behaviour). The game board will reflect this.
- The `game_id` in the response is the same ID returned by `GET /game` in the game list.

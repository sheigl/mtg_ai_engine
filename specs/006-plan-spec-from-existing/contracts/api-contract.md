# API Contract: MTG Rules Engine

**Generated**: 2026-03-20  
**Source**: `/specs/006-plan-spec-from-existing/spec.md`  
**Status**: Phase 1 - Design & Contracts

---

## Overview

This document defines the REST API contract for the MTG Rules Engine. All endpoints use JSON for request/response bodies and follow RESTful conventions.

**Base URL**: `http://localhost:8000/api/v1`  
**Content-Type**: `application/json`  
**Error Format**: HTTP 422 with `{ "error": "...", "error_code": "..." }`

---

## Authentication

No authentication required for local development. For production deployment, consider API key authentication via `X-API-Key` header.

---

## Endpoints

### Create Game

**POST** `/games`

Create a new game with two players.

**Request Body**:
```json
{
  "player_0_name": "Agent Alpha",
  "player_1_name": "Agent Beta",
  "format": "competitive",
  "starting_life": 20,
  "random_seed": 12345
}
```

**Response** (200 OK):
```json
{
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "created_at": "2026-03-20T12:00:00Z",
    "turn": 1,
    "step": "untap",
    "active_player": 0,
    "players": {
      "0": {
        "id": 0,
        "name": "Agent Alpha",
        "life": 20
      },
      "1": {
        "id": 1,
        "name": "Agent Beta",
        "life": 20
      }
    }
  }
}
```

**Error Responses**:
- `422 UnprocessableEntity`: Invalid player names (empty, too long)
- `422 UnprocessableEntity`: Invalid starting life (< 1 or > 40)

---

### Get Game State

**GET** `/games/{game_id}`

Retrieve the current game state.

**Path Parameters**:
- `game_id` (string, required): UUID of the game

**Response** (200 OK):
```json
{
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "turn": 1,
    "step": "draw",
    "phase": "precombat_main",
    "active_player": 0,
    "priority": 0,
    "players": {
      "0": {
        "id": 0,
        "name": "Agent Alpha",
        "life": 20,
        "deck_size": 47,
        "hand_size": 5,
        "graveyard_size": 0,
        "exile_size": 0
      },
      "1": {
        "id": 1,
        "name": "Agent Beta",
        "life": 20,
        "deck_size": 47,
        "hand_size": 5,
        "graveyard_size": 0,
        "exile_size": 0
      }
    },
    "battlefield": [],
    "stack": [],
    "round_of_sbas": false,
    "round_of_triggers": false
  }
}
```

**Error Responses**:
- `404 NotFound`: Game not found

---

### Take Game Action

**POST** `/games/{game_id}/actions`

Execute a game action (cast spell, activate ability, pass priority, etc.).

**Path Parameters**:
- `game_id` (string, required): UUID of the game

**Request Body**:
```json
{
  "action_type": "cast_spell",
  "card_id": "43d2d6a4-a3d4-4f0d-9b7e-1e8f5c6d7e8f",
  "target_player": null,
  "targets": [],
  "value": null,
  "mode": null,
  "dry_run": false
}
```

**Action Types**:

| Action Type | Description | Required Fields |
|-------------|-------------|-----------------|
| `cast_spell` | Cast a spell from hand | `card_id`, `target_player` (optional) |
| `activate_ability` | Activate an ability | `card_id`, `value` (if applicable) |
| `play_land` | Play a land from hand | `land_id` |
| `pass_priority` | Pass priority without action | none |
| `take_action` | Generic action with custom type | `action_type`, `details` |
| `surrender` | Surrender the game | none |
| `concede` | Concede the game | none |

**Response** (200 OK):
```json
{
  "data": {
    "action_id": "action-123456",
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "action_type": "cast_spell",
    "status": "resolved",
    "stack_item_id": "stack-item-789",
    "game_state": {
      "turn": 1,
      "step": "draw",
      "priority": 1,
      "stack": [
        {
          "id": "stack-item-789",
          "source_type": "spell",
          "source_id": "43d2d6a4-a3d4-4f0d-9b7e-1e8f5c6d7e8f",
          "controller": 0,
          "targets": [],
          "resolved": false
        }
      ]
    }
  }
}
```

**Error Responses**:
- `422 UnprocessableEntity`: Invalid action type
- `422 UnprocessableEntity`: Card not in player's hand
- `422 UnprocessableEntity`: Insufficient mana
- `422 UnprocessableEntity`: Invalid target
- `422 UnprocessableEntity`: Can't take action at this time (wrong priority)
- `422 UnprocessableEntity`: Action not legal in current step/phase

---

### Handle Choice

**POST** `/games/{game_id}/choices`

Handle a choice the game engine needs from a player (replacement effects, modal spells, etc.).

**Path Parameters**:
- `game_id` (string, required): UUID of the game

**Request Body**:
```json
{
  "choice_id": "choice-abc123",
  "player_id": 0,
  "choice_type": "replacement_effect",
  "choice_value": {
    "apply_effect": true,
    "effect_id": "damage-prevention-1"
  }
}
```

**Response** (200 OK):
```json
{
  "data": {
    "choice_id": "choice-abc123",
    "status": "resolved",
    "game_state": {
      "turn": 1,
      "step": "draw",
      "priority": 0
    }
  }
}
```

**Error Responses**:
- `422 UnprocessableEntity`: Invalid choice ID
- `422 UnprocessableEntity`: Wrong player (not their choice)
- `422 UnprocessableEntity`: Choice already resolved

---

### Export Training Data

**GET** `/games/{game_id}/export`

Export training data for a completed game.

**Path Parameters**:
- `game_id` (string, required): UUID of the game

**Query Parameters**:
- `format` (string, optional): `jsonl` (default) or `json`
- `data_type` (string, optional): `snapshots`, `transcripts`, `rules_qa`, `outcomes`, or `all` (default: `all`)

**Response** (200 OK):
```
Content-Type: application/x-jsonlines

{"type": "snapshot", "game_id": "...", "turn": 1, ...}
{"type": "snapshot", "game_id": "...", "turn": 1, ...}
{"type": "transcript", "game_id": "...", "event": "..."}
{"type": "outcome", "game_id": "...", "winner": 0, ...}
```

**Error Responses**:
- `404 NotFound`: Game not found
- `422 UnprocessableEntity`: Game not completed (only completed games can be exported)

---

### Get Training Data (MongoDB)

**GET** `/export/{data_type}/{game_id}`

Retrieve training data from MongoDB export.

**Path Parameters**:
- `data_type` (string): `snapshots`, `transcripts`, `rules_qa`, `outcomes`
- `game_id` (string): UUID of the game

**Response** (200 OK):
```json
{
  "data": [
    {
      "game_id": "550e8400-e29b-41d4-a716-446655440000",
      "turn": 1,
      "step": "draw",
      "game_state": {...}
    },
    ...
  ]
}
```

**Error Responses**:
- `404 NotFound`: No training data found for this game
- `400 BadRequest`: Invalid data_type

---

## Request Models

### CreateGameRequest

```python
class CreateGameRequest(BaseModel):
    player_0_name: str = Field(..., min_length=1, max_length=50)
    player_1_name: str = Field(..., min_length=1, max_length=50)
    format: str = "competitive"
    starting_life: int = Field(default=20, ge=1, le=40)
    random_seed: Optional[int] = None
```

### GameActionRequest

```python
class GameActionRequest(BaseModel):
    action_type: str
    card_id: Optional[str] = None
    land_id: Optional[str] = None
    target_player: Optional[int] = None
    targets: List[str] = []
    value: Optional[Any] = None
    mode: Optional[str] = None
    dry_run: bool = False
    
    # Generic action support
    details: Optional[Dict[str, Any]] = None
    
    # Validation
    model_validator(mode='after')
    def validate_action(self):
        if self.action_type == 'cast_spell' and not self.card_id:
            raise ValueError('card_id required for cast_spell')
        if self.action_type == 'play_land' and not self.land_id:
            raise ValueError('land_id required for play_land')
        if self.action_type in ['surrender', 'concede', 'pass_priority']:
            if self.card_id or self.targets or self.value:
                raise ValueError('No card/target/value allowed for this action')
        return self
```

### ChoiceRequest

```python
class ChoiceRequest(BaseModel):
    choice_id: str
    player_id: int
    choice_type: str
    choice_value: Dict[str, Any]
```

---

## Error Response Format

All errors follow this structure:

```json
{
  "error": "Human-readable error message",
  "error_code": "SNAKE_CASE_ERROR_CODE",
  "details": {
    "field": "Optional field-specific details"
  }
}
```

**Error Codes**:
- `INVALID_ACTION_TYPE`: Action type not recognized
- `CARD_NOT_IN_HAND`: Card not found in player's hand
- `INSUFFICIENT_MANA`: Player doesn't have enough mana
- `INVALID_TARGET`: Target is illegal
- `WRONG_PRIORITY`: Not this player's priority
- `ILLEGAL_ACTION_IN_STEP`: Can't do this in current step/phase
- `GAME_NOT_ACTIVE`: Game is not in active state
- `GAME_NOT_COMPLETED`: Game must be completed to export
- `CHOICE_NOT_FOUND`: Choice ID doesn't exist
- `CHOICE_ALREADY_RESOLVED`: Choice already handled
- `INVALID_CHOICE_VALUE`: Choice value doesn't match expected format

---

## Rate Limiting

For local development, no rate limiting. For production:
- 100 requests/second per IP
- 1000 requests/minute per IP

---

## Versioning

API version is in URL path (`/api/v1`). Breaking changes will increment version (`/api/v2`).

---

## OpenAPI Specification

Auto-generated OpenAPI 3.0 spec available at `/docs` (Swagger UI) and `/openapi.json`.

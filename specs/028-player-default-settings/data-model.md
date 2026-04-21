# Data Model: Player Default Settings

**Feature**: 028-player-default-settings
**Date**: 2026-04-20

## Entity: PlayerTypeDefaults

Represents the default configuration for a specific player type.

### MongoDB Document Schema

```json
{
  "_id": "human",
  "player_type": "human",
  "settings": {
    "auto_tap": true,
    "confirm_combat": false
  },
  "updated_at": "2026-04-20T12:00:00Z"
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `_id` | string | Yes | Same as `player_type`. Used as primary key to guarantee uniqueness. |
| `player_type` | string | Yes | One of `human`, `ai`, `heuristic`. |
| `settings` | object | Yes | Player-type-specific settings payload. Structure varies by type (see below). |
| `updated_at` | ISO-8601 datetime | Yes | Last modification timestamp. |

### Validation Rules

- `player_type` must be one of `human`, `ai`, `heuristic`.
- `settings` must conform to the Pydantic model for the given `player_type`.
- Unknown keys in `settings` are rejected at write time.

### Index

```python
# Unique index on player_type (already enforced by _id, but explicit index is defensive)
await collection.create_index("player_type", unique=True)
```

---

## Settings Payloads by Player Type

### Human Player Settings

```python
class HumanPlayerSettings(BaseModel):
    auto_tap: bool = True
    confirm_combat: bool = False
    # Future: theme, sound_enabled, card_size, etc.
```

### AI (LLM) Player Settings

```python
class AiPlayerSettings(BaseModel):
    base_url: str = ""
    model: str = ""
    enable_thinking: bool | None = None
    # Future: temperature, max_tokens, system_prompt, etc.
```

### Heuristic Player Settings

```python
class HeuristicPlayerSettings(BaseModel):
    personality: AiPersonalityProfile = Field(default_factory=lambda: AiPersonalityProfile.DEFAULT)
    # Future: depth_limit, evaluation_weights, etc.
```

---

## Entity: PlayerSettings (Runtime)

At game creation, the merged result of request values + defaults becomes the effective `PlayerSettings` for that player. This is **not** persisted to MongoDB; it lives only in-memory for the duration of the game.

### Merge Rules

1. Start with defaults for the player's type (if any exist in MongoDB).
2. Overlay any values explicitly provided in the game creation request.
3. The resulting dict/model is passed to `GameManager.create_game` or the AI client.

---

## Relationships

```
PlayerTypeDefaults (1) ──settings──> PlayerSettings (N per game)
```

- One `PlayerTypeDefaults` document per player type.
- Each game creates two `PlayerSettings` instances (one per player), derived from the relevant `PlayerTypeDefaults`.
- `PlayerSettings` are independent once created; updating `PlayerTypeDefaults` does not affect existing games.

## State Transitions

No state machine. Documents are created, updated, or deleted. No lifecycle beyond that.

## Data Integrity

- `_id` = `player_type` ensures exactly one document per player type.
- `updated_at` is set server-side on every write.
- Validation occurs at the API layer before MongoDB write.

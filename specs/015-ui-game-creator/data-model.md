# Data Model: UI Game Creator

**Branch**: `015-ui-game-creator` | **Date**: 2026-03-23

## Entities

### AIPlayerConfig (backend request sub-model)

Represents one player's configuration in a `POST /ai-game` request.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Player display name (must be unique within the request) |
| `player_type` | `"llm" \| "heuristic"` | yes | Decision engine |
| `base_url` | string | when llm | LLM endpoint base URL (e.g. `http://localhost:11434/v1`) |
| `model` | string | when llm | Model identifier (e.g. `devstral`) |

**Validation**: `base_url` and `model` are required when `player_type == "llm"`. Names must be non-empty and unique across the two players.

---

### AIGameRequest (backend request model — `POST /ai-game` body)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `player1` | AIPlayerConfig | yes | — | First player config |
| `player2` | AIPlayerConfig | yes | — | Second player config |
| `deck1` | list[string] | no | `[]` (use default) | Card names for player 1's deck |
| `deck2` | list[string] | no | `[]` (use default) | Card names for player 2's deck |
| `format` | `"standard" \| "commander"` | no | `"standard"` | Game format |
| `commander1` | string \| null | when commander | null | Commander name for player 1 |
| `commander2` | string \| null | when commander | null | Commander name for player 2 |
| `verbose` | bool | no | `false` | Enable play-by-play logging |
| `max_turns` | int | no | `200` | Maximum turns before forced end |
| `debug` | bool | no | `false` | Enable debug panel and AI prompt capture |
| `observer_url` | string \| null | no | null | Observer AI endpoint (used when debug=true) |
| `observer_model` | string \| null | no | null | Observer AI model |

**Validation**:
- `commander1` and `commander2` required when `format == "commander"`
- Both player names must be non-empty strings
- Player names must differ

---

### AIGameResponse (backend response model)

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | string | UUID of the newly created game |

---

## Frontend State

### CreateGameFormState (client-only, not persisted)

Mirrors `AIGameRequest` with additional UI state:

| Field | Type | Notes |
|-------|------|-------|
| `player1` | PlayerFormState | |
| `player2` | PlayerFormState | |
| `deck1Text` | string | Raw comma-separated input; split on submit |
| `deck2Text` | string | Raw comma-separated input; split on submit |
| `format` | `"standard" \| "commander"` | |
| `commander1` | string | |
| `commander2` | string | |
| `verbose` | bool | |
| `maxTurns` | number | |
| `debug` | bool | |
| `observerUrl` | string | |
| `observerModel` | string | |
| `isSubmitting` | bool | UI loading state |
| `error` | string \| null | Server or validation error message |

### PlayerFormState

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | |
| `playerType` | `"llm" \| "heuristic"` | |
| `baseUrl` | string | Shown only when playerType == "llm" |
| `model` | string | Shown only when playerType == "llm" |

## Relationships

- `AIGameRequest` → creates one `GameState` (via existing `GameManager.create_game()`)
- `AIGameRequest` → starts one background `GameLoop` thread per game
- `AIGameResponse.game_id` → used by frontend to navigate to `/game/{game_id}`

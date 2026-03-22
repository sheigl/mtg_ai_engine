# API Contracts: Debug Log Endpoints

**Feature**: 011-observer-ai-commentary
**Router prefix**: `/game/{game_id}/debug`
**Response envelope**: `{"data": ...}` (matching existing API convention)

---

## POST `/game/{game_id}/debug/entry`

Creates a new debug entry in the game's debug log. Called by the AI client when a prompt is sent (before the LLM responds).

**Request Body** (`application/json`):
```json
{
  "entry_id": "550e8400-e29b-41d4-a716-446655440000",
  "entry_type": "prompt_response",
  "source": "Llama",
  "turn": 3,
  "phase": "precombat_main",
  "step": "main",
  "timestamp": 1742600000.123,
  "prompt": "=== MTG Game — Turn 3 | precombat_main / main ===\n...",
  "response": "",
  "is_complete": false
}
```

**Responses**:
- `200 OK` → `{"data": {"entry_id": "550e8400-..."}}`
- `404 Not Found` → `{"error": "Game not found", "error_code": "GAME_NOT_FOUND"}`
- `422 Unprocessable Entity` → validation error

---

## PATCH `/game/{game_id}/debug/entry/{entry_id}`

Appends streaming tokens to an in-progress `prompt_response` entry. Called repeatedly as the LLM streams its response; called once with `is_complete: true` on the final chunk.

**Request Body** (`application/json`):
```json
{
  "response_chunk": " I should cast Llanowar Elves",
  "is_complete": false
}
```

**Responses**:
- `200 OK` → `{"data": {"entry_id": "550e8400-...", "is_complete": false}}`
- `404 Not Found` → game or entry not found

---

## GET `/game/{game_id}/debug`

Returns the full debug log for a completed or paused game. Used for historical game viewing.

**Response** `200 OK`:
```json
{
  "data": {
    "game_id": "83cb23ac-fbba-47a1-a715-57d3127bf3bd",
    "entries": [
      {
        "entry_id": "550e8400-...",
        "entry_type": "prompt_response",
        "source": "Llama",
        "turn": 1,
        "phase": "precombat_main",
        "step": "main",
        "timestamp": 1742600000.0,
        "prompt": "=== MTG Game — Turn 1 ...",
        "response": "{\"action_index\": 2, \"reasoning\": \"Playing Forest first.\"}",
        "is_complete": true
      },
      {
        "entry_id": "660e8400-...",
        "entry_type": "commentary",
        "source": "Observer AI",
        "turn": 1,
        "phase": "precombat_main",
        "step": "main",
        "timestamp": 1742600002.5,
        "prompt": "Analyze this MTG play ...",
        "response": "{\"rating\": \"good\", \"explanation\": \"...\", \"alternative\": null}",
        "is_complete": true,
        "rating": "good",
        "explanation": "Playing a Forest on turn 1 is the correct land-drop; no better alternative exists.",
        "alternative": null
      }
    ]
  }
}
```

---

## GET `/game/{game_id}/debug/stream`

Server-Sent Events stream. The frontend connects when the debug panel is enabled during a live game. Every new or patched `DebugEntry` is pushed as a `data:` event. A final `event: game_over` is sent when the game ends so the frontend knows to stop listening.

**Response**: `text/event-stream`

**Event format** (each entry):
```
data: {"entry_id":"550e8400-...","entry_type":"prompt_response","source":"Llama","turn":1,...}

```

**Game-over event**:
```
event: game_over
data: {"game_id":"83cb23ac-..."}

```

**Connection lifecycle**:
1. Client connects with `EventSource('/game/{id}/debug/stream')`
2. Server replays any entries already in the log (for late-connecting clients)
3. Server pushes new entries/patches as they arrive
4. On game end, server sends `game_over` event and closes the stream
5. Client switches to `GET /game/{id}/debug` for the static historical view

**Notes**:
- No authentication required (internal dev tool)
- Connection timeout: server sends a `:keepalive` comment every 15s to prevent proxy timeouts
- If the game does not exist: HTTP 404 before the stream is established

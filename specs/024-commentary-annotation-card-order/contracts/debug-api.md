# API Contracts: Debug Entry Annotations & Rating Override

## New Endpoints

### PATCH /game/{game_id}/debug/entry/{entry_id}/annotate

Sets, updates, or clears the player annotation on a debug entry.

**Request body**:
```json
{ "text": "string or null" }
```

- `text`: The annotation text. `null` or empty string deletes the annotation.
- Whitespace-only strings are rejected with 422.
- Entry must exist; returns 404 if not found.
- Entry must be `is_complete: true`; returns 409 if still streaming.

**Response** (200):
```json
{
  "data": {
    "entry_id": "string",
    "player_annotation": "string or null"
  }
}
```

**SSE effect**: Emits an update event on `/game/{game_id}/debug/stream` with the full updated entry so the frontend panel refreshes automatically.

---

### PATCH /game/{game_id}/debug/entry/{entry_id}/rerate

Sets or clears the player rating override on an observer commentary entry.

**Request body**:
```json
{ "rating": "good" | "acceptable" | "suboptimal" | null }
```

- `null` removes the override (reverts display to original AI rating).
- Only valid for entries with `entry_type: "commentary"` — returns 422 for prompt_response entries.
- The original `rating` field is never modified.

**Response** (200):
```json
{
  "data": {
    "entry_id": "string",
    "rating": "string",
    "player_rating_override": "string or null"
  }
}
```

**SSE effect**: Emits an update event on `/game/{game_id}/debug/stream` with the full updated entry.

---

## Modified Existing Responses

### GET /game/{game_id}/debug

All `DebugEntry` objects now include two additional nullable fields:

```json
{
  "entry_id": "...",
  "entry_type": "commentary | prompt_response",
  "source": "...",
  "turn": 1,
  "phase": "...",
  "step": "...",
  "timestamp": 0.0,
  "prompt": "...",
  "response": "...",
  "is_complete": true,
  "rating": "good | acceptable | suboptimal | null",
  "explanation": "... | null",
  "alternative": "... | null",
  "thinking": "... | null",
  "player_annotation": "... | null",
  "player_rating_override": "good | acceptable | suboptimal | null"
}
```

### GET /export/{game_id}/game-log

The plain-text game log now includes observer commentary and AI reasoning entries merged into the turn timeline, with player annotations and rating overrides rendered inline. Entries where all player fields are `null` are formatted identically to the current log (no regression for existing consumers).

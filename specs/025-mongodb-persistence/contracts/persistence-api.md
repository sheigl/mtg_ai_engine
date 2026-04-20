# API Contracts: MongoDB Persistence (Feature 025)

## New Endpoints

### GET /games/records

Query persisted game records for training pipelines.

**Query parameters**:

| Parameter         | Type    | Default | Description |
|-------------------|---------|---------|-------------|
| `format`          | string  | (all)   | Filter by game format: `standard` or `commander` |
| `has_human_player`| boolean | (all)   | Filter games with a human player: `true` or `false` |
| `is_complete`     | boolean | `true`  | Filter completed games |
| `from`            | ISO8601 | (none)  | Filter games created at or after this timestamp |
| `to`              | ISO8601 | (none)  | Filter games created before this timestamp |
| `limit`           | int     | `100`   | Max records returned (1–1000) |
| `fields`          | string  | (all except snapshots) | Comma-separated top-level fields to include |

**Response** (200):
```json
{
  "data": {
    "count": 42,
    "records": [
      {
        "game_id": "string",
        "format": "standard",
        "player_1": { "name": "string", "type": "human|ai" },
        "player_2": { "name": "string", "type": "human|ai" },
        "has_human_player": true,
        "created_at": "2026-04-19T10:00:00Z",
        "completed_at": "2026-04-19T10:25:00Z",
        "is_complete": true,
        "outcome": {
          "winner": "string",
          "win_condition": "life|mill|poison|concede",
          "total_turns": 12
        },
        "transcript": [ ... ],
        "debug_entries": [ ... ],
        "rules_qa": [ ... ]
      }
    ]
  }
}
```

**Error responses**:
- `503 Service Unavailable` — MongoDB not configured or unreachable

---

### GET /games/records/{game_id}

Retrieve the full persisted record for a single game.

**Response** (200):
```json
{
  "data": {
    "game_id": "string",
    "format": "standard",
    "player_1": { "name": "string", "type": "human|ai" },
    "player_2": { "name": "string", "type": "human|ai" },
    "has_human_player": true,
    "created_at": "2026-04-19T10:00:00Z",
    "completed_at": "2026-04-19T10:25:00Z",
    "is_complete": true,
    "outcome": { ... },
    "transcript": [ ... ],
    "snapshots": [ ... ],
    "debug_entries": [ ... ],
    "rules_qa": [ ... ]
  }
}
```

**Error responses**:
- `404 Not Found` — game record not found in MongoDB
- `503 Service Unavailable` — MongoDB not configured

---

### GET /health (modified)

The existing health endpoint is extended to report MongoDB connectivity.

**Response** (200 — MongoDB configured and reachable):
```json
{
  "status": "ok",
  "mongodb": "connected"
}
```

**Response** (200 — MongoDB not configured):
```json
{
  "status": "ok",
  "mongodb": "not_configured"
}
```

**Response** (200 — MongoDB configured but unreachable):
```json
{
  "status": "ok",
  "mongodb": "error"
}
```

---

## Modified Existing Endpoints

### GET /export/{game_id}/game-log (modified behavior)

When MongoDB is configured and the game record exists in storage, the game log is generated from the persisted data rather than in-memory. This ensures the log reflects any player annotations or rating overrides saved after the game ended.

When MongoDB is unavailable, behavior falls back to current in-memory generation (no visible change for end user, but log may not reflect post-game annotations).

No change to the response format or schema.

---

## Internal: PATCH /game/{game_id}/debug/entry/{entry_id}/annotate (side effect)

When MongoDB is configured, in addition to updating the in-memory `DebugEntry`, the persisted document in MongoDB is updated using `$set` with a positional array filter targeting the `entry_id`. The `rating` field is never modified.

Same applies to `PATCH .../rerate`.

---

## Environment Configuration

```bash
MONGODB_URL=mongodb://localhost:27017/mtg_training
```

The database name is parsed from the URL path. If not set, all MongoDB functionality is silently disabled.

**Optional: custom database and collection**:
```bash
MONGODB_DATABASE=mtg_training   # override database name (default: parsed from URL)
MONGODB_COLLECTION=games        # override collection name (default: "games")
```

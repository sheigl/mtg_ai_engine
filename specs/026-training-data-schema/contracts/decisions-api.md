# API Contract: Decisions Endpoints (Feature 026)

## Changed: GET /game/{game_id}/legal-actions

**Change**: Response now includes `snapshot_id`.

```json
{
  "data": {
    "priority_player": "Alice",
    "phase": "main",
    "step": "precombat_main",
    "legal_actions": [...],
    "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
    "is_paused": false,
    "is_game_over": false,
    "winner": null
  }
}
```

---

## Changed: POST /game/{game_id}/debug/entry

**Change**: `DebugEntry` body now accepts two new optional fields.

```json
{
  "entry_id": "uuid",
  "entry_type": "prompt_response",
  "source": "Alice",
  "snapshot_id": "550e8400-...",
  "related_entry_id": null,
  "turn": 3,
  "phase": "main",
  "step": "precombat_main",
  "timestamp": 1713600000.0,
  "prompt": "...",
  "response": "",
  "is_complete": false
}
```

Both `snapshot_id` and `related_entry_id` are optional (`null` if omitted). Existing clients without these fields continue to work.

---

## New: GET /games/records/{game_id}/decisions

Return all decision documents for a completed game, sorted by `sequence_number`.

**Request**:
```
GET /games/records/{game_id}/decisions
```

**Response** (200):
```json
{
  "data": {
    "game_id": "game-uuid",
    "decisions": [
      {
        "snapshot_id": "...",
        "sequence_number": 1,
        "turn": 1,
        "phase": "main",
        "step": "precombat_main",
        "active_player": "Alice",
        "board_state": { ... },
        "legal_actions": [ ... ],
        "action_taken": { ... },
        "action_taken_by": "Alice",
        "llm_reasoning": { ... } | null,
        "observer_evaluation": { ... } | null,
        "outcome_context": { ... } | null,
        "created_at": "2026-04-20T10:01:23Z"
      }
    ],
    "count": 47
  }
}
```

**Error** (404): Game not found in `decisions` collection.
**Error** (503): MongoDB not configured.

---

## Changed: GET /games/records

Now queries only `games` collection (metadata only — no embedded arrays). The `fields` query parameter still applies but `transcript`, `snapshots`, `debug_entries` are no longer valid field names (those collections are queried separately).

---

## Changed: GET /games/records/{game_id}

Returns `games` document metadata only. The embedded `transcript`, `snapshots`, and `debug_entries` arrays are removed from the response.

---

## Unchanged: PATCH /game/{game_id}/debug/entry/{entry_id}/annotate

Internally: now updates `decisions.llm_reasoning.player_annotation` instead of the embedded array in `games`. Response contract unchanged.

## Unchanged: PATCH /game/{game_id}/debug/entry/{entry_id}/rerate

Internally: now updates `decisions.llm_reasoning.player_rating_override`. Response contract unchanged.

# API Contract: Game Observer Web UI

**Feature**: 010-game-observer-ui
**Date**: 2026-03-21

## Overview

The observer UI requires one new endpoint and consumes several existing endpoints. All endpoints are read-only GET requests — the observer never modifies game state.

---

## New Endpoint

### `GET /game` — List Active Games

Returns a summary of all currently active games for the game list view.

**Request**: No parameters.

**Response** (200 OK):
```json
{
  "data": [
    {
      "game_id": "a1b2c3d4-...",
      "player1_name": "Alice",
      "player2_name": "Bob",
      "format": "standard",
      "turn": 5,
      "phase": "combat",
      "step": "declare_attackers",
      "is_game_over": false,
      "winner": null
    },
    {
      "game_id": "e5f6g7h8-...",
      "player1_name": "Carol",
      "player2_name": "Dave",
      "format": "commander",
      "turn": 12,
      "phase": "postcombat_main",
      "step": "main",
      "is_game_over": false,
      "winner": null
    }
  ]
}
```

**Response** (200 OK — no active games):
```json
{
  "data": []
}
```

**Notes**:
- Returns an empty list when no games are running (FR-004 handles this in the UI as "No active games" message).
- Completed games that haven't been deleted yet may appear with `is_game_over: true`.
- The list is not paginated — the engine typically runs 1–5 concurrent games.
- Polling interval: every 5 seconds (FR-001).

---

## Existing Endpoints Used by the Observer

### `GET /game/{game_id}` — Full Game State

Returns the complete game state for the board view. This is the primary data source for the live board.

**Polling interval**: every 1.5 seconds (to meet FR-002's 2-second requirement).

**Optimization**: Compare `state_hash` from the response to the previously received hash. If unchanged, skip re-rendering.

**Response structure**: See existing API documentation. Returns full `GameState` wrapped in `{"data": {...}}`.

**Error handling**:
- **404**: Game not found (game was deleted/ended) → show "Game ended" message.
- **Network error**: Show reconnection indicator, retry with exponential backoff (FR-009).

### `GET /export/{game_id}/transcript` — Play-by-Play Events

Returns all transcript entries for the action log sidebar.

**Polling interval**: every 2 seconds.

**Optimization**: Track the highest `seq` number received. On each poll, filter client-side to only display entries with `seq > lastSeenSeq`. This avoids re-rendering the entire log on each poll.

**Response structure**:
```json
[
  {
    "seq": 1,
    "event_type": "phase_change",
    "description": "Turn 1: entering beginning — untap",
    "data": {"turn": 1, "phase": "beginning", "step": "untap", "active_player": "Alice"},
    "turn": 1,
    "phase": "beginning",
    "step": "untap"
  },
  {
    "seq": 2,
    "event_type": "cast",
    "description": "Alice casts Lightning Bolt targeting Bob",
    "data": {"player": "Alice", "card_name": "Lightning Bolt", "targets": ["Bob"]},
    "turn": 1,
    "phase": "precombat_main",
    "step": "main"
  }
]
```

**Event types displayed in action log** (filtered for readability — skip noisy events):
- `cast` — "Alice casts Lightning Bolt"
- `resolve` — "Lightning Bolt resolves"
- `zone_change` — "Mountain moves from hand to battlefield"
- `damage` — "Lightning Bolt deals 3 damage to Bob"
- `attack` — "Alice attacks with Grizzly Bears"
- `block` — "Bob blocks Grizzly Bears with Wall of Omens"
- `life_change` — "Bob loses 3 life from Lightning Bolt"
- `game_end` — "Game over. Winner: Alice"
- `trigger` — "Triggered ability from Soul Warden: gain 1 life"
- `draw` — "Alice draws a card"

**Event types to skip** (too noisy for observer):
- `phase_change` — Shown via phase tracker component, not log
- `priority_grant` — Internal engine detail, not meaningful to observer
- `choice_made` — Usually redundant with the resulting action
- `sba` — State-based actions are reflected in zone changes

### `GET /game/{game_id}/stack` — Current Stack Contents

Returns the current stack. Can be used as an alternative to extracting `stack` from the full game state.

**Note**: Since the full game state from `GET /game/{game_id}` already includes `stack`, this endpoint may not be needed separately. Use the main game state poll for stack data.

---

## UI Static File Serving

### `GET /ui/{path}` — Serve Frontend SPA

FastAPI serves the built React SPA from `frontend/dist/`.

**Routing rules**:
- `/ui/assets/*` → Serve static files (JS, CSS, fonts) directly from `frontend/dist/assets/`
- `/ui/*` (any other path) → Serve `frontend/dist/index.html` (SPA catch-all for React Router)
- API routes (`/game/*`, `/export/*`, `/deck/*`, `/health`) → Unchanged, handled by existing routers

**CORS**: Not needed — frontend and API are served from the same origin.

---

## Error Handling Contract

All error responses follow the existing engine pattern:

```json
{
  "detail": {
    "error": "Human-readable error message",
    "error_code": "MACHINE_READABLE_CODE"
  }
}
```

| Scenario | HTTP Status | Error Code | UI Behavior |
|----------|-------------|------------|-------------|
| Game not found | 404 | GAME_NOT_FOUND | Show "Game ended" message |
| Server error | 500 | INTERNAL_ERROR | Show reconnection indicator |
| Network timeout | N/A | N/A | Show reconnection indicator, retry |
| Game deleted mid-view | 404 on next poll | GAME_NOT_FOUND | Show "Game ended" gracefully |

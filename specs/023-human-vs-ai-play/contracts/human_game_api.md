# API Contract: Human Game Endpoints

**Branch**: `023-human-vs-ai-play` | **Date**: 2026-04-18

## New Endpoints

### POST /human-game

Creates a new game with mixed player types (at least one human seat) and starts the hybrid game loop.

**Request Body** (`application/json`):
```json
{
  "player1_type": "human",
  "player2_type": "heuristic",
  "player1_deck": ["Forest", "Forest", "Llanowar Elves", "..."],
  "player2_deck": ["Mountain", "Mountain", "Lightning Bolt", "..."],
  "player1_name": "You",
  "player2_name": "Heuristic Bot",
  "format": "standard",
  "ai_model": "gpt-4o-mini",
  "observer_model": "gpt-4o-mini",
  "observer_enabled": true
}
```

**Response 200** (`application/json`):
```json
{
  "game_id": "abc123",
  "human_player_name": "You",
  "redirect_url": "/ui/human-game/abc123"
}
```

**Validation errors (422)**:
- No seat is `"human"`
- Both seats are `"human"` (not supported in v1)
- `player1_deck` or `player2_deck` is empty

---

## Existing Endpoints Used by Human Player (no changes)

All existing game action endpoints are used directly by the frontend for human player actions. The engine validates `priority_holder` on each action, so no changes are needed.

### GET /game/{game_id}
Returns full `GameState`. Frontend polls every 1500ms.

### GET /game/{game_id}/legal-actions
Returns `{ priority_player, phase, step, legal_actions, is_paused, is_game_over, winner }`.
Frontend polls every 750ms when `is_my_turn` to keep action highlights fresh.

### POST /game/{game_id}/pass
Pass priority (no request body needed beyond game_id in path).

### POST /game/{game_id}/play-land
```json
{ "card_id": "uuid-of-land-card" }
```

### POST /game/{game_id}/cast
```json
{
  "card_id": "uuid-of-spell",
  "targets": ["permanent-id-or-player-name"],
  "mana_payment": null,
  "x_value": null,
  "face_index": 0
}
```
Note: `mana_payment: null` triggers auto-tap logic server-side.

### POST /game/{game_id}/declare-attackers
```json
{
  "attacker_ids": ["permanent-id-1", "permanent-id-2"]
}
```

### POST /game/{game_id}/declare-blockers
```json
{
  "assignments": [
    { "blocker_id": "permanent-id-3", "attacker_id": "permanent-id-1" }
  ]
}
```

### POST /game/{game_id}/activate
```json
{
  "permanent_id": "uuid",
  "ability_index": 0,
  "targets": [],
  "mana_payment": null
}
```

### POST /game/{game_id}/mulligan
```json
{ "keep": true }
```

---

## Frontend Route Contract

| Route | Component | Description |
|-------|-----------|-------------|
| `/ui/` | `GameList.tsx` (existing) | Game list; will add "New Human Game" button |
| `/ui/game/:gameId` | `GameBoard.tsx` (existing, observer) | AI vs AI observer view |
| `/ui/human-game/:gameId` | `HumanGameBoard.tsx` (new) | Human interactive game board |
| `/ui/human-game/create` | `HumanGameCreator.tsx` (new) | Game creation form for human games |

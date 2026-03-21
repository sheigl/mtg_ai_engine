# API Contract: Verbose Logging Toggle

**Feature**: 007-play-by-play-log
**Date**: 2026-03-21

## Overview

Two API changes expose verbose logging control to callers:

1. A new `verbose` flag on game creation (`POST /game`)
2. A new toggle endpoint (`POST /game/{game_id}/verbose`)

Verbose output is emitted to the server's log stream (stdout/file via Python logging), not returned in API responses.

---

## Modified Endpoint: POST /game

**Existing endpoint** — one new optional field added to the request body.

### Request Body (addition)

```json
{
  "player1_name": "player_1",
  "player2_name": "player_2",
  "deck1": ["..."],
  "deck2": ["..."],
  "seed": null,
  "verbose": false
}
```

| Field   | Type    | Required | Default | Description                                      |
|---------|---------|----------|---------|--------------------------------------------------|
| verbose | boolean | No       | false   | Enable play-by-play log output for this game     |

### Response

Unchanged from existing contract. Returns the initial `GameState`.

---

## New Endpoint: POST /game/{game_id}/verbose

Toggle verbose logging on or off for an existing game.

### Path Parameters

| Parameter | Type   | Description          |
|-----------|--------|----------------------|
| game_id   | string | ID of the target game |

### Request Body

```json
{
  "enabled": true
}
```

| Field   | Type    | Required | Description                          |
|---------|---------|----------|--------------------------------------|
| enabled | boolean | Yes      | true to enable, false to disable     |

### Success Response — 200 OK

```json
{
  "data": {
    "game_id": "abc-123",
    "verbose_enabled": true
  }
}
```

### Error Responses

| Status | error_code     | Condition                    |
|--------|----------------|------------------------------|
| 404    | GAME_NOT_FOUND | game_id does not exist       |
| 422    | INVALID_BODY   | Request body missing/invalid |

---

## Verbose Output Format (server log)

Verbose output is written to the `mtg_engine.verbose` logger at `INFO` level. When the default logging handler routes to stdout, callers see output like:

```
═══ Turn 1 — player_1 ═══════════════════════════════════
  [Beginning / Untap]
  [Beginning / Draw]
    player_1 draws a card.
  [Pre-combat Main]
    player_1 plays Forest.
    player_1 casts Llanowar Elves.
    Llanowar Elves resolves → enters battlefield under player_1.
  [Combat / Declare Attackers]
    player_1 attacks with Llanowar Elves → player_2.
  [Combat / Combat Damage]
    Llanowar Elves deals 1 damage to player_2. (player_2 life: 19)
  [Ending / Cleanup]

══ GAME OVER — player_1 wins (life_total_zero) ══════════
```

Output is per-game and interleaved with normal application logs unless callers configure separate log handlers.

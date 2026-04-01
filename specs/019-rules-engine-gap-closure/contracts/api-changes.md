# API Contract Changes: Rules Engine Gap Closure (Feature 019)

**Feature**: 019-rules-engine-gap-closure
**Date**: 2026-03-29

---

## Modified Endpoints

### POST /game/{game_id}/cast

**Request body changes** (additions to `CastRequest`):

```json
{
  "card_id": "string",
  "targets": ["string"],
  "mana_payment": {"W": 1, "generic": 2},
  "alternative_cost": "flashback | escape | convoke | delve | improvise | emerge | null",
  "modes_chosen": [1],
  "x_value": 0,
  "kicker_paid": false,
  "from_command_zone": false,
  "from_graveyard": false,

  // NEW FIELDS:
  "convoke_creature_ids": ["perm_id_1", "perm_id_2"],
  "delve_card_ids": ["card_id_in_graveyard"],
  "improvise_artifact_ids": ["artifact_perm_id"],
  "emerge_sacrifice_id": "creature_perm_id_or_null",
  "buyback_paid": false,
  "replicate_count": 0,
  "flashback": false,
  "escape_exile_ids": ["graveyard_card_id_1", "graveyard_card_id_2"],
  "opponent_target": "player_name_or_null"
}
```

**Response**: No changes to response shape.

**New validation errors**:
- `400 CONVOKE_INVALID`: Creature ID in `convoke_creature_ids` not on battlefield, tapped, or has summoning sickness
- `400 DELVE_INVALID`: Card ID in `delve_card_ids` not in player's graveyard
- `400 IMPROVISE_INVALID`: Artifact ID not on battlefield or is tapped
- `400 EMERGE_INVALID`: Creature not on battlefield
- `400 ESCAPE_INSUFFICIENT`: Not enough graveyard cards to satisfy escape exile requirement
- `400 BUYBACK_COST_UNPAID`: Buyback flag set but mana_payment doesn't cover the additional buyback cost
- `400 COMMAND_TAX_INSUFFICIENT`: Cost paid doesn't cover command tax for this commander's cast count

---

## New Endpoints

### POST /game/{game_id}/cycle

Cycle a card from hand.

**Request body**:
```json
{
  "card_id": "string",
  "mana_payment": {"generic": 2}
}
```

**Response**:
```json
{
  "game_state": { ... },
  "cycled_card": "card_name"
}
```

**Errors**:
- `400 CARD_NOT_IN_HAND`
- `400 CARD_NO_CYCLING`
- `400 INSUFFICIENT_MANA`

---

### POST /game/{game_id}/dredge

Choose whether to dredge instead of drawing (called during draw step when pending dredge choices exist).

**Request body**:
```json
{
  "dredge_card_id": "string_or_null"
}
```
- If `dredge_card_id` is null: draw normally instead.
- If set: mill N cards (N from dredge value), return dredge card to hand.

**Errors**:
- `400 CARD_NOT_IN_GRAVEYARD`
- `400 CARD_NO_DREDGE`
- `400 INSUFFICIENT_LIBRARY`: Not enough cards to mill for dredge N
- `400 NO_PENDING_DREDGE`: No draw replacement is pending

---

### POST /game/{game_id}/proliferate

Choose targets for a proliferate effect (called when a proliferate effect is resolving).

**Request body**:
```json
{
  "targets": [
    {"type": "permanent", "id": "perm_id"},
    {"type": "player", "name": "Alice"}
  ]
}
```

**Response**: Updated game state.

**Errors**:
- `400 NO_PENDING_PROLIFERATE`
- `400 INVALID_TARGET`: Target permanent has no counters
- `400 INVALID_PLAYER_TARGET`: Player has no counters

---

## Modified Game State Response

New fields in the game state response body:

```json
{
  "emblems": [
    {
      "id": "uuid",
      "controller": "player_name",
      "source_name": "Jace, the Mind Sculptor",
      "abilities": ["Whenever an opponent draws a card, that player loses 1 life."]
    }
  ]
}
```

---

## Legal Actions Response Changes

New `action_type` values in `GET /game/{game_id}` legal actions:

| action_type | When present | Key fields |
|-------------|-------------|-----------|
| `"cycle"` | Player has cycling cards in hand and can pay cycling cost | `card_id`, `mana_options` |
| `"dredge"` | Player has dredge cards in GY and a draw is pending | `card_id` (the dredge card), description includes dredge N |
| `"proliferate"` | A proliferate effect is resolving | `valid_targets` (permanents/players with counters) |
| `"cast_flashback"` | Player has flashback cards in graveyard they can cast | `card_id`, `from_graveyard: true`, `mana_options` |
| `"cast_escape"` | Player has escape cards in graveyard they can cast | `card_id`, `from_graveyard: true`, description includes exile count |

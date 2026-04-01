# API Contract Changes: Rules Engine Complete Parity (Feature 020)

**Feature**: 020-rules-engine-complete-parity
**Date**: 2026-04-01

---

## Modified Endpoints

### POST /game/{game_id}/cast

**Request body changes** (additions to `CastRequest`):

```json
{
  "card_id": "string",
  "targets": ["string"],
  "mana_payment": {"W": 1, "generic": 2},
  "alternative_cost": "string | null",
  "modes_chosen": [1],
  "x_value": 0,
  "kicker_paid": false,
  "from_command_zone": false,
  "from_graveyard": false,

  "// NEW FIELDS (020)": "",
  "face_index": 0,
  "fuse": false,
  "as_face_down": false,
  "foretell": false,
  "cast_foretold": false,
  "mutate_target_id": "string | null",
  "mutate_on_top": true
}
```

**Response**: No changes to response shape.

**New validation errors**:
- `400 INVALID_FACE_INDEX`: `face_index` out of range for card's faces list
- `400 FUSE_NOT_AVAILABLE`: `fuse=True` but card does not have the fuse keyword
- `400 AFTERMATH_WRONG_ZONE`: Aftermath second half cast attempted from hand (must be from graveyard)
- `400 ADVENTURE_ALREADY_EXILED`: Adventure half cast attempted but the card is already in adventure exile
- `400 MORPH_NOT_AVAILABLE`: `as_face_down=True` but card does not have morph or megamorph
- `400 FORETELL_NOT_YOUR_TURN`: Foretell attempted on opponent's turn
- `400 FORETELL_SAME_TURN`: Cast from foretell attempted on the same turn the card was foretold
- `400 FORETELL_NOT_IN_EXILE`: `cast_foretold=True` but card is not in foretold exile
- `400 MUTATE_INVALID_TARGET`: Mutate target is Human, not a creature, or not controlled by caster
- `400 MUTATE_NO_TARGET`: `mutate_target_id` required for mutate cast
- `400 ILLEGAL_TARGET_HEXPROOF`: Target has hexproof and spell controller is an opponent
- `400 ILLEGAL_TARGET_SHROUD`: Target has shroud
- `400 ILLEGAL_TARGET_PROTECTION`: Target has protection from the spell's quality

### POST /game/{game_id}/activate

**Behavior change**: Before placing the ability on the stack, the engine now checks `is_mana_ability()`. If the ability is a mana ability (produces mana, no target, not a loyalty ability), the ability resolves immediately without going on the stack. The response includes the updated game state with mana added to the pool.

**New validation errors**:
- `400 SPLIT_SECOND_BLOCKS_ABILITY`: A spell with split second is on the stack and the ability is not a mana ability

### POST /game/{game_id}/choice

**Extended choice types**: The existing `/choice` endpoint handles additional choice IDs:

| `choice_id` | Payload | When prompted |
|-------------|---------|---------------|
| `"legend_choice"` | `{"keep_permanent_id": "uuid"}` | Legend rule: choose which legendary permanent to keep |
| `"ward_payment"` | `{"pay": true, "mana_payment": {...}}` or `{"pay": false}` | Ward triggered: pay the ward cost or let the spell be countered |
| `"echo_payment"` | `{"pay": true, "mana_payment": {...}}` or `{"pay": false}` | Echo upkeep: pay echo cost or sacrifice |
| `"blocker_damage_order"` | `{"assignments": [{"target_id": "id", "damage": N}]}` | Manual damage assignment to ordered blockers |
| `"cleanup_discard"` | `{"card_ids": ["id1", "id2"]}` | Cleanup step: choose cards to discard to hand size |

---

## New Endpoints

### POST /game/{game_id}/crew

Crew a Vehicle artifact by tapping creatures.

**Request body**:
```json
{
  "vehicle_id": "permanent_uuid",
  "crew_creature_ids": ["perm_id_1", "perm_id_2"]
}
```

**Response**:
```json
{
  "game_state": { "..." : "..." },
  "vehicle_crewed": true
}
```

**Errors**:
- `400 NOT_A_VEHICLE`: `vehicle_id` does not reference a Vehicle artifact
- `400 INSUFFICIENT_CREW_POWER`: Total power of tapped creatures < crew cost
- `400 CREATURE_NOT_AVAILABLE`: A creature in `crew_creature_ids` is tapped, has summoning sickness, or is not on the battlefield
- `400 SORCERY_SPEED_ONLY`: Crew attempted at instant speed (not player's main phase with empty stack)

---

### POST /game/{game_id}/turn_face_up

Turn a face-down creature face up by paying its morph/megamorph cost. This is a special action (CR 702.36e) that does not use the stack.

**Request body**:
```json
{
  "permanent_id": "permanent_uuid",
  "mana_payment": {"G": 1, "generic": 2}
}
```

**Response**:
```json
{
  "game_state": { "..." : "..." },
  "revealed_card": "card_name",
  "megamorph_counter_added": false
}
```

**Errors**:
- `400 NOT_FACE_DOWN`: Permanent is not face-down
- `400 NOT_CONTROLLER`: Player does not control this permanent
- `400 INSUFFICIENT_MANA`: Payment does not cover the morph cost
- `400 NO_MORPH_COST`: Card does not have morph or megamorph

---

### POST /game/{game_id}/foretell

Exile a card face-down from hand for the foretell cost of {2}.

**Request body**:
```json
{
  "card_id": "card_uuid"
}
```

**Response**:
```json
{
  "game_state": { "..." : "..." },
  "foretold_card": "card_name (face-down)"
}
```

**Errors**:
- `400 CARD_NOT_IN_HAND`: Card is not in the player's hand
- `400 NO_FORETELL`: Card does not have the foretell keyword
- `400 NOT_YOUR_TURN`: Foretell can only be done on the player's own turn
- `400 INSUFFICIENT_MANA`: Player cannot pay {2}

---

## Modified Game State Response

New fields in the game state response body:

```json
{
  "additional_combat_phases": 0,
  "step_skip_flags": {"draw": true},
  "damage_modifiers": [
    {
      "source_permanent_id": "uuid",
      "controller": "Alice",
      "multiplier": 2,
      "applies_to": "all"
    }
  ],
  "pending_legend_choice": {
    "player": "Alice",
    "permanent_ids": ["uuid1", "uuid2"],
    "legend_name": "Thalia, Guardian of Thraben"
  },
  "pending_echo_payment": {
    "player": "Alice",
    "permanent_id": "uuid",
    "echo_cost": "{3}{R}"
  }
}
```

Permanent objects in the battlefield array gain:
```json
{
  "phased_out": false,
  "crewed_until_end_of_turn": false,
  "mutated_cards": []
}
```

ManaPool gains:
```json
{
  "snow": 0,
  "snow_by_color": {}
}
```

PlayerState gains:
```json
{
  "mana_persistence": {
    "colors": [],
    "convert_to_colorless": false
  }
}
```

---

## Legal Actions Response Changes

New `action_type` values in `GET /game/{game_id}` legal actions:

| action_type | When present | Key fields |
|-------------|-------------|-----------|
| `"crew"` | Player controls a Vehicle and has creatures with sufficient total power | `permanent_id` (vehicle), `description` includes crew cost |
| `"turn_face_up"` | Player controls a face-down creature with a morph cost they can pay | `permanent_id`, `mana_options` (morph cost options) |
| `"foretell"` | Player has a foretell card in hand on their turn, can pay {2} | `card_id`, description: "Foretell for {2}" |
| `"cast_foretold"` | Foretold card in exile, can pay foretell cost, not foretold this turn | `card_id`, `mana_options` (foretell cast cost) |
| `"cast_adventure"` | Adventure card in hand (adventure half) or in adventure-exile (creature half) | `card_id`, `face_index`, `from_graveyard` or `description` |
| `"activate_mana_ability"` | Permanent has an untapped mana-producing ability | `permanent_id`, `ability_index` |
| `"mutate"` | Mutate creature in hand, non-Human target on battlefield | `card_id`, `valid_targets` |
| `"cast_split_left"` | Left half of a split card is castable | `card_id`, `face_index=0`, `mana_options` |
| `"cast_split_right"` | Right half of a split card is castable | `card_id`, `face_index=1`, `mana_options` |
| `"cast_fuse"` | Both halves castable and card has fuse | `card_id`, `mana_options` (combined cost) |
| `"play_mdfc_land"` | MDFC back face is a land and player has land drops | `card_id`, `face_index=1` |

---

## Targeting Validation Changes

All targeting endpoints (`/cast`, `/activate`, `/put_trigger`) now enforce:

1. **Hexproof check**: If target permanent has hexproof and the spell/ability controller is an opponent of the permanent's controller, reject.
2. **Shroud check**: If target permanent has shroud, reject regardless of controller.
3. **Protection check**: If target permanent has protection from a quality matching the spell/ability source, reject. Quality matching covers:
   - Color: spell's colors vs protection color
   - Card type: source permanent's types vs protection type
   - CMC: source's CMC vs protection threshold
4. **Ward trigger**: If target permanent has ward and spell/ability controller is an opponent, queue ward trigger on the stack (does not reject the targeting outright — ward is a triggered ability).

These checks are applied in `_validate_targets(game_state, targets, source, controller)` — a new shared validation function called from all targeting endpoints.

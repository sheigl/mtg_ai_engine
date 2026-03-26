# API Contracts: New Engine Endpoints

**Branch**: `017-forge-ai-parity` | **Date**: 2026-03-25

All endpoints follow the existing FastAPI JSON pattern.

---

## POST /game/{game_id}/mulligan

Perform a London mulligan for a player during the pre-game mulligan phase.

**Request Body**: `MulliganRequest`
```json
{
  "player_name": "Alice",
  "keep": false
}
```

**Response** (200):
```json
{
  "kept": false,
  "new_hand_size": 6,
  "hand": [ /* Card objects */ ]
}
```

**Errors**:
- 400 if not in mulligan phase
- 400 if player_name not in game
- 400 if hand size already at 5 (minimum — force keep)

---

## POST /game/{game_id}/activate-loyalty

Activate a planeswalker loyalty ability. Only valid during the controller's main phase when the planeswalker has not activated this turn.

**Request Body**: `ActivateLoyaltyRequest`
```json
{
  "permanent_id": "pw-abc123",
  "ability_index": 0,
  "targets": ["creature-xyz"]
}
```

**Response** (200):
```json
{
  "loyalty_change": 1,
  "new_loyalty": 4,
  "effect_queued": true
}
```

**Errors**:
- 400 if permanent is not a planeswalker
- 400 if loyalty already activated this turn
- 400 if insufficient loyalty for − ability
- 400 if `ability_index` out of range

**Legal Action emitted**: `action_type="activate_loyalty"` with `permanent_id`, `ability_index`, `valid_targets`, `description`.

---

## POST /game/{game_id}/cascade-choice

Resolve a cascade trigger. Called when the engine has exiled cards down to the cascade card and is waiting for the controller's decision.

**Request Body**: `CascadeChoiceRequest`
```json
{
  "player_name": "Alice",
  "card_id": "card-abc",
  "cast": true
}
```

**Response** (200):
```json
{
  "cast": true,
  "card_name": "Lightning Bolt",
  "result": "spell_on_stack"
}
```

**Errors**:
- 400 if no cascade choice pending for this player
- 400 if `card_id` does not match the offered cascade card

**Legal Action emitted**: `action_type="cascade_choice"` with `cascade_card_id`, `card_name`, `description`.

---

## POST /game/{game_id}/cast (extended)

Existing endpoint extended with new `alternative_cost` values. No schema change — `alternative_cost` field already exists.

**New `alternative_cost` values**:

| Value | Meaning | `targets` usage |
|-------|---------|-----------------|
| `"flashback"` | Cast from graveyard; exile on resolution | normal spell targets |
| `"escape"` | Cast from graveyard; exile N cards from graveyard | graveyard card IDs to exile |
| `"unearth"` | Cast from graveyard; exile at end of turn | (none) |
| `"disturb"` | Cast DFC transformed from graveyard | normal spell targets |
| `"convoke"` | Tap creatures to reduce cost | creature permanent IDs to tap |
| `"delve"` | Exile graveyard cards to reduce generic cost | graveyard card IDs to exile |
| `"emerge"` | Sacrifice a creature to reduce cost | `targets[0]` = creature to sacrifice |
| `"phyrexian"` | Pay 2 life per Phyrexian mana symbol | (none; life deducted automatically) |

---

## Legal Action Schema Extensions

`LegalAction` gains two optional fields used by new action types:

```json
{
  "action_type": "activate_loyalty",
  "permanent_id": "pw-abc123",
  "ability_index": 0,
  "loyalty_ability_index": 0,
  "valid_targets": ["creature-xyz"],
  "description": "Activate Jace, the Mind Sculptor: +1: Brainstorm"
}
```

```json
{
  "action_type": "cascade_choice",
  "cascade_card_id": "card-abc",
  "card_name": "Lightning Bolt",
  "description": "Cascade: cast Lightning Bolt for free?"
}
```

```json
{
  "action_type": "cast",
  "card_id": "card-def",
  "card_name": "Snapcaster Mage",
  "from_graveyard": true,
  "valid_targets": [],
  "description": "Cast Snapcaster Mage (unearth) from graveyard"
}
```

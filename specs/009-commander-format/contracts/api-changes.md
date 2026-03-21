# API Contract: Commander Format Changes

**Branch**: `009-commander-format` | **Date**: 2026-03-21

All changes are backward-compatible additions. Existing standard-format requests are unaffected.

---

## `POST /game` — Create Game (extended)

**Request body additions**:

```json
{
  "player1_name": "Alice",
  "player2_name": "Bob",
  "deck1": ["Forest", "Forest", ...],
  "deck2": ["Forest", "Forest", ...],
  "format": "commander",
  "commander1": "Multani, Maro-Sorcerer",
  "commander2": "Ghalta, Primal Hunger",
  "verbose": false
}
```

| Field | Required | Values | Notes |
|-------|----------|--------|-------|
| `format` | No | `"standard"` (default), `"commander"` | Omit for standard games |
| `commander1` | If `format == "commander"` | Card name string | Must be a legendary creature in `deck1`; placed in command zone, not in library |
| `commander2` | If `format == "commander"` | Card name string | Must be a legendary creature in `deck2`; placed in command zone, not in library |

**Validation errors (Commander mode)**:
- `DECK_SIZE_ERROR` — deck not exactly 100 cards (not counting commander which is removed)
- `SINGLETON_VIOLATION` — deck contains more than one copy of a non-basic-land card; error body includes offending card name
- `INVALID_COMMANDER` — designated card is not a legendary creature or is not in the deck
- `COLOR_IDENTITY_VIOLATION` — a deck card's color identity contains a color not in the commander's color identity; error body includes offending card name and commander color identity

**Response**: Same as standard. `players[N].command_zone` will contain the commander card.

---

## `GET /game/{game_id}` — Game State (extended response)

**New fields in response `data`**:

```json
{
  "data": {
    "format": "commander",
    "commander_damage": {
      "<commander_permanent_id>": {
        "Alice": 14,
        "Bob": 0
      }
    },
    "players": [
      {
        "name": "Alice",
        "life": 40,
        "command_zone": [
          {
            "name": "Multani, Maro-Sorcerer",
            "mana_cost": "{4}{G}{G}",
            "type_line": "Legendary Creature — Elemental",
            ...
          }
        ],
        "commander_name": "Multani, Maro-Sorcerer",
        "commander_cast_count": 1
      }
    ]
  }
}
```

---

## `GET /game/{game_id}/legal-actions` — Legal Actions (extended)

**New action type: `cast_commander`**

Appears when:
- `format == "commander"`
- The priority player's commander is in their command zone
- The player can pay the commander's mana cost + commander tax (`2 × commander_cast_count` additional generic mana)

```json
{
  "data": {
    "priority_player": "Alice",
    "phase": "precombat_main",
    "step": "main",
    "legal_actions": [
      {
        "action_type": "cast_commander",
        "card_id": "<card_id_of_commander_in_command_zone>",
        "card_name": "Multani, Maro-Sorcerer",
        "description": "Cast Multani, Maro-Sorcerer from command zone (cost: {4}{G}{G} + {2} tax = {6}{G}{G})",
        "mana_options": [{"mana_cost": "{4}{G}{G}", "commander_tax": 2}]
      }
    ]
  }
}
```

---

## `POST /game/{game_id}/cast` — Cast Spell (extended request)

**New optional field**:

```json
{
  "card_id": "<commander_card_id>",
  "mana_payment": {"G": 2, "C": 6},
  "targets": [],
  "from_command_zone": true
}
```

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `from_command_zone` | No | `false` | If `true`, the engine looks for the card in the command zone rather than hand; applies commander tax; increments `commander_cast_count` |

**Validation errors**:
- `INVALID_ACTION` with message `"Commander not in command zone"` if `from_command_zone=true` but card is not there
- `INVALID_ACTION` with message `"Insufficient mana for commander tax"` if mana payment does not include the tax amount

---

## CLI Argument Contract: Commander Mode

### New flags

| Flag | Format | Required | Default | Description |
|------|--------|----------|---------|-------------|
| `--format` | `standard\|commander` | No | `standard` | Game format |
| `--commander` | `CARD NAME` (repeatable) | If `--format commander` | — | Commander name per player, in player order |

### Invocation examples

```bash
# Commander mode with default decks
python -m ai_client \
  --format commander \
  --player "Alice,http://localhost:8080/v1,llama3.2" \
  --player "Bob,http://localhost:8080/v1,llama3.2" \
  --commander "Multani, Maro-Sorcerer" \
  --commander "Ghalta, Primal Hunger"

# Commander mode with custom decks
python -m ai_client \
  --format commander \
  --player "Alice,http://localhost:8080/v1,llama3.2" \
  --player "Bob,http://localhost:8080/v1,llama3.2" \
  --commander "Multani, Maro-Sorcerer" \
  --commander "Ghalta, Primal Hunger" \
  --deck1 "Forest,Forest,...,Llanowar Elves,..." \
  --deck2 "Forest,Forest,...,Llanowar Elves,..."
```

### Validation errors (Commander mode)

- Fewer than two `--commander` flags when `--format commander` → exit 1 with descriptive error
- More than two `--commander` flags → exit 1 (only 2-player Commander supported)
- `--commander` used without `--format commander` → warning printed, flag ignored

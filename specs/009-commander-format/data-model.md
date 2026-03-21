# Data Model: Commander Format Support

**Branch**: `009-commander-format` | **Date**: 2026-03-21

All changes are additive extensions to existing models. No existing fields are removed or renamed.

---

## Modified: `Card` (in `mtg_engine/models/game.py`)

Add one new field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `color_identity` | `list[str]` | `[]` | Scryfall color identity (e.g. `["G"]` for mono-green). Used for Commander deck validation. Populated from Scryfall `color_identity` field. |

**Populated by**: `ScryfallClient._build_card()` from `raw.get("color_identity", [])`.

---

## Modified: `PlayerState` (in `mtg_engine/models/game.py`)

Add three new fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `command_zone` | `list[Card]` | `[]` | Cards in this player's command zone. Holds at most one card (the commander) in standard Commander. |
| `commander_name` | `str \| None` | `None` | Name of this player's designated commander. Set at game creation; `None` for non-Commander games. |
| `commander_cast_count` | `int` | `0` | Number of times this player has cast their commander from the command zone. Used to compute commander tax. |

**Derived value** (not stored): `commander_tax = 2 × commander_cast_count` generic mana added to commander's base cost.

---

## Modified: `GameState` (in `mtg_engine/models/game.py`)

Add two new fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | `str` | `"standard"` | Game format identifier. `"standard"` or `"commander"`. Controls rule enforcement throughout the game. |
| `commander_damage` | `dict[str, dict[str, int]]` | `{}` | Nested dict: `commander_permanent_id → defending_player_name → total_combat_damage`. Accumulated for the full game; never reset. |

---

## Modified: `CreateGameRequest` (in `mtg_engine/api/routers/game.py`)

Add three new fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | `str` | `"standard"` | Game format. `"standard"` enforces 60-card minimum; `"commander"` enforces 100-card singleton + color identity. |
| `commander1` | `str \| None` | `None` | Card name of player 1's commander. Required when `format == "commander"`. |
| `commander2` | `str \| None` | `None` | Card name of player 2's commander. Required when `format == "commander"`. |

---

## Modified: `LegalAction` (in `mtg_engine/models/actions.py`)

Extend the `action_type` field's documented values:

| Action Type | When Present | Extra Fields |
|-------------|--------------|--------------|
| `cast_commander` | Commander is in command zone AND player can pay mana cost + tax | `card_id`, `card_name`, `mana_options` (includes tax), `description` |

The `cast_commander` action is submitted to `POST /game/{id}/cast` with `from_command_zone: true` in the request body.

---

## Modified: `CastRequest` (in `mtg_engine/models/actions.py`)

Add one new field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `from_command_zone` | `bool` | `False` | If `True`, the card is cast from the command zone rather than from hand. The engine applies commander tax and increments `commander_cast_count`. |

---

## New Entity: Commander Damage Record

Not a Pydantic model — stored directly in `GameState.commander_damage`.

```
GameState.commander_damage = {
    "<permanent_id_of_commander_A>": {
        "player_B": 14,
        "player_C": 0
    },
    "<permanent_id_of_commander_B>": {
        "player_A": 7
    }
}
```

**Lifecycle**:
- Entry created when a commander permanent first deals combat damage to a player
- Cumulative total grows with each combat damage event
- Entry is NOT deleted when the commander leaves the battlefield (the permanent ID record persists)
- New permanent ID created on re-cast, but old entry remains (old damage is preserved as historical record)

---

## Modified: `GameConfig` (in `ai_client/models.py`)

Add three new fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | `str` | `"standard"` | Game format passed to the engine. `"commander"` activates Commander rules. |
| `commander1` | `str \| None` | `None` | Card name of player 1's commander. Required in Commander mode. |
| `commander2` | `str \| None` | `None` | Card name of player 2's commander. Required in Commander mode. |

---

## Entity Relationships

```
GameState
  ├── format: "standard" | "commander"
  ├── commander_damage: {perm_id → {player → int}}
  └── players: [PlayerState, ...]
        ├── command_zone: [Card]        ← at most 1 in Commander
        ├── commander_name: str | None
        └── commander_cast_count: int

Card
  └── color_identity: [str]             ← new; from Scryfall

CastRequest
  └── from_command_zone: bool           ← new

CreateGameRequest
  ├── format: str
  ├── commander1: str | None
  └── commander2: str | None

GameConfig (ai_client)
  ├── format: str
  ├── commander1: str | None
  └── commander2: str | None
```

# Data Model: Full Rules Engine Parity (018)

## Model Changes

### GameState (mtg_engine/models/game.py)

New optional fields added:

```python
# Pending blocking choices (set by engine, cleared on choice submission)
pending_scry_choice: dict | None = None
# Format: {"player": str, "cards": [Card], "n": int}

pending_surveil_choice: dict | None = None
# Format: {"player": str, "cards": [Card], "n": int}

pending_tutor_choice: dict | None = None
# Format: {"player": str, "filter_type": str, "destination": "hand" | "battlefield"}

pending_discard_choice: dict | None = None
# Format: {"player": str, "count": int}

pending_ward_payment: dict | None = None
# Format: {"player": str, "ward_cost": str, "targeting_spell_id": str}

# Transform tracking
spells_cast_this_turn: int = 0    # Reset each turn; checked for werewolf conditions
spells_cast_last_turn: int = 0    # Snapshot of previous turn's count
```

Note: `pending_cascade` already exists on GameState.

---

### StackObject (mtg_engine/models/game.py)

New fields:

```python
x_value: int = 0                          # X value for {X} spells
kicker_paid: bool = False                  # Whether kicker cost was paid
jump_start_discard_id: str | None = None   # Card discarded for jump-start cost
```

Note: `modes_chosen: list[int]` already exists.

---

### Permanent (mtg_engine/models/game.py)

New fields:

```python
unearthed: bool = False     # True if entered via Unearth — exile at end of turn
time_counters: int = 0      # Used for suspended cards in exile zone
foretold: bool = False      # True if exiled face-down via Foretell
```

---

### CastRequest (mtg_engine/models/actions.py)

New fields:

```python
x_value: int = 0                          # X value chosen for {X} mana cost
kicker_paid: bool = False                  # Whether to pay kicker cost
jump_start_discard_id: str | None = None   # Card to discard for jump-start
```

Note: `modes_chosen: list[int]` and `from_graveyard: bool` already exist.

---

### PlayerState (mtg_engine/models/game.py)

New fields:

```python
suspended_cards: list[Card] = []   # Cards exiled via Suspend (with time_counters)
foretold_cards: list[Card] = []    # Cards exiled face-down via Foretell
```

---

### LegalAction (mtg_engine/models/actions.py)

New fields (all optional):

```python
x_value: int | None = None         # For X spell variants
kicker_paid: bool | None = None    # For kicker variants
```

---

## New Legal Action Types

| action_type | When emitted | Key fields |
|-------------|-------------|------------|
| `suspend` | Main phase, suspend card in hand | `card_id`, `description` |
| `foretell` | Main phase, foretell card in hand | `card_id`, `description` |
| `cascade_choice` | After cascade spell resolves | `cascade_card_id`, `card_id` |

Note: `cascade_choice` endpoint already exists in the router.

---

## Entity Relationships

```
GameState
├── pending_scry_choice → {player, cards[], n}
├── pending_surveil_choice → {player, cards[], n}
├── pending_tutor_choice → {player, filter_type, destination}
├── pending_discard_choice → {player, count}
├── pending_ward_payment → {player, ward_cost, targeting_spell_id}
├── spells_cast_this_turn: int
├── spells_cast_last_turn: int
├── players[] → PlayerState
│   ├── suspended_cards[]
│   └── foretold_cards[]
├── battlefield[] → Permanent
│   ├── unearthed: bool
│   ├── time_counters: int
│   └── foretold: bool
└── stack[] → StackObject
    ├── x_value: int
    ├── kicker_paid: bool
    └── jump_start_discard_id: str | None
```

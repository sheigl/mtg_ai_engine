# Data Model: Rules Engine Gap Closure (Feature 019)

**Feature**: 019-rules-engine-gap-closure
**Date**: 2026-03-29

---

## New Models

### Emblem
Location: `mtg_engine/models/game.py`

```python
class Emblem(BaseModel):
    id: str                    # UUID
    controller: str            # player name who controls this emblem
    source_name: str           # planeswalker card name that created this emblem
    abilities: list[str]       # oracle text of the emblem's abilities
```

Emblems live in `GameState.emblems: list[Emblem]`. They function like permanents for trigger detection — the trigger loop must iterate emblems alongside permanents.

---

## Modified Models

### CastRequest (`mtg_engine/models/actions.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `convoke_creature_ids` | `list[str]` | `[]` | Creature IDs to tap for Convoke |
| `delve_card_ids` | `list[str]` | `[]` | Graveyard card IDs to exile for Delve |
| `improvise_artifact_ids` | `list[str]` | `[]` | Artifact IDs to tap for Improvise |
| `emerge_sacrifice_id` | `str \| None` | `None` | Creature ID to sacrifice for Emerge |
| `buyback_paid` | `bool` | `False` | Whether buyback cost was paid |
| `replicate_count` | `int` | `0` | Number of replicate payments made |
| `flashback` | `bool` | `False` | Casting via flashback from graveyard |
| `escape_exile_ids` | `list[str]` | `[]` | Graveyard card IDs to exile for Escape |
| `opponent_target` | `str \| None` | `None` | Specific opponent for "target opponent" effects in multiplayer |

### StackObject (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `buyback_paid` | `bool` | `False` | Whether buyback is active for this cast |
| `replicate_count` | `int` | `0` | Number of replicate copies to create on resolution |
| `flashback` | `bool` | `False` | Card came from graveyard via flashback |
| `escape` | `bool` | `False` | Card came from graveyard via escape |

### GameState (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `emblems` | `list[Emblem]` | `[]` | Emblem objects from planeswalker ultimates |

Note: `spells_cast_this_turn: int` already exists and is sufficient for Storm.

### LegalAction (`mtg_engine/models/actions.py`)
New action_type values:

| Value | Description |
|-------|-------------|
| `"cycle"` | Cycling a card from hand |
| `"dredge"` | Choosing to dredge instead of draw (presented during draw step) |
| `"proliferate"` | Selecting proliferate targets |
| `"cast_flashback"` | Casting a spell from graveyard via flashback |
| `"cast_escape"` | Casting a spell from graveyard via escape |

---

## Existing Fields Leveraged (No Changes Needed)

| Model | Field | Used For |
|-------|-------|---------|
| `Permanent.unearthed` | `bool` | Unearth SBA — already exists |
| `Permanent.loyalty_activated_this_turn` | `bool` | Loyalty limit enforcement — already exists |
| `Permanent.counters` | `dict[str, int]` | Persist/Undying counter checks; lore counters for Sagas |
| `PlayerState.commander_cast_count` | `int` | Command tax — already exists |
| `PlayerState.suspended_cards` | `list[Card]` | Suspend auto-cast — already exists |
| `GameState.spells_cast_this_turn` | `int` | Storm count — already exists |
| `CastRequest.from_command_zone` | `bool` | Command tax — already exists |
| `CastRequest.from_graveyard` | `bool` | Flashback/Escape base — already exists |
| `Card.parse_status` | `str` | `"suspended:N"` time counter tracking — already exists |

---

## State Transitions

### Saga Lifecycle
```
[enters battlefield]
  → add lore counter (counters["lore"] = 1)
  → fire Chapter I trigger
  → [each upkeep] add lore counter
  → fire corresponding chapter trigger
  → [final chapter trigger resolves] → sacrifice
```

### Suspend Lifecycle
```
[cast with suspend] → card exiled with parse_status="suspended:N"
  → [each upkeep] decrement N
  → [N reaches 0] → cast for free (no mana cost)
  → [if creature] add haste until end of turn
  → [if countered] card goes to graveyard (not back to exile)
```

### Persist/Undying Lifecycle
```
[creature would go to graveyard from battlefield]
  → check persist: keyword="persist" AND counters.get("-1/-1", 0) == 0
    → true: return to battlefield with -1/-1 counter (no graveyard trip)
  → check undying: keyword="undying" AND counters.get("+1/+1", 0) == 0
    → true: return to battlefield with +1/+1 counter (no graveyard trip)
  → else: proceed to graveyard normally
```

### Flashback/Escape Lifecycle
```
[card in graveyard] → legal_actions includes cast_flashback/cast_escape
  → [cast] → card moves from graveyard to stack
  → [resolves or countered] → card goes to EXILE (not graveyard)
```

### Dredge Lifecycle
```
[player would draw a card]
  → check graveyard for dredge cards
  → if found: present dredge_choice legal action
  → [player chooses dredge N] → mill N cards, return dredge card to hand (no draw)
  → [player passes/no dredge cards] → draw normally
```

---

## Counter Key Conventions

The `Permanent.counters: dict[str, int]` uses string keys. New counter types added:

| Key | Used For |
|-----|---------|
| `"lore"` | Saga chapter tracking |
| `"time"` | Suspend time counters (alternative to parse_status approach) |

Note: Existing convention uses `parse_status="suspended:N"` for time counters on cards in exile. The `"time"` counter key is available for future permanents that use time counters on the battlefield (Vanishing).

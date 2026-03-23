# Data Model: Rules Engine Completeness (014)

**Date**: 2026-03-23

All changes are **additive** — existing model shapes are preserved. New fields have defaults so all existing serialized states remain valid.

---

## Modified Models

### `GameState` (mtg_engine/models/game.py)

New optional fields:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `prevention_effects` | `list[DamagePreventionEffect]` | `[]` | Active damage prevention shields (FR-007) |
| `attack_constraints` | `list[AttackConstraint]` | `[]` | Must-attack / cost-to-attack / goad constraints (FR-010, FR-011) |
| `block_constraints` | `list[BlockConstraint]` | `[]` | Cannot-block / evasion restrictions (FR-010) |
| `prevent_all_combat_damage` | `bool` | `False` | Set by Fog-like effects; cleared at end of step (FR-007) |
| `phase_skip_flags` | `dict[str, bool]` | `{}` | Keys: phase names to skip (e.g. `"combat"`). Cleared end of turn (FR-012) |

### `Permanent` (mtg_engine/models/game.py)

New optional fields:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `copy_of_permanent_id` | `str \| None` | `None` | Source permanent ID for copy effects (layer 1, FR-008) |

### `StackObject` (mtg_engine/models/game.py)

Already has `is_copy: bool = False` — no change needed. Used by copy-spell resolution to skip graveyard placement (FR-012).

---

## New Models

### `DamagePreventionEffect` (mtg_engine/models/game.py)

Represents an active damage prevention shield.

| Field | Type | Description |
|-------|------|-------------|
| `effect_id` | `str` | Unique ID (UUID) |
| `source_permanent_id` | `str \| None` | Permanent that created the effect; `None` for spell-sourced effects (Fog) |
| `target_id` | `str \| None` | Specific permanent/player this applies to; `None` = global (all combat) |
| `remaining` | `int \| None` | Damage remaining to prevent; `None` = unlimited (until end of turn) |
| `combat_only` | `bool` | `True` if only prevents combat damage (Fog) vs all damage |
| `color_restriction` | `str \| None` | If set, only prevents damage from sources of this color (protection) |

**Validation rules**:
- When `remaining` is not `None`, decrement by the amount prevented each time the effect is applied.
- When `remaining` reaches 0, remove from `GameState.prevention_effects`.
- All effects are cleared at start of cleanup step.

### `AttackConstraint` (mtg_engine/models/game.py)

Represents a constraint on declaring attackers.

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Source permanent generating this constraint |
| `affected_id` | `str` | Creature permanent ID, or `"all"` for all creatures |
| `constraint_type` | `Literal["must_attack", "cannot_attack", "cost_to_attack", "goad"]` | Constraint kind |
| `cost` | `str \| None` | Mana cost string (e.g. `"{2}"`) for `cost_to_attack` type |
| `goad_controller` | `str \| None` | For `"goad"`: player whose creatures must be attacked instead |

### `BlockConstraint` (mtg_engine/models/game.py)

Represents a constraint on declaring blockers.

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Source permanent generating this constraint |
| `affected_id` | `str` | Blocker permanent ID, or `"all"` for all blockers |
| `constraint_type` | `Literal["cannot_block", "can_only_block_flyers", "min_power_to_block"]` | Constraint kind |
| `restriction` | `str \| None` | Additional restriction details (e.g. power threshold) |

---

## State Transitions

### DamagePreventionEffect lifecycle

```
Fog resolves → GameState.prevent_all_combat_damage = True
                                     │
                          Combat damage step
                                     │
               assign_combat_damage checks prevent_all_combat_damage
                                     │
                          All damage → 0
                                     │
              Cleanup step → prevent_all_combat_damage reset to False
```

### AttackConstraint lifecycle

```
Propaganda ETB → derive AttackConstraint("cost_to_attack", cost="{2}", affected="all")
                stored in GameState.attack_constraints
                                     │
                     Declare Attackers legal action check
                                     │
            Cost payable? → include attacker in legal actions
            Cost not payable? → omit attacker from legal actions
```

### Deck-out loss

```
draw_card(player) called when library is empty
        │
player.has_lost = True (marks loss immediately)
        │
SBA loop on next priority grant detects has_lost → sets is_game_over
```

---

## No New Tables / No Persistence Changes

All models are held in-memory in `GameState`. No database schema changes. The SQLite Scryfall cache is unaffected.

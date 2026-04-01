# Data Model: Rules Engine Complete Parity (Feature 020)

**Feature**: 020-rules-engine-complete-parity
**Date**: 2026-04-01

---

## New Models

### DamageModifier
Location: `mtg_engine/models/game.py`

```python
class DamageModifier(BaseModel):
    """A damage multiplication replacement effect (CR 614.1a)."""
    source_permanent_id: str        # Permanent providing the effect
    controller: str                 # Controller of the source permanent
    multiplier: int = 2             # 2 = double, 3 = triple
    applies_to: str = "all"         # "all" | "sources_you_control" | "combat_only"
    timestamp: float = 0.0          # For ordering when multiple modifiers apply
```

Registered on `GameState.damage_modifiers: list[DamageModifier]`. Added when a permanent with a damage-doubling/tripling static ability enters the battlefield; removed when it leaves.

---

### ETBReplacementEffect
Location: `mtg_engine/replacement.py` (internal, not a Pydantic model on GameState)

```python
@dataclass
class ETBReplacementEffect:
    source_permanent_id: str        # Permanent imposing the replacement
    pattern: str                    # Regex pattern to match against entering permanent
    effect_type: str                # "enters_tapped" | "counter_multiply" | "counter_add"
    parameters: dict                # e.g. {"multiplier": 2} or {"counter_type": "+1/+1", "count": 1}
    applies_to: Callable            # Predicate: (entering_permanent, controller) -> bool
```

This is a runtime-only dataclass used within `apply_etb_replacements()`. Not persisted on GameState — rebuilt by scanning battlefield permanents at ETB time.

---

### ManaPoolPersistence
Location: `mtg_engine/models/game.py` (field on PlayerState)

```python
class ManaPoolPersistence(BaseModel):
    """Tracks which mana colors persist across step/phase transitions."""
    colors: list[str] = Field(default_factory=list)  # ["G"] for Omnath, ["W","U","B","R","G","C"] for Upwelling
    convert_to_colorless: bool = False                # True for Kruphix (unused mana becomes colorless)
```

---

## Modified Models

### Card (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `card_layout` | `str` | `"normal"` | Layout type: `"normal"`, `"split"`, `"mdfc"`, `"adventure"`, `"aftermath"`, `"transform"` |

Note: `faces: list[CardFace] | None` already exists. `CardFace` already has all needed fields (name, mana_cost, type_line, oracle_text, power, toughness, loyalty, colors). No changes to `CardFace` needed.

---

### CastRequest (`mtg_engine/models/actions.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `face_index` | `int` | `0` | Which face to cast for split/MDFC/adventure cards (0=left/front, 1=right/back) |
| `fuse` | `bool` | `False` | Cast both halves of a split card with fuse |
| `as_face_down` | `bool` | `False` | Cast face-down (morph) for {3} |
| `foretell` | `bool` | `False` | Exile face-down for foretell ({2} cost) |
| `cast_foretold` | `bool` | `False` | Cast from foretell exile at foretell cost |
| `mutate_target_id` | `str \| None` | `None` | Target creature for mutate cast |
| `mutate_on_top` | `bool` | `True` | Place mutating creature on top (True) or bottom (False) |

---

### StackObject (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `face_index` | `int` | `0` | Which face this spell represents |
| `is_face_down` | `bool` | `False` | Morph: spell is face-down |
| `is_adventure` | `bool` | `False` | Spell is the adventure half (exile on resolution, not graveyard) |
| `is_fused` | `bool` | `False` | Fused split card (both halves) |
| `mutate_target_id` | `str \| None` | `None` | Target creature for mutate |
| `mutate_on_top` | `bool` | `True` | Mutate placement choice |

---

### Permanent (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `phased_out` | `bool` | `False` | True if this permanent is phased out (treated as nonexistent) |
| `crewed_until_end_of_turn` | `bool` | `False` | True if crewed; becomes creature until cleanup |
| `has_phasing` | `bool` | `False` | True if this permanent has the phasing keyword |
| `echo_paid` | `bool` | `False` | True after echo cost has been paid |
| `echo_cost` | `str \| None` | `None` | Echo cost string parsed from oracle_text |
| `mutated_cards` | `list[Card]` | `[]` | Cards in the mutate pile (bottom to top order) |
| `mana_doesnt_empty` | `ManaPoolPersistence \| None` | `None` | If set, this permanent grants mana persistence to its controller |

---

### ManaPool (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `snow` | `int` | `0` | Amount of snow-flagged mana available for `{S}` costs |
| `snow_by_color` | `dict[str, int]` | `{}` | Snow mana tracked per color: `{"G": 2, "R": 1}` means 2 green snow, 1 red snow |

**Mana tracking note**: When a snow permanent produces mana, the mana is added both to the appropriate color field (e.g. `G += 1`) and to `snow_by_color` (e.g. `snow_by_color["G"] += 1`). When paying `{S}`, any entry in `snow_by_color` with value > 0 can satisfy it; the corresponding color field is decremented too. The `snow` field is the sum of all `snow_by_color` values (convenience field).

---

### PlayerState (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `mana_persistence` | `ManaPoolPersistence` | `ManaPoolPersistence()` | Which mana colors persist for this player |

---

### GameState (`mtg_engine/models/game.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `additional_combat_phases` | `int` | `0` | Number of additional combat phases remaining this turn |
| `step_skip_flags` | `dict[str, bool]` | `{}` | Step-level skip flags keyed by Step value (e.g. `{"draw": True}`) |
| `damage_modifiers` | `list[DamageModifier]` | `[]` | Active damage multiplication effects |
| `pending_legend_choice` | `dict \| None` | `None` | Format: `{"player": str, "permanent_ids": [str], "legend_name": str}` |
| `pending_morph_payment` | `dict \| None` | `None` | Format: `{"player": str, "permanent_id": str, "morph_cost": str}` |
| `pending_echo_payment` | `dict \| None` | `None` | Format: `{"player": str, "permanent_id": str, "echo_cost": str}` |

---

### LegalAction (`mtg_engine/models/actions.py`)
New action_type values:

| Value | When Present | Key Fields |
|-------|-------------|-----------|
| `"crew"` | Player controls a Vehicle and untapped creatures with sufficient total power | `permanent_id` (vehicle), `description` includes crew cost |
| `"turn_face_up"` | Player controls a face-down creature and can pay the morph cost | `permanent_id`, `mana_options` (morph cost) |
| `"foretell"` | Player has a foretell card in hand during their turn | `card_id`, description includes "{2} to foretell" |
| `"cast_foretold"` | Player has a foretold card in exile and can pay foretell cost | `card_id`, `mana_options` (foretell cast cost) |
| `"cast_adventure"` | Player has an adventure card in hand or adventure-exiled creature | `card_id`, `face_index` |
| `"activate_mana_ability"` | Player controls a permanent with a mana ability | `permanent_id`, `ability_index` |
| `"mutate"` | Player has a mutate creature in hand and controls a non-Human creature | `card_id`, `valid_targets` (non-Human creatures) |

---

### ContinuousEffect (`mtg_engine/engine/layers.py`)
New fields added:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `type_operation` | `str` | `"add"` | `"add"` (existing), `"remove"`, or `"overwrite"` |
| `remove_abilities` | `bool` | `False` | If True, remove all non-intrinsic abilities (Blood Moon) |
| `grant_abilities` | `list[str]` | `[]` | Abilities to grant after removal (e.g. `["{T}: Add {R}"]`) |
| `switch_pt` | `bool` | `False` | If True, this is a layer 7d P/T switch effect |

---

## Existing Fields Leveraged (No Changes Needed)

| Model | Field | Used For |
|-------|-------|---------|
| `Permanent.is_face_down` | `bool` | Morph face-down state — already exists |
| `Permanent.foretold` | `bool` | Foretell exile state — already exists |
| `Permanent.counters` | `dict[str, int]` | Fade counters, +1/+1 (megamorph), lore counters |
| `Permanent.damage_marked` | `int` | Cleanup damage removal — already exists |
| `Permanent.power_bonus` / `toughness_bonus` | `int` | Cleanup effect expiry — already exists |
| `Permanent.power_bonus_expires` | `str \| None` | "end_of_turn" tracking — already exists |
| `Permanent.summoning_sick` | `bool` | Crew timing check — already exists |
| `PlayerState.foretold_cards` | `list[Card]` | Foretell tracking — already exists |
| `PlayerState.max_hand_size` | `int` | Cleanup discard check — already exists |
| `GameState.pending_ward_payment` | `dict \| None` | Ward payment flow — field already exists |
| `GameState.pending_discard_choice` | `dict \| None` | Cleanup discard — field already exists |
| `GameState.phase_skip_flags` | `dict[str, bool]` | Phase-level skipping — already exists |
| `GameState.extra_turns` | `list[str]` | Extra turn tracking — already exists |
| `StackObject.kicker_paid` | `bool` | Kicker detection at resolution — already exists |
| `SpecialActionRequest.action_type` | `str` | `"turn_face_up"` already defined — needs wiring |
| `CombatState.blocker_order` on `AttackerInfo` | `list[str]` | Blocker ordering — already exists |
| `Card.faces` | `list[CardFace] \| None` | Multi-face data — already exists |

---

## State Transitions

### Cleanup Step Flow
```
[end step completes]
  → enter cleanup step
  → active player discards to max_hand_size (if needed)
    → set pending_discard_choice
    → wait for player choice
  → remove all damage_marked on permanents
  → expire "until end of turn" effects (power_bonus, toughness_bonus, crewed, temp keywords)
  → check SBAs
    → if SBAs fired or triggers added:
      → grant priority
      → resolve stack
      → begin NEW cleanup step (loop)
    → else: end turn
```

### Morph Face-Up Flow
```
[player submits turn_face_up action]
  → validate: permanent is face-down, controller matches, can pay morph cost
  → deduct morph cost from mana pool
  → set is_face_down = False on permanent
  → restore printed characteristics (name, type_line, abilities, P/T)
  → if megamorph: add +1/+1 counter
  → check triggers ("whenever [this] is turned face up")
  → NO stack involvement (special action)
```

### Vehicle Crew Flow
```
[player submits crew action with vehicle_id + creature_ids]
  → validate: vehicle on battlefield, creatures untapped, total power >= crew cost
  → tap all crew creatures
  → set crewed_until_end_of_turn = True on vehicle
  → vehicle gains creature type (type_line includes "Creature")
  → at cleanup: clear crewed_until_end_of_turn, remove creature type
```

### Adventure Card Flow
```
[in hand: two legal actions available]
  → cast_adventure (face_index=1): adventure spell on stack
    → on resolution: exile card (not graveyard)
    → card tracked as "adventure-exiled" on PlayerState.exile
  → cast creature (face_index=0): creature spell on stack
    → resolves normally

[from exile after adventure resolved]
  → cast creature (from exile): creature enters battlefield
  → on death/removal: goes to graveyard (not back to exile)

[adventure spell countered]
  → card goes to graveyard (exile only on successful resolution)
```

### Phasing Step (Untap)
```
[untap step begins, BEFORE untapping]
  → for each permanent with phased_out=True:
    → if token: remove from battlefield (cease to exist)
    → else: set phased_out = False (phase in; NOT an ETB)
  → for each permanent with has_phasing=True and phased_out=False:
    → set phased_out = True
    → find all attached Auras/Equipment: set phased_out = True (indirect phasing)
  → proceed to normal untap
```

### Mutate Merge Flow
```
[mutate spell resolves]
  → find target creature (must be non-Human, controlled by caster)
  → if mutate_on_top:
    → mutating card goes on top of pile
    → permanent keeps new top card's name/P/T/types
  → else:
    → mutating card goes under the pile
    → permanent keeps existing top card's name/P/T/types
  → permanent gains all abilities from all cards in pile
  → fire "whenever this creature mutates" triggers
  → update permanent.mutated_cards list
```

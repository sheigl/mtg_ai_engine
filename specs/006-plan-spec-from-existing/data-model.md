# Data Model: MTG Rules Engine

**Generated**: 2026-03-20  
**Source**: `/specs/006-plan-spec-from-existing/spec.md`  
**Status**: Phase 1 - Design & Contracts

---

## Overview

This document defines the Pydantic v2 models for all game state objects in the MTG Rules Engine. All models are fully JSON-serializable and type-annotated for Python 3.11+.

---

## Core Entities

### Card

Represents a single Magic: The Gathering card in any zone.

```python
class Card(BaseModel):
    id: str  # Scryfall oracle ID (e.g., "43d2d6a4-a3d4-4f0d-9b7e-1e8f5c6d7e8f")
    name: str
    mana_cost: Optional[str]  # e.g., "{2}{U}{U}"
    cmc: Decimal  # Converted mana cost
    card_type: str  # e.g., "creature", "instant", "enchantment"
    subtype: Optional[str]  # e.g., "Elf Warrior", "Sorcery"
    power: Optional[int]  # Only for creatures
    toughness: Optional[int]  # Only for creatures
    rules_text: Optional[str]  # Oracle text
    color_identity: Optional[str]  # e.g., "U" for blue
    set: str
    collector_number: str
    rarity: str
    
    # Runtime state
    zone: str  # "hand", "library", "graveyard", "stack", "battlefield", "exile"
    owner: int  # Player ID (0 or 1)
    controller: int  # Player ID who controls the card
    tapped: bool = False
    summoning_sickness: bool = True  # Can't attack/activate unless haste
    counters: Dict[str, int] = {}  # e.g., {"+1/+1": 3}
    attached_to: Optional[str] = None  # Card ID if attached (auras/equipment)
    flipped: bool = False  # For double-faced cards
    face_id: Optional[str] = None  # Which face is up
    
    # Copy state
    is_copy: bool = False
    copy_of: Optional[str] = None  # Card ID being copied
    copy_effects: List[str] = []  # Effects modifying copy state
```

**Validation Rules**:
- `power` and `toughness` only populated for `card_type == "creature"`
- `cmc` must equal sum of mana cost numerals (e.g., "{2}{U}{U}" → 4.0)
- `controller` must be valid player ID (0 or 1)
- `counters` keys must be valid counter types (engine-enforced at runtime)

---

### Player

Represents a game participant.

```python
class Player(BaseModel):
    id: int  # 0 (active) or 1 (non-active)
    name: str
    life: int = 20
    deck_size: int = 0  # Cards remaining in library
    hand_size: int = 0
    graveyard_size: int = 0
    exile_size: int = 0
    sideboard_size: int = 0
    cards_drawn_this_turn: int = 0
    tokens: Dict[str, int] = {}  # Token type → count
    phase_out_steps: int = 0  # For phased out permanents
    protection_colors: List[str] = []  # Colors this player protects from
    protection_qualities: List[str] = []  # e.g., "artifact", "black"
    
    # Turn-specific state
    max_hand_size: int = 7
    draws_this_turn: bool = False  # Whether they've drawn this turn
    skips_untap: bool = False
    skips_upkeep: bool = False
    skips_main_1: bool = False
    skips_combat: bool = False
    skips_main_2: bool = False
    skips_end: bool = False
```

**Validation Rules**:
- `life` must be ≥ 0 (SBA checks if ≤ 0 → player loses)
- `deck_size` must be ≥ 0 (SBA checks if ≤ 0 and no cards to draw → player loses)
- `id` must be 0 or 1 (2-player only)

---

### Zone

Represents a game zone (library, graveyard, battlefield, etc.).

```python
class Zone(BaseModel):
    name: str  # "library", "graveyard", "hand", "battlefield", "stack", "exile"
    owner_id: int  # Which player owns cards in this zone
    cards: List[str] = []  # Card IDs in order (top to bottom for library)
    
    # Library-specific
    library_top_cards: List[str] = []  # Cards visible from top (e.g., from scry)
    library_bottom_cards: List[str] = []  # Cards visible from bottom
    
    # Stack-specific
    stack_order: List[str] = []  # Card IDs from bottom to top
    
    # Battlefield-specific
    battlefield_order: List[str] = []  # For tracking layer order
```

**Validation Rules**:
- `owner_id` must match Player ID
- `cards` must reference valid Card objects
- Library cards must be in valid order (top card is first)

---

### Game

Represents the complete game state.

```python
class Game(BaseModel):
    id: str  # UUID
    created_at: datetime
    status: str  # "active", "completed", "aborted"
    
    # Players
    players: Dict[int, Player]  # 0 and 1
    
    # Zones
    zones: Dict[str, Zone]  # "library_0", "library_1", "graveyard_0", etc.
    battlefield: Zone  # Shared battlefield
    stack: Zone  # Shared stack
    
    # Turn structure
    turn: int = 1
    step: str = "untap"  # "untap", "upkeep", "draw", "main1", "combat", "main2", "end"
    phase: str = "precombat_main"  # "precombat_main", "combat", "postcombat_main"
    active_player: int = 0  # Whose turn it is
    non_active_player: int = 1
    
    # Stack state
    stack_height: int = 0  # For tracking priority
    priority: Optional[int] = None  # Whose priority it is (None = no priority)
    stack_items: List[StackItem] = []  # Full stack state
    
    # Game state flags
    round_of_sbas: bool = False  # Whether SBA check is in progress
    round_of_triggers: bool = False  # Whether trigger check is in progress
    round_of_replacements: bool = False  # Whether replacement check is in progress
    
    # Random state
    random_seed: Optional[int] = None  # For determinism
    rng: Optional[Any] = None  # Seeded Random instance
    
    # Metadata
    format: str = "competitive"  # Not implementing Commander, etc.
    rule_413: bool = True  # Fixed game state (default)
```

**Validation Rules**:
- `active_player` must match `turn` player (0 for odd turns, 1 for even)
- `priority` must be 0 or 1 when set
- `step` must be valid for current `phase` and `turn`

---

### StackItem

Represents an object on the stack (spell, ability, etc.).

```python
class StackItem(BaseModel):
    id: str  # UUID
    source_type: str  # "spell", "ability", "trigger"
    source_id: str  # Card ID or "game" for game actions
    ability_type: Optional[str]  # e.g., "activated", "triggered", "static"
    target_player: Optional[int]  # Target player (if any)
    target_card: Optional[str]  # Target card ID (if any)
    targets: List[str] = []  # Multiple targets
    mode: Optional[str]  # e.g., "with_haste", "without_haste"
    value: Optional[Any]  # e.g., damage amount, number of cards
    controller: int  # Who put it on stack
    owner: int  # Who owns the source
    stack_time: int = 0  # Timestamp for layer ordering
    copied_from: Optional[str] = None  # If this is a copy
    spell_ability_index: Optional[int] = None  # For split cards on stack
    
    # Resolution state
    resolved: bool = False
    cancelled: bool = False
    source_removed: bool = False  # Source left battlefield before resolution
```

**Validation Rules**:
- `controller` and `owner` must be valid player IDs
- `targets` must be valid for the source ability (enforced at cast/activate time)
- `stack_time` must be monotonically increasing

---

### GameStateSnapshot

For training data export - immutable snapshot of game state.

```python
class GameStateSnapshot(BaseModel):
    game_id: str
    timestamp: datetime
    turn: int
    step: str
    phase: str
    active_player: int
    priority: Optional[int]
    
    # Player states
    player_states: Dict[int, PlayerState]
    
    # Battlefield state (simplified for training)
    battlefield: List[BattlefieldCard]
    
    # Stack state (simplified)
    stack: List[StackSnapshot]
    
    # Game flags
    sba_check_pending: bool
    trigger_check_pending: bool
```

---

## State Transitions

### Turn Structure

```
Start of Turn (Active Player)
  → Untap Step
    → Untap Phase (untap permanents, remove counters)
    → SBA Check
    → Priority Grant
  → Upkeep Step
    → Trigger "at beginning of upkeep" abilities
    → SBA Check
    → Priority Grant
  → Draw Step
    → Draw card
    → Trigger "at beginning of draw" abilities
    → SBA Check
    → Priority Grant
  → Main Phase I
    → Priority Grant
  → Combat Phase
    → Beginning of Combat Step
      → Priority Grant
    → Declare Attackers Step
      → Declare attackers
      → Priority Grant
    → Declare Blockers Step
      → Declare blockers
      → Combat Damage Step (first strike if applicable)
      → SBA Check
      → Combat Damage Step (regular if applicable)
      → SBA Check
    → End of Combat Step
      → Priority Grant
  → Main Phase II
    → Priority Grant
  → End Step
    → Trigger "at beginning of end" abilities
    → SBA Check
    → Priority Grant
  → End of Turn Phase
    → "At end of turn" triggers
    → SBA Check (hand size)
    → End turn
```

### Priority Flow

```
Event occurs (spell cast, ability activated, turn step changes)
  → Check replacement effects (event may be modified)
  → Check state-based actions (loop until no changes)
  → Check triggered abilities (add to stack in APNAP order)
  → If triggers exist:
      → Put triggers on stack (AP: first, then NAP)
      → Active player gets priority
    Else:
      → Active player gets priority
  → Player passes priority:
      → If other player has priority:
          → Other player gets priority
        Else:
          → If stack not empty:
              → Top of stack resolves
              → Repeat priority flow
            Else:
              → Move to next step/phase
```

---

## Layer System (CR 613)

The engine applies continuous effects in 7 layers, ordered by dependency:

```
Layer 1: Copy effects
Layer 2: Control-changing effects
Layer 3: Text-changing effects
Layer 4: Type-changing effects
Layer 5: Color-changing effects
Layer 6: Ability-adding/removing effects
Layer 7: Power/Toughness-changing effects
  → 7a: Characteristic-defining abilities
  → 7b: Set power/toughness effects
  → 7c: Modify power/toughness effects
  → 7d: P/T setting effects
```

**Dependency Rule (CR 613.8)**: An effect in layer N depends on layer M (M < N) if applying layer M changes what layer N applies to.

**Example**: Humility + Opalescence
- Humility: "All creatures lose all abilities and are 1/1"
- Opalescence: "Enchantments are creatures with P/T = CMC"
- Layer 4: Opalescence makes Humility a creature
- Layer 6: Humility removes Opalescence's ability (but Opalescence already applied)
- Layer 7b: Both become 1/1

---

## Replacement Effects (CR 616)

Replacement effects modify events before they happen:

```python
class ReplacementEffect(BaseModel):
    source_id: str  # Card ID with replacement effect
    effect_type: str  # e.g., "damage_prevention", "enter_as_copy", "phase_skip"
    replacement_text: str  # Human-readable description
    applies_to: List[str]  # Event types: ["damage", "draw", "enter_battlefield", ...]
    target_types: List[str]  # What can be affected: ["creature", "player", "spell", ...]
    optional: bool = False  # Controller chooses whether to apply
    source_controller: int  # Who controls the replacement effect
```

**Ordering Rule (CR 616.5)**: When multiple replacement effects apply to same event, affected object's controller chooses order.

---

## Training Data Schemas

### Game Snapshot (for state → action pairs)

```python
class TrainingSnapshot(BaseModel):
    game_id: str
    turn: int
    step: str
    priority_player: int
    game_state: GameStateSnapshot
    legal_actions: List[Dict]  # Actions AI can take
    chosen_action: Optional[Dict]  # What AI actually did
```

### Decision Transcript (play-by-play)

```python
class DecisionTranscript(BaseModel):
    game_id: str
    event_sequence: List[GameEvent]

class GameEvent(BaseModel):
    timestamp: datetime
    event_type: str  # "spell_cast", "ability_resolved", "damage_dealt", ...
    player: int
    description: str
    rules_citations: List[str]  # e.g., ["CR 601.2", "CR 702.2a"]
    stack_before: List[StackSnapshot]
    stack_after: List[StackSnapshot]
```

### Rules Q&A Pair

```python
class RulesQA(BaseModel):
    game_id: str
    question: str  # e.g., "Can I respond to a split-second spell?"
    answer: str  # "No, CR 702.60b"
    context: Dict  # Game state when question arose
    trigger_event: str  # What triggered the rules question
```

### Outcome Record

```python
class OutcomeRecord(BaseModel):
    game_id: str
    winner: int  # 0 or 1
    loss_reason: str  # e.g., "life_total_zero", "deck_out", "surrender"
    turn_count: int
    duration_seconds: float
    training_tags: List[str]  # e.g., ["trample", "deathtouch", "stack_interaction"]
```

---

## Validation Summary

| Field | Validation | Enforced By |
|-------|------------|-------------|
| Player ID | 0 or 1 | Pydantic model validator |
| Life total | ≥ 0 | Pydantic + SBA |
| Deck size | ≥ 0 | Pydantic + SBA |
| Zone ownership | Matches player | Pydantic + game logic |
| Stack order | Bottom → top | Game logic |
| Target legality | Valid targets | Action validator |
| Mana payment | Sufficient mana | Action validator |
| Summoning sickness | Respects haste | Action validator |
| Layer ordering | CR 613 compliant | Layer engine |
| Replacement ordering | CR 616 compliant | Replacement engine |

---

## Notes

- All models use Pydantic v2 `BaseModel` with `model_config = ConfigDict(extra='forbid')`
- All fields are type-annotated for Python 3.11+
- All models support `model_dump_json()` for training data export
- Models are immutable after creation (no `update()` methods)
- Game state mutations go through `GameAction` commands, not direct field assignment

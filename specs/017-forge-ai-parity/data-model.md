# Data Model: Forge AI Parity

**Branch**: `017-forge-ai-parity` | **Date**: 2026-03-25

---

## New AI Client Entities

### `AIMemory`

Per-game, per-player structure tracking cross-turn game state. One instance per player per game, passed as a parameter to all `HeuristicPlayer` decision methods.

```
AIMemory
├── revealed_cards: dict[str, list[Card]]
│     # Opponent cards learned through effects; keyed by player name
├── bounced_this_turn: set[str]
│     # Permanent IDs returned to hand this turn (cleared at AI's turn start)
├── attached_this_turn: set[str]
│     # Equipment permanent IDs attached this turn (cleared at turn start)
├── animated_this_turn: set[str]
│     # Permanent IDs animated into creatures this turn (cleared at turn start)
├── chosen_fog_effect: str | None
│     # Card ID of Fog spell being held for defensive use (cleared on use)
├── trick_attackers: set[str]
│     # Attacker permanent IDs designated as trick bait this combat
│     # (attack to provoke block → cast pump instant at declare-blockers)
├── mandatory_attackers: set[str]
│     # Permanent IDs of goaded or must-attack creatures (cleared when effect ends)
├── held_mana_for_main2: set[str]
│     # Land/mana-source IDs held back from main phase 1 activations
└── held_mana_for_declblk: set[str]
      # Mana-source IDs reserved for combat-step instant-speed responses
```

**Lifecycle**: Created in `game_loop.py` at game start (one per AI player). Passed into every `HeuristicPlayer.choose_action()` call. Per-turn fields are cleared by `AIMemory.new_turn()` called at the start of each AI turn.

---

### `AiPersonalityProfile`

Named configuration controlling all behavioral probability and boolean properties. Bound to a player instance; not global.

```
AiPersonalityProfile
│
├── name: str                              # e.g. "default", "aggro"
│
├── # Combat aggression
├── chance_to_attack_into_trade: float     # default 0.40
├── attack_into_trade_when_tapped_out: bool  # default False
├── chance_to_atktrade_when_opp_has_mana: float  # default 0.30
├── try_to_avoid_attacking_into_certain_block: bool  # default True
├── enable_random_favorable_trades_on_block: bool  # default True
├── randomly_trade_even_when_have_less_creatures: bool  # default False
├── chance_decrease_to_trade_vs_embalm: float  # default 0.50
│
├── # Combat tricks
├── chance_to_hold_combat_tricks: float    # default 0.30
│
├── # Planeswalker protection
├── chance_to_trade_to_save_planeswalker: float  # default 0.70
│
├── # Counter behavior (probabilities per CMC tier)
├── chance_to_counter_cmc_1: float         # default 0.50
├── chance_to_counter_cmc_2: float         # default 0.75
├── chance_to_counter_cmc_3_plus: float    # default 1.00
│
├── # Counter boolean flags
├── always_counter_other_counterspells: bool  # default True
├── always_counter_damage_spells: bool        # default False
├── always_counter_removal_spells: bool       # default False
├── always_counter_pump_spells: bool          # default False
├── always_counter_auras: bool                # default False
│
├── # Removal behavior
├── actively_destroy_artifacts_and_enchantments: bool  # default True
├── actively_destroy_immediately_unblockable: bool     # default True
│
├── # Token generation
├── token_generation_chance: float         # default 0.80
│
├── # Land/mana management
├── hold_land_drop_for_main2_if_unused: bool  # default False
├── re_equip_on_creature_death: bool          # default True
│
└── # Phyrexian mana
    phyrexian_life_threshold: int          # default 5
```

**Built-in profiles**:
- `AiPersonalityProfile.DEFAULT` — all defaults as above
- `AiPersonalityProfile.AGGRO` — `chance_to_attack_into_trade=0.8`, `attack_into_trade_when_tapped_out=True`, `chance_to_counter_cmc_1=0.0`, `chance_to_counter_cmc_2=0.25`, `token_generation_chance=0.9`

---

### `BlockClassification` (Enum)

```
BlockClassification
├── SAFE    # Blocker kills attacker AND blocker survives
├── TRADE   # Both die (mutual lethal)
└── CHUMP   # Only blocker dies (attacker survives)
```

Used by `compute_block_declarations` to sort proposed blocks. Preference order: SAFE > TRADE > CHUMP, subject to lethal-avoidance override.

---

### `LookaheadSimulator`

Module: `ai_client/lookahead.py`

```
LookaheadSimulator
├── __init__(heuristic_player: HeuristicPlayer, max_depth: int = 1)
├── evaluate_bonus(current_action: dict, game_state: dict, memory: AIMemory) -> float
│     # Returns a bonus (0–30) added to the current action's heuristic score.
│     # Internally: deep-copies game_state, applies current_action to the copy,
│     # scores all actions the AI would have next turn, returns
│     # scaled_best_future_score capped at 30.
└── _apply_action_to_state(action: dict, state: dict) -> dict
      # Lightweight state mutation for lookahead (does not call engine API).
      # Handles: play_land (+1 land), cast spell (remove from hand, add to bf
      # for creatures), pass (advance step). Does NOT handle full rules resolution.
```

---

## Modified Existing Entities

### `PlayerConfig` (ai_client/models.py)

Add two new optional fields:

```
PlayerConfig (extended)
├── ... existing fields ...
├── personality: AiPersonalityProfile = AiPersonalityProfile.DEFAULT
└── memory: AIMemory | None = None   # set by game_loop at game start
```

### `LegalAction` (mtg_engine/models/actions.py)

Add fields to support new action types:

```
LegalAction (extended)
├── ... existing fields ...
├── loyalty_ability_index: int | None = None
│     # For action_type="activate_loyalty": which ability index
├── cascade_card_id: str | None = None
│     # For action_type="cascade_choice": the card being offered
└── from_graveyard: bool = False
      # True when this cast action originates from the graveyard zone
```

### `CastRequest` (mtg_engine/models/actions.py)

Already has `alternative_cost: Optional[str]`. No schema change needed. New values for `alternative_cost`:
- `"flashback"` — cast from graveyard, exile on resolution
- `"escape"` — cast from graveyard, exile N cards from graveyard
- `"unearth"` — cast from graveyard, exile at end of turn
- `"disturb"` — cast transformed DFC from graveyard
- `"convoke"` — tap creatures to reduce cost (targets = creature IDs to tap)
- `"delve"` — exile graveyard cards (targets = card IDs to exile)
- `"emerge"` — sacrifice a creature (targets[0] = creature ID to sacrifice)
- `"phyrexian"` — pay 2 life per Phyrexian mana symbol instead of colored mana

### New Request Model: `MulliganRequest`

```
MulliganRequest
├── player_name: str
└── keep: bool   # True = keep hand, False = discard and draw N−1
```

### New Request Model: `ActivateLoyaltyRequest`

```
ActivateLoyaltyRequest
├── permanent_id: str    # planeswalker permanent ID
└── ability_index: int   # 0 = first ability (usually +), 1 = second, 2 = ultimate
```

### New Request Model: `CascadeChoiceRequest`

```
CascadeChoiceRequest
├── player_name: str
├── card_id: str     # the cascaded card being offered
└── cast: bool       # True = cast it for free, False = exile it and skip
```

---

## State Transitions

### Game Start (with Mulligan Phase)

```
Game Created
    └── mulligan_phase_active = True
            └── AI calls evaluate_mulligan() → keep/mulligan decision
                    └── [if mulligan] → draw N−1 new cards, retry up to hand size 5
                    └── [if keep] → mulligan_phase_active = False, game proceeds
```

### Combat — Instant-Speed Trick Flow

```
AI's creatures attack
    ├── AI designates TRICK_ATTACKERS in AIMemory
    │       (creatures attacking to bait a block)
    ├── Engine grants priority at declare-blockers to non-active player
    │       (already happens — AI currently auto-passes)
    └── [NEW] AI evaluates instant-speed pump responses:
            ├── If pump saves TRICK_ATTACKER → cast pump (FR-016)
            └── Else → pass priority
```

### Cascade Resolution Flow

```
Cascade spell resolves
    └── Engine emits cascade_choice event on GameState
            └── Engine grants priority to controller
                    └── AI calls HeuristicPlayer.choose_action() with cascade_choice action
                            ├── [score > 0] → CascadeChoiceRequest(cast=True)
                            └── [score ≤ 0] → CascadeChoiceRequest(cast=False)
```

---

## Scoring Architecture

### HeuristicPlayer._score_action() dispatch table (extended)

```
action_type → scoring method
─────────────────────────────
pass              → 0.0 (unless holding trick/fog/counter: negative penalty)
play_land         → _score_play_land()
cast              → _score_cast()  [covers hand + graveyard casts]
activate          → _score_activate()  [covers equip, mana, fight, animate, remove-from-combat]
activate_loyalty  → _score_loyalty_ability()
declare_attackers → _score_attackers()
declare_blockers  → _score_blockers()  [now with SAFE/TRADE/CHUMP classification]
assign_combat_damage → 500.0  [always do it]
put_trigger       → 30.0
cascade_choice    → _score_cast(cascade card)
mulligan          → evaluate_mulligan()  [separate method]
```

### _score_cast() sub-dispatch (new/extended effects)

```
card type / oracle text → scoring branch
─────────────────────────────────────────
creature              → _score_creature()
  └── with ETB bonus  → +15/draw +10/damage +15/token
  └── with dies bonus → +10 trade-willingness
  └── with DFC bonus  → +TransformBonus
planeswalker          → +40 + loyalty×8
enchantment (aura)    → _score_aura()
instant/sorcery       → _score_noncreature_spell()
  ├── draw spell      → +15 per card drawn
  ├── ramp spell      → +(turns_of_accel × 20)
  ├── removal         → best_target_CMC × 12  (all targets considered)
  ├── burn            → lethal-first, then face-pressure
  ├── board wipe      → _score_board_wipe() (net CMC delta)
  ├── token producer  → _score_token_spell() × TOKEN_GENERATION_CHANCE
  ├── tutor/search    → _score_tutor()
  ├── fight           → _score_fight()
  ├── goad            → _score_goad()
  ├── life gain       → _score_life_gain()
  ├── life loss       → _score_life_loss()  [same formula as burn]
  ├── control steal   → stolen_CMC × 15
  ├── animate         → _score_animate()
  ├── remove-combat   → _score_remove_from_combat()
  ├── fog effect      → flag as CHOSEN_FOG_EFFECT, score 0 (held)
  └── modal (charm)   → max(_score for each valid mode)

graveyard casts (alternative_cost in {flashback,escape,unearth,disturb}):
  └── same as above + +10 free-resource bonus
```

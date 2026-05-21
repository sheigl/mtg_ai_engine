# TASKS: Forge Parity - Card Abilities Implementation

## Meta
- Spec: 037-forge-parity (SPEC.md)
- Plan: 037-forge-parity (plan.md)
- Status: **COMPLETED** (core features), **DEFERRED** (advanced features)

---

## COMPLETED TASKS ✅

### Phase REFACTOR: Core Architecture - DONE ✅

- [x] **EFF-01**: Create Effect Base Class Hierarchy - `ability/effects/base.py`
- [x] **EFF-02**: Implement DamageEffect - `base.py`
- [x] **EFF-03**: Implement DestroyEffect - `base.py`
- [x] **EFF-04**: Implement DrawEffect - `base.py`
- [x] **EFF-05**: Implement SearchEffect - `base.py`
- [x] **EFF-EXTRAS**: ExileEffect, CreateTokenEffect, GainLifeEffect

### Phase STATIC ABILITY - DONE ✅

- [x] **STA-01**: Create StaticAbility Base Class - `ability/staticability.py`
- [x] **STA-02**: Implement CantAttackBlock Ability - `staticability.py`
- [x] **STA-03**: Implement Continuous Pump Ability - `staticability.py`
- [x] **STA-04**: Hook Into SBA System - `engine/sba.py` (added `_apply_static_abilities()`)

### Phase TRIGGERS - DONE ✅

- [x] **TRG-01**: Expand Trigger Patterns (15→50) - `engine/triggers.py`
- All trigger categories implemented: cast, attack, block, upkeep, end_step, death, draw, damage, etb, ltb, end_turn, combat_start, discard, token, counter, landfall, planeswalk, face_up

### Phase ETB/LTB - DONE ✅

- [x] **ETB-01**: ETB triggers - handled via TRIGGER_PATTERNS["etb"]
- [x] **ETB-02**: LTB triggers - handled via TRIGGER_PATTERNS["ltb"]

### Phase LAYERS - DONE ✅

- [x] **LAY-01**: Static ability application - implemented in sba.py `_apply_static_abilities()`

---

## IMPLEMENTATION SUMMARY

| Category | Target | Implemented | Status |
|----------|--------|-------------|--------|
| Effect classes | 7+ | 7 | ✅ |
| Static abilities | 5+ | 5 | ✅ |
| Trigger patterns | 50+ | 50+ | ✅ |
| Trigger categories | 18 | 18 | ✅ |

**Test Results**: 518 passing, 1 pre-existing failure

---

## DEFERRED TASKS - EXPANDED

### PHASE 100: PARSER ENHANCEMENTS - DONE ✅

Tasks from plan.md (lines 89-106):

#### Task PAR-01: Extend Keyword Support ✅
- **Description**: Extend keyword support from 20 to 50+ keywords
- **Files**: `mtg_engine/card_data/ability_parser.py`
- **Tests**: `tests/card_data/test_keywords.py`
- **Acceptance**: 50+ keywords recognized
- **Dependency**: None

#### Task PAR-02: Extended Effect Patterns ✅
- **Description**: Extend effect patterns from 30 to 50+
- **Files**: `mtg_engine/card_data/ability_parser.py`
- **Tests**: `tests/card_data/test_effects.py`
- **Acceptance**: 50+ effect patterns parsed
- **Dependency**: PAR-01

#### Task PAR-03: Targeting Support ✅
- **Description**: Add targeting pattern support (targeted abilities)
- **Files**: `mtg_engine/card_data/ability_parser.py`
- **Tests**: `tests/card_data/test_targeting.py`
- **Acceptance**: Target selection patterns work
- **Dependency**: PAR-01

### PHASE 200: ACTIVATED ABILITIES ✅

Tasks from plan.md (lines 99-106):

#### Task ACT-01: Full Cost Payment System ✅
- **Description**: Full cost payment (mana, tap, sacrifice, exile)
- **Files**: `mtg_engine/ability/cost.py`
- **Tests**: `tests/ability/test_cost.py`
- **Acceptance**: All cost types handled
- **Dependency**: PAR-01

#### ACT-02: Timing Restrictions ✅
- **Description**: Timing restrictions for activated abilities
- **Files**: `mtg_engine/ability/timing.py`
- **Tests**: `tests/ability/test_timing.py`
- **Acceptance**: "Only during main phase" works
- **Dependency**: PAR-01, PAR-02

#### ACT-03: Loyalty Abilities ✅
- **Description**: Planeswalker loyalty ability system
- **Files**: `mtg_engine/ability/loyalty.py`
- **Tests**: `tests/ability/test_loyalty.py`
- **Acceptance**: Loyalty abilities work
- **Dependency**: ACT-01, ACT-02

### PHASE 300: LAYERS ADVANCED

#### LAY-02: Layer Dependency Tracking ✅
- **Description**: Layer dependency tracking (CR 611.1b)
- **Files**: `mtg_engine/engine/layers.py`
- **Tests**: `tests/engine/test_layer_deps.py`
- **Acceptance**: Dependencies resolve correctly
- **Dependency**: LAY-01

---

## GAP CLOSURE TASKS (SPEC.md)

Implementation gaps from SPEC.md that need specific tasks:

### PHASE 400: KEYWORD GAP CLOSURE - DONE ✅

From SPEC.md line 108 (Keyword Directory - 34 files vs 1):

#### KW-01: Keyword Base Class ✅
- **Description**: Create keyword ability base class hierarchy
- **Files**: `mtg_engine/ability/keywords/base.py`
- **Tests**: `tests/ability/keywords/test_base.py`
- **Acceptance**: Base class with apply() interface
- **Dependency**: None

#### KW-02: EtbKeywords (ETB Triggers) ✅
- **Description**: Implement enters Battlefield triggers from keywords
- **Files**: `mtg_engine/ability/keywords/etb.py`
- **Tests**: `tests/ability/keywords/test_etb.py`
- **Acceptance**: "Etb" keyword working
- **Dependency**: KW-01

#### KW-03: LeaveBattlefieldKeywords (LTB) ✅
- **Description**: Implement leaves Battlefield triggers
- **Files**: `mtg_engine/ability/keywords/leave.py`
- **Tests**: `tests/ability/keywords/test_leave.py`
- **Acceptance**: "Leaves battlefield" working
- **Dependency**: KW-02

#### KW-04: Counter Keywords (+1/+1, -1/-1) ✅
- **Description**: Implement counter placement keywords
- **Files**: `mtg_engine/ability/keywords/counter.py`
- **Tests**: `tests/ability/keywords/test_counter.py`
- **Acceptance**: Adds/removes counters
- **Dependency**: KW-01

#### KW-05: Level Up Keyword ✅
- **Description**: Implement level up ability
- **Files**: `mtg_engine/ability/keywords/level.py`
- **Tests**: `tests/ability/keywords/test_level.py`
- **Acceptance**: Level counters work
- **Dependency**: KW-04

#### KW-06: Toxic Keyword ✅
- **Description**: Implement toxic (poison counters)
- **Files**: `mtg_engine/ability/keywords/toxic.py`
- **Tests**: `tests/ability/keywords/test_toxic.py`
- **Acceptance**: Toxic works
- **Dependency**: KW-04

#### KW-07: Meld Keyword ✅
- **Description**: Implement meld ability
- **Files**: `mtg_engine/ability/keywords/meld.py`
- **Tests**: `tests/ability/keywords/test_meld.py`
- **Acceptance**: Meld works
- **Dependency**: KW-01

#### KW-08: TypeCycling Keyword ✅
- **Description**: Implement type cycling
- **Files**: `mtg_engine/ability/keywords/cycle.py`
- **Tests**: `tests/ability/keywords/test_cycle.py`
- **Acceptance**: Type cycling works
- **Dependency**: PAR-01

### PHASE 500: COMBAT SYSTEM ENHANCEMENT - DONE ✅

From SPEC.md line 74 (Combat Directory - 10 files vs 1):

#### CMB-01: Attack Requirements ✅
- **Description**: Implement attack restrictions/requirements
- **Files**: `mtg_engine/engine/combat/requirements.py`
- **Tests**: `tests/engine/combat/test_requirements.py`
- **Acceptance**: "Must attack" works
- **Dependency**: None

#### CMB-02: Cannot Block Abilities ✅
- **Description**: Implement cannot block
- **Files**: `mtg_engine/engine/combat/blocking.py`
- **Tests**: `tests/engine/combat/test_blocking.py`
- **Acceptance**: "Cannot block" works
- **Dependency**: None

#### CMB-03: Banding Support ✅
- **Description**: Implement banding
- **Files**: `mtg_engine/engine/combat/banding.py`
- **Tests**: `tests/engine/combat/test_banding.py`
- **Acceptance**: Banding works
- **Dependency**: None

#### CMB-04: Flanking Support ✅
- **Description**: Implement flanking keyword
- **Files**: `mtg_engine/ability/keywords/flanking.py`
- **Tests**: `tests/ability/keywords/test_flanking.py`
- **Acceptance**: Flanking works
- **Dependency**: KW-01

#### CMB-05: Multi-Block Restriction ✅
- **Description**: Handle "can only block creatures"
- **Files**: `mtg_engine/engine/combat/blocking.py`
- **Tests**: `tests/engine/combat/test_canonlyblock.py`
- **Acceptance**: "Can only block" works
- **Dependency**: CMB-02

### PHASE 600: MANA SYSTEM ✅

From SPEC.md line 124 (Mana Directory - 6 files vs 1):

#### MANA-01: Mana Pool Enhancement ✅
- **Description**: Enhance mana pool with split/colored mana
- **Files**: `mtg_engine/engine/mana.py`
- **Tests**: `tests/engine/test_mana.py`
- **Acceptance**: Colored mana works
- **Dependency**: None

#### MANA-02: Mana Abilities (Land) ✅
- **Description**: Full land mana ability support
- **Files**: `mtg_engine/engine/mana.py`
- **Tests**: `tests/engine/test_mana_abilities.py`
- **Acceptance**: Basic land mana works
- **Dependency**: MANA-01

#### MANA-03: Mana Production Events ✅
- **Description**: Trigger on mana production
- **Files**: `mtg_engine/engine/mana.py`, `engine/triggers.py`
- **Tests**: `tests/engine/test_mana_trigger.py`
- **Acceptance**: "Whenever mana is tapped" works
- **Dependency**: TRG-01

### PHASE 700: ZONE ENHANCEMENTS - DONE ✅

From SPEC.md line 188 (Zone Directory - 8 files vs 1):

#### ZN-01: Exile Zone Enhancement ✅
- **Description**: Handle exile zone properly with grouping/reason tracking
- **Files**: `mtg_engine/engine/zones.py`, `mtg_engine/models/game.py`
- **Tests**: `tests/rules/test_zones_enhanced.py`
- **Acceptance**: Exile stacks with reason tracking, face-down support, CRUD operations
- **Dependency**: None

#### ZN-02: Graveyard Enhancement ✅
- **Description**: Handle graveyard with ordering/search/reorder
- **Files**: `mtg_engine/engine/zones.py`
- **Tests**: `tests/rules/test_zones_enhanced.py`
- **Acceptance**: Graveyard top, search by name/type, reorder support
- **Dependency**: None

#### ZN-03: Command Zone ✅
- **Description**: Command zone support with move functions
- **Files**: `mtg_engine/engine/zones.py`
- **Tests**: `tests/rules/test_zones_enhanced.py`
- **Acceptance**: Command zone CRUD, commander redirect
- **Dependency**: None

#### ZN-04: Sideboard ✅
- **Description**: Add sideboard zone with swap mechanism
- **Files**: `mtg_engine/engine/zones.py`, `mtg_engine/models/game.py`
- **Tests**: `tests/rules/test_zones_enhanced.py`
- **Acceptance**: Sideboard zone, swap cards, search
- **Dependency**: None

### PHASE 800: REPLACEMENT EFFECTS - DONE ✅

From SPEC.md line 152 (Replacement Directory - 46 files vs ~1):

#### REP-01: Prevention Effects ✅
- **Description**: Damage prevention system
- **Files**: `mtg_engine/engine/replacement.py`
- **Tests**: `tests/engine/test_replacement_phase800.py`
- **Acceptance**: "Prevent damage" works
- **Dependency**: None

#### REP-02: Replacement Draw ✅
- **Description**: Card draw replacement
- **Files**: `mtg_engine/engine/replacement.py`
- **Tests**: `tests/engine/test_replacement_phase800.py`
- **Acceptance**: "If you would draw" works
- **Dependency**: None

#### REP-03: Effect Duration ✅
- **Description**: "Until end of turn" effects
- **Files**: `mtg_engine/engine/duration.py`
- **Tests**: `tests/engine/test_replacement_phase800.py`
- **Acceptance**: Duration tracking works
- **Dependency**: None

### PHASE 900: COST PAYMENT - DONE ✅

From SPEC.md line 90 (Cost Directory - 51 files vs ~1):

#### CST-01: Sacrfice Cost ✅
- **Description**: Handle sacrifice costs
- **Files**: `mtg_engine/ability/cost.py`
- **Tests**: `tests/ability/test_cost.py`
- **Acceptance**: Sacrifice costs work
- **Dependency**: None

#### CST-02: Exile Cost ✅
- **Description**: Handle exile from deck/grave costs
- **Files**: `mtg_engine/ability/cost.py`
- **Tests**: `tests/ability/test_cost.py`
- **Acceptance**: Exile costs work
- **Dependency**: None

#### CST-03: Discard Cost ✅
- **Description**: Handle discard costs
- **Files**: `mtg_engine/ability/cost.py`
- **Tests**: `tests/ability/test_cost.py`
- **Acceptance**: Discard costs work
- **Dependency**: None

#### CST-04: Life Cost ✅
- **Description**: Handle life payment costs
- **Files**: `mtg_engine/ability/cost.py`
- **Tests**: `tests/ability/test_cost.py`
- **Acceptance**: Life costs work
- **Dependency**: None

### PHASE 1000: CARD TYPE SUPPORT

From SPEC.md (Card Types - various):

#### CT-01: CardType Model ✅
- **Description**: Structured card type model with CoreType, Supertype enums and type line parsing
- **Files**: `mtg_engine/models/card_type.py`
- **Tests**: `tests/models/test_card_type.py` (23 tests, all passing)
- **Acceptance**: CoreType, Supertype enums; parse_type_line() function; CardType model with helper methods
- **Dependency**: None

#### CT-02: Enchantment Type ✅
- **Description**: Enchantment sub-types (Aura, Cartouche, Saga, Shrine, etc) with Aura targeting logic
- **Files**: `mtg_engine/models/enchantment.py`, `mtg_engine/models/card_type.py` (updated)
- **Tests**: `tests/models/test_enchantment.py` (47 tests, all passing)
- **Acceptance**: EnchantmentSubtype enum with 12 subtypes; AuraTarget parsing from oracle text; can_enchant_permanent() validation; is_attachment() helper
- **Dependency**: CT-01

#### CT-03: Artifact Type ✅
- **Description**: Artifact sub-types (Equipment, Vehicle) with equip cost parsing and crew logic
- **Files**: `mtg_engine/models/artifact.py`, `mtg_engine/models/card_type.py` (updated)
- **Tests**: `tests/models/test_artifact.py` (48 tests, all passing)
- **Acceptance**: ArtifactSubtype enum (Equipment, Fortification, Vehicle); parse_equip_cost(); parse_crew_cost(); can_equip() validation; EquipmentModel and VehicleModel with crew()/uncrew()
- **Dependency**: CT-01

#### CT-04: Battle Type (NEW 2024)
- **Description**: Battle card type support
- **Files**: `mtg_engine/models/battle.py`
- **Tests**: `tests/models/test_battle.py`
- **Acceptance**: Battles work
- **Dependency**: CT-01

#### CT-05: Saga Type
- **Description**: Saga card support with chapter counters
- **Files**: `mtg_engine/models/saga.py`
- **Tests**: `tests/models/test_saga.py`
- **Acceptance**: Saga chapters work
- **Dependency**: KW-04

### PHASE 1100: SPELLABILITY ENHANCEMENT

From SPEC.md (SpellAbility - 23 files vs ~1):

#### SPL-01: Spell Target Validation
- **Description**: Validate spell targets
- **Files**: `mtg_engine/engine/stack.py`
- **Tests**: `tests/engine/test_stack_targets.py`
- **Acceptance**: Target validation works
- **Dependency**: PAR-03

#### SPL-02: Overload Ability
- **Description**: Implement overload keyword
- **Files**: `mtg_engine/ability/keywords/overload.py`
- **Tests**: `tests/ability/keywords/test_overload.py`
- **Acceptance**: Overload works
- **Dependency**: KW-01

#### SPL-03: Split Second
- **Description**: Implement split second
- **Files**: `mtg_engine/ability/keywords/split_second.py`
- **Tests**: `tests/ability/keywords/test_split_second.py`
- **Acceptance**: Split second works
- **Dependency**: KW-01

### PHASE 1200: ADDITIONAL KEYWORDS

Additional high-value keywords missing (from SPEC.md):

#### KW-09: Infect/ Poison
- **Description**: Implement infect (damage as poison)
- **Files**: `mtg_engine/ability/keywords/infect.py`
- **Tests**: `tests/ability/keywords/test_infect.py`
- **Acceptance**: Infect works
- **Dependency**: KW-06

#### KW-10: Lifelink Enhancement
- **Description**: Ensure lifelink works properly
- **Files**: `mtg_engine/ability/keywords/lifelink.py`
- **Tests**: `tests/ability/keywords/test_lifelink.py`
- **Acceptance**: Lifelink works
- **Dependency**: KW-01

#### KW-11: Deathtouch Enhancement
- **Description**: Ensure deathtouch works properly
- **Files**: `mtg_engine/ability/keywords/deathtouch.py`
- **Tests**: `tests/ability/keywords/test_deathtouch.py`
- **Acceptance**: Deathtouch works
- **Dependency**: KW-01

#### KW-12: Reach Enhancement
- **Description**: Ensure reach works (flying vs reach)
- **Files**: `mtg_engine/ability/keywords/reach.py`
- **Tests**: `tests/ability/keywords/test_reach.py`
- **Acceptance**: Reach works
- **Dependency**: KW-01

#### KW-13: Menace Enhancement
- **Description**: Ensure menace works
- **Files**: `mtg_engine/ability/keywords/menace.py`
- **Tests**: `tests/ability/keywords/test_menace.py`
- **Acceptance**: Menace works
- **Dependency**: KW-01, CMB-02

#### KW-14: Hexproof Enhancement
- **Description**: Ensure hexproof works
- **Files**: `mtg_engine/ability/keywords/hexproof.py`
- **Tests**: `tests/ability/keywords/test_hexproof.py`
- **Acceptance**: Hexproof works
- **Dependency**: KW-01

#### KW-15: Shroud Enhancement
- **Description**: Ensure shroud works
- **Files**: `mtg_engine/ability/keywords/shroud.py`
- **Tests**: `tests/ability/keywords/test_shroud.py`
- **Acceptance**: Shroud works  
- **Dependency**: KW-01

---

### PHASE 1300: EVENT SYSTEM - DEFERRED

From forge `event/` directory (63 files):

#### EVT-01: Event Bus Infrastructure
- **Description**: Create typed event notification bus (AttackEvent, BlockEvent, DamageEvent, ZoneChangeEvent, PhaseChangeEvent, etc.)
- **Files**: `mtg_engine/engine/events.py`
- **Tests**: `tests/engine/test_events.py`
- **Acceptance**: Events fire and triggers subscribe correctly
- **Dependency**: None

#### EVT-02: Event-to-Trigger Bridge
- **Description**: Connect event bus to trigger system so triggers react to typed events
- **Files**: `mtg_engine/engine/events.py`, `mtg_engine/engine/triggers.py`
- **Tests**: `tests/engine/test_event_triggers.py`
- **Acceptance**: All existing trigger patterns work via event bus
- **Dependency**: EVT-01, TRG-01

### PHASE 1400: CARD MODEL ENHANCEMENT - DEFERRED

From forge `card/` directory (38 files):

#### CRD-01: Card Type System
- **Description**: Implement full card type hierarchy with all subtypes (Artifact, Creature, Enchantment, Instant, Sorcery, Planeswalker, Battle, etc.)
- **Files**: `mtg_engine/models/card_types.py`
- **Tests**: `tests/models/test_card_types.py`
- **Acceptance**: All card types/subtypes recognized
- **Dependency**: CT-01..05

#### CRD-02: Card Factory
- **Description**: Card creation factory matching Forge's CardFactory
- **Files**: `mtg_engine/card_data/card_factory.py`
- **Tests**: `tests/card_data/test_card_factory.py`
- **Acceptance**: Cards can be created from oracle text
- **Dependency**: CRD-01, PAR-01

### PHASE 1500: MULLIGAN SYSTEM - DEFERRED

From forge `mulligan/` directory (7 files):

#### MLG-01: Mulligan Types
- **Description**: Implement London mulligan, Vancouver mulligan, etc.
- **Files**: `mtg_engine/engine/mulligan.py`
- **Tests**: `tests/engine/test_mulligan.py`
- **Acceptance**: Mulligan rules work per variant
- **Dependency**: None

### PHASE 1600: PLAYER ACTIONS - DEFERRED

From forge `player/actions/` directory (28 files):

#### PLA-01: Player Action Models
- **Description**: Model player decision types (play land, cast spell, activate ability, declare attackers, etc.)
- **Files**: `mtg_engine/models/player_actions.py`
- **Tests**: `tests/models/test_player_actions.py`
- **Acceptance**: All player action types modeled with validation
- **Dependency**: None

### PHASE 1700: AI SYSTEM - DEFERRED

From forge `forge-ai/` module (187 files):

#### AI-01: AI Decision Framework
- **Description**: Create AI decision-making framework (evaluation, scoring, selection)
- **Files**: `mtg_engine/ai/`
- **Tests**: `tests/ai/test_ai_framework.py`
- **Acceptance**: AI can evaluate game state and select actions
- **Dependency**: PAR-01, ACT-01

#### AI-02: AI Combat
- **Description**: AI attack/block decisions (AiAttackController, AiBlockController parity)
- **Files**: `mtg_engine/ai/combat.py`
- **Tests**: `tests/ai/test_ai_combat.py`
- **Acceptance**: AI makes reasonable combat decisions
- **Dependency**: AI-01, CMB-01..05

#### AI-03: AI Card Evaluation
- **Description**: AI card evaluation (ComputerUtilCard, ComputerUtilAbility parity)
- **Files**: `mtg_engine/ai/card_eval.py`
- **Tests**: `tests/ai/test_card_eval.py`
- **Acceptance**: AI can evaluate card quality
- **Dependency**: AI-01

## QUICK START

### Priority Order

1. **PARSER** (PAR-01, PAR-02, PAR-03) - Foundation for everything
2. **KEYWORDS** (KW-02 to KW-06) - Build on parser
3. **ACTIVATED** (ACT-01, ACT-02, ACT-03) - Build on parser
4. **COMBAT** (CMB-01, CMB-02) - High impact abilities
5. **ZONES** (ZN-01, ZN-02) - Foundation
6. **COST** (CST-01 to CST-04) - Build on activated
7. **CARD TYPES** (CT-01 to CT-03) - Build on keywords
8. **SPELLABILITY** (SPL-01 to SPL-03) - Build on parser

### Good First Issues

1. PAR-01 (Extend keywords) - straightforward addition
2. KW-02 (EtbKeywords) - follows existing patterns
3. ACT-02 (Timing restrictions) - logic focused

### Run Tests

```bash
pytest tests/card_data/        # Parser tasks
pytest tests/ability/keywords/ # Keyword tasks  
pytest tests/engine/combat/    # Combat tasks
pytest tests/engine/          # Layer tasks
```
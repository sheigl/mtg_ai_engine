# PLAN: Forge Parity - Card Abilities Implementation

## Overview
Comprehensive implementation to match Forge's card ability handling. Gap analysis complete in SPEC.md. This plan outlines specific implementation tasks.

## Status: INCOMPLETE - EXTENSIVE GAPS (UPDATED)

## COMPLETE GAP LIST FROM FORGE ANALYSIS:

| Category | Forge Count | Our Count | Gap |
|----------|-------------|----------|-----|
| Trigger Types | 159 | ~10 | **149** |
| Keywords | ~200 | ~20 | **180** |
| Effect/Api Types | ~220 | ~13 | **207** |
| Replacement Types | 41 | ~5 | **36** |
| Layer System | 10 | 3 | **7** |

### ADDITIONAL GAPS DISCOVERED:

| Category | Forge Count | Our Count | Gap |
|----------|-------------|----------|-----|
| Card Types | 15+ | 5 | **10+** |
| Game Variants | 12+ | 2 | **10+** |
| Combat System | Full | Basic | **Large** |
| Cost Payment | Full | Partial | **Large** |
| Zone Management | 10+ zones | 5 | **5+** |
| AI System | Extensive | Basic | **Large** |

## Dependencies
- 036-spree (complete) - Spree mechanic handling
- Previous specs for base engine features

## Phases

### Phase REFACTOR: Core Architecture (3 sprints)

#### Sprint 1: Effect Class Hierarchy

| Task | Description | Files | Points |
|------|------------|-------|--------|
| EFF-01 | Create effect base class hierarchy | `ability/effects/*.py` | 5 |
| EFF-02 | Implement DamageEffect with prevention | `ability/effects/damage.py` | 3 |
| EFF-03 | Implement DestroyEffect with indestructible | `ability/effects/destroy.py` | 2 |
| EFF-04 | Implement DrawEffect with shuffle | `ability/effects/draw.py` | 2 |
| EFF-05 | Implement SearchEffect for tutoring | `ability/effects/search.py` | 2 |

#### Sprint 2: Static Ability System

| Task | Description | Files | Points |
|------|------------|-------|--------|
| STA-01 | Create StaticAbility base class | `ability/staticability.py` | 5 |
| STA-02 | Implement CantAttackBlock ability | `ability/staticability/*.py` | 2 |
| STA-03 | Implement continuous P/T modifiers | `ability/staticability/pump.py` | 3 |
| STA-04 | Hook into SBA system | `engine/sba.py` | 2 |

#### Sprint 3: Replacement Effects

| Task | Description | Files | Points |
|------|------------|-------|--------|
| REP-01 | Refactor replacement to class hierarchy | `ability/replacement.py` | 5 |
| REP-02 | Implement prevention replacement | `ability/replacement/damage.py` | 2 |

### Phase TRIGGERS: Trigger System Expansion (3 sprints)

#### Sprint 4: Trigger Parser Expansion

| Task | Description | Files | Points |
|------|------------|-------|--------|
| TRG-01 | Expand trigger patterns (15 → 50) | `engine/triggers.py` | 5 |
| TRG-02 | Add phase-restricted triggers | `engine/triggers.py` | 3 |
| TRG-03 | Add condition-based triggers | `engine/triggers.py` | 3 |

#### Sprint 5: ETB/LTB System

| Task | Description | Files | Points |
|------|------------|-------|--------|
| ETB-01 | Add enters battlefield handler | `engine/triggers.py` | 5 |
| ETB-02 | Add leaves battlefield handler | `engine/triggers.py` | 3 |
| ETB-03 | Handle "champion" triggers | `engine/triggers.py` | 2 |

#### Sprint 6: Advanced Triggers

| Task | Description | Files | Points |
|------|------------|-------|--------|
| TRG-04 | Add damage triggers | `engine/triggers.py` | 3 |
| TRG-05 | Add "whenever a player casts" | `engine/triggers.py` | 3 |
| TRG-06 | Multi-zone triggers (champion) | `engine/triggers.py` | 2 |

### Phase PARSER: Ability Parser Enhancement (2 sprints)

#### Sprint 7: Extended Parsing

| Task | Description | Files | Points |
|------|------------|-------|--------|
| PAR-01 | Extend keyword support (30 → 80) | `card_data/ability_parser.py` | 5 |
| PAR-02 | Extend effect patterns (30 → 80) | `card_data/ability_parser.py` | 5 |
| PAR-03 | Add targeting pattern support | `card_data/ability_parser.py` | 3 |

#### Sprint 8: Activated Abilities

| Task | Description | Files | Points |
|------|------------|-------|--------|
| ACT-01 | Full cost payment system | `ability/*abilities.py` | 5 |
| ACT-02 | Timing restrictions | `ability/*abilities.py` | 3 |
| ACT-03 | Loyalty abilities | `ability/*loyalty.py` | 3 |

### Phase LAYERS: Layer System (1 sprint)

#### Sprint 9: Layer Implementation

| Task | Description | Files | Points |
|------|------------|-------|--------|
| LAY-01 | Implement 7-layer system | `engine/layers.py` | 8 |
| LAY-02 | Layer dependency tracking | `engine/layers.py` | 3 |

## Task Count
- 26 tasks total
- 89 story points
- 9 sprints estimated

## Test Strategy

### Unit Tests (per task)
- Each effect class: 3-5 tests
- Each static ability: 2-3 tests
- Each trigger: 2-3 tests

### Integration Tests
- Tier 1-5 cards from SPEC.md
- Full game loops with multiple abilities
- Edge cases (multiple triggers, replacement stacking)

## Test Cards

### Phase Complete Tests
After REFACTOR:
- Dark Confidant (upkeep trigger)
- Wall of Roots (ETB)
- Darksteel Colossus (activated ability)

After TRIGGERS:
- Snapcaster Mage (ETB flash)
- Snapcaster Mage (flash from graveyard - cast trigger)
- Gifts Storm (noncreature cast trigger)

After PARSER:
- Sakura-Tribe Elder (activated + sacrifice)
- Birthing Pod (activated ability)

After LAYERS:
- Ghostly Prison (static ability)
- Archetype of Endurance (static + hexproof)

## Success Criteria

### Phase REFACTOR (35 pts)
- [ ] Effect classes handle 80%+ of spell effects
- [ ] Static abilities modify battlefiel correctly
- [ ] No performance regression

### Phase TRIGGERS (30 pts)
- [ ] 50+ trigger patterns working
- [ ] ETB/LTB triggers fire correctly
- [ ] APNAP ordering correct

### Phase PARSER (24 pts)
- [ ] 80+ keywords recognized
- [ ] 80+ effect patterns parsed
- [ ] Full cost system working

## Parallelization

- TRIGGERS can start after PARSER-01 (keyword support needed)
- LAYERS depends on REFACTOR (static ability needed)
- Other phases are mostly independent

## Notes

## Status: INCOMPLETE - EXTENSIVE GAPS

Core features implemented (see tasks.md). The following are DEFERRED and represent massive gaps:

### PHASE TRIGGERS-DEFERRED: Missing 149 Trigger Types
All 159 trigger types from SPEC.md need handlers. Added to tasks.md.

### PHASE KEYWORDS-DEFERRED: Missing ~180 Keywords
All ~200 Forge keywords need implementation. Added to tasks.md.

### PHASE EFFECTS-DEFERRED: Missing ~207 API Effects
All ~220 API effects need handlers. Added to tasks.md.

### PHASE REPLACEMENTS-DEFERRED: Missing ~36 Replacement Effects
All 41 replacement effects need handlers. Added to tasks.md.

### PHASE LAYERS-DEFERRED: Full 10-Layer System
Layer system needs full 10-layer CR 611.1 implementation. Added to tasks.md.

### PHASE COMBAT-DEFERRED: Full Combat System
Full combat with bands, restrictions, requirements. Added to tasks.md.
- Focus on test-driven development
- Each effect class should have tests before integration
- Document patterns for future extension
- Keep backwards compatibility with existing stack.py effects during transition
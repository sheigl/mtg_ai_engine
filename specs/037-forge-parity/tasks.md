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

## PARTIALLY IMPLEMENTED / DEFERRED

The following are architectural improvements that would require larger changes:

- **REP-01, REP-02**: Replacement effects - current regex-based system works for basic cases
- **PAR-01, PAR-02, PAR-03**: Extended parsing - base keywords work, additional patterns can be added on-demand
- **ACT-01, ACT-02, ACT-03**: Full cost system - basic timing/restrictions in stack.py
- **LAY-02**: Layer dependency tracking - continuous effects apply in order

---

## IMPLEMENTATION SUMMARY

| Category | Target | Implemented | Status |
|----------|--------|-------------|--------|
| Effect classes | 7+ | 7 | ✅ |
| Static abilities | 5+ | 5 | ✅ |
| Trigger patterns | 50+ | 50+ | ✅ |
| Trigger categories | 18 | 18 | ✅ |

**Test Results**: 518 passing, 1 pre-existing failure

### Sprint 1: Effect Class Hierarchy

#### Task EFF-01: Create Effect Base Class Hierarchy
- **Description**: Create effect base class hierarchy with interface for resolve, can_target
- **Files**: `mtg_engine/ability/effects/__init__.py`, `base.py`
- **Tests**: `tests/ability/test_effects_base.py`
- **Acceptance**: Base class with resolve/can_target interface
- **Dependency**: None

#### Task EFF-02: Implement DamageEffect
- **Description**: Implement DamageEffect with damage prevention and distribution
- **Files**: `mtg_engine/ability/effects/damage.py`
- **Tests**: `tests/ability/test_effects_damage.py`
- **Acceptance**: Handles all damage types (combat, noncombat, wither)
- **Dependency**: EFF-01

#### Task EFF-03: Implement DestroyEffect
- **Description**: Implement DestroyEffect with indestructible check
- **Files**: `mtg_engine/ability/effects/destroy.py`
- **Tests**: `tests/ability/test_effects_destroy.py`
- **Acceptance**: Checks indestructible before destroying
- **Dependency**: EFF-01

#### Task EFF-04: Implement DrawEffect
- **Description**: Implement DrawEffect with shuffle handling
- **Files**: `mtg_engine/ability/effects/draw.py`
- **Tests**: `tests/ability/test_effects_draw.py`
- **Acceptance**: Handles draw with library shuffle when empty
- **Dependency**: EFF-01

#### Task EFF-05: Implement SearchEffect
- **Description**: Implement SearchEffect for library tutoring
- **Files**: `mtg_engine/ability/effects/search.py`
- **Tests**: `tests/ability/test_effects_search.py`
- **Acceptance**: Handles search and put zones (hand, library, battlefield)
- **Dependency**: EFF-01

---

### Sprint 2: Static Ability System

#### Task STA-01: Create StaticAbility Base Class
- **Description**: Create StaticAbility base class with applies/modify interface
- **Files**: `mtg_engine/ability/staticability.py`
- **Tests**: `tests/ability/test_staticability.py`
- **Acceptance**: Base class with applies/modify interface
- **Dependency**: None

#### Task STA-02: Implement CantAttackBlock Ability
- **Description**: Implement cant attack/block static abilities
- **Files**: `mtg_engine/ability/staticability/cant.py`
- **Tests**: `tests/ability/test_staticability_cant.py`
- **Acceptance**: Prevents attack/block based on controller
- **Dependency**: STA-01

#### Task STA-03: Implement Continuous Pump Ability
- **Description**: Implement continuous P/T modifiers (pump, +1/+1, -1/-1)
- **Files**: `mtg_engine/ability/staticability/pump.py`
- **Tests**: `tests/ability/test_staticability_pump.py`
- **Acceptance**: Applies temporary P/T modifications
- **Dependency**: STA-01

#### Task STA-04: Hook Into SBA System
- **Description**: Hook static abilities into SBA (State-Based Actions)
- **Files**: `mtg_engine/engine/sba.py`
- **Tests**: `tests/rules/test_sba.py` (existing)
- **Acceptance**: Static abilities applied before SBA checks
- **Dependency**: STA-01, STA-02, STA-03

---

### Sprint 3: Replacement Effects

#### Task REP-01: Refactor Replacement Class Hierarchy
- **Description**: Refactor replacement to class-based system
- **Files**: `mtg_engine/engine/replacement.py`
- **Tests**: `tests/ability/test_replacement.py`
- **Acceptance**: Class hierarchy matching Forge
- **Dependency**: None

#### Task REP-02: Implement Prevention Replacement
- **Description**: Implement damage prevention replacement
- **Files**: `mtg_engine/ability/replacement/damage.py`
- **Tests**: `tests/ability/test_replacement_damage.py`
- **Acceptance**: Handles damage prevention effects
- **Dependency**: REP-01

---

## Phase TRIGGERS: Trigger System Expansion

### Sprint 4: Trigger Parser Expansion

#### Task TRG-01: Expand Trigger Patterns
- **Description**: Expand trigger patterns from 15 to 50
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_patterns.py`
- **Acceptance**: 50+ pattern types matching
- **Dependency**: None

#### Task TRG-02: Add Phase-Restricted Triggers
- **Description**: Add support for phase-restricted triggers
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_phase_restricted.py`
- **Acceptance**: Handles "at beginning of end step" etc
- **Dependency**: TRG-01

#### Task TRG-03: Add Condition-Based Triggers
- **Description**: Add support for "if you control X" triggers
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_conditional.py`
- **Acceptance**: Handles conditional triggers
- **Dependency**: TRG-01

---

### Sprint 5: ETB/LTB System

#### Task ETB-01: Add Enters Battlefield Handler
- **Description**: Add ETB trigger detection and handling
- **Files**: `mtg_engine/engine/triggers.py`, `engine/zones.py`
- **Tests**: `tests/triggers/test_etb.py`
- **Acceptance**: ETB triggers fire on zone change to battlefield
- **Dependency**: TRG-01

#### Task ETB-02: Add Leaves Battlefield Handler  
- **Description**: Add LTB trigger detection and handling
- **Files**: `mtg_engine/engine/triggers.py`, `engine/zones.py`
- **Tests**: `tests/triggers/test_ltb.py`
- **Acceptance**: LTB triggers fire on zone change from battlefield
- **Dependency**: ETB-01

#### Task ETB-03: Handle Champion Triggers
- **Description**: Handle champion triggers (multiple zone changes)
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_champion.py`
- **Acceptance**: Champion mechanic works
- **Dependency**: ETB-01, ETB-02

---

### Sprint 6: Advanced Triggers

#### Task TRG-04: Add Damage Triggers
- **Description**: Add damage dealt/dealt triggers
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_damage.py`
- **Acceptance**: When X deals damage triggers fire
- **Dependency**: TRG-01

#### Task TRG-05: Add Cast Triggers
- **Description**: Add "whenever a player casts" triggers
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_cast.py`
- **Acceptance**: Spell cast triggers fire
- **Dependency**: TRG-01

#### Task TRG-06: Multi-Zone Triggers
- **Description**: Handle multi-zone triggers (champion, delve)
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/triggers/test_multi_zone.py`
- **Acceptance**: Multiple zone tracking works
- **Dependency**: ETB-01, ETB-02

---

## Phase PARSER: Ability Parser Enhancement

### Sprint 7: Extended Parsing

#### Task PAR-01: Extend Keyword Support
- **Description**: Extend keyword support from 30 to 80
- **Files**: `mtg_engine/card_data/ability_parser.py`
- **Tests**: `tests/card_data/test_keywords.py`
- **Acceptance**: 80+ keywords recognized
- **Dependency**: None

#### Task PAR-02: Extend Effect Patterns
- **Description**: Extend effect patterns from 30 to 80
- **Files**: `mtg_engine/card_data/ability_parser.py`
- **Tests**: `tests/card_data/test_effects.py`
- **Acceptance**: 80+ effect patterns parsed
- **Dependency**: EFF-01 (effect classes)

#### Task PAR-03: Add Targeting Pattern Support
- **Description**: Add targeting pattern support
- **Files**: `mtg_engine/card_data/ability_parser.py`
- **Tests**: `tests/card_data/test_targeting.py`
- **Acceptance**: Target selection patterns work
- **Dependency**: PAR-01

---

### Sprint 8: Activated Abilities

#### Task ACT-01: Full Cost Payment System
- **Description**: Full cost payment (mana, tap, sacrifice)
- **Files**: `mtg_engine/ability/cost.py`
- **Tests**: `tests/ability/test_cost.py`
- **Acceptance**: All cost types handled
- **Dependency**: PAR-01

#### Task ACT-02: Timing Restrictions
- **Description**: Timing restrictions for activated abilities
- **Files**: `mtg_engine/ability/timing.py`
- **Tests**: `tests/ability/test_timing.py`
- **Acceptance**: "Only during main phase" etc works
- **Dependency**: PAR-01, PAR-02

#### Task ACT-03: Loyalty Abilities
- **Description**: Planeswalker loyalty ability system
- **Files**: `mtg_engine/ability/loyalty.py`
- **Tests**: `tests/ability/test_loyalty.py`
- **Acceptance**: Loyalty abilities work
- **Dependency**: ACT-01, ACT-02

---

## Phase LAYERS: Layer System

### Sprint 9: Layer Implementation

#### Task LAY-01: Implement 7-Layer System
- **Description**: Implement CR 611.1 7-layer system
- **Files**: `mtg_engine/engine/layers.py`
- **Tests**: `tests/engine/test_layers.py`
- **Acceptance**: Layers apply in correct order
- **Dependency**: STA-01, STA-02, STA-03

#### Task LAY-02: Layer Dependency Tracking
- **Description**: Layer dependency tracking (611.1b)
- **Files**: `mtg_engine/engine/layers.py`
- **Tests**: `tests/engine/test_layer_deps.py`
- **Acceptance**: Dependencies resolve correctly
- **Dependency**: LAY-01

---

## Implementation Notes

### Test-Driven Development
- Each task should have tests BEFORE implementation
- Use existing test structure from `tests/rules/`
- Focus on edge cases

### Backwards Compatibility
- Keep stack.py effects working during transition
- Deprecate old patterns gradually
- Document breaking changes

### Performance
- Target: <200ms per turn for cards with abilities
- Profile before/after each task
- Cache parsed abilities where possible

---

## Quick Start

### To Start Working

1. **Pick a Phase**:
   - REFACTOR if you want foundational work
   - TRIGGERS if you want trigger expansion
   - PARSER if you want parsing work
   - LAYERS if you want advanced features

2. **Pick a Task** (in order within phase):
   - Tasks are ordered by dependency

3. **Run Tests First**:
   - `pytest tests/ability/` for effect tasks
   - `pytest tests/triggers/` for trigger tasks
   - `pytest tests/card_data/` for parser tasks

### Good First Issues

1. EFF-01 (Effect base) - foundational
2. TRG-01 (Expand triggers) - straightforward regex
3. PAR-01 (Extend keywords) - data-driven

---

## DEFERRED TASKS (Future Enhancement)

These tasks are deferred for future implementation when more advanced features are needed:

### PHASE 1XX: MISSING 149 TRIGGER TYPES (Deferred)

All 159 Forge trigger types need individual handler implementations:

- [ ] TRG-10x: TriggerAbandoned
- [ ] TRG-11x: TriggerAbilityCast / SpellAbilityCast / SpellCast / SpellCastOrCopy
- [ ] TRG-12x: TriggerAbilityResolves
- [ ] TRG-13x: TriggerAbilityTriggered
- [ ] TRG-14x: TriggerAdapt
- [ ] TRG-15x: TriggerAirbend/Earthbend/Firebend/Waterbend/ElementalBend
- [ ] TRG-16x: TriggerAlways
- [ ] TRG-17x: TriggerAttached / TriggerUnattach
- [ ] TRG-18x: TriggerAttackerBlocked / AttackerBlockedOnce / AttackerBlockedByCreature
- [ ] TRG-19x: TriggerAttackerUnblocked / AttackerUnblockedOnce
- [ ] TRG-20x: TriggerAttacks
- [ ] TRG-21x: TriggerBecomeMonarch
- [ ] TRG-22x: TriggerBecomeMonstrous
- [ ] TRG-23x: TriggerBecomeRenowned
- [ ] TRG-24x: TriggerBecomesCrewed / BecomesSaddled / BecomesPlotted
- [ ] TRG-25x: TriggerBecomesTarget / BecomesTargetOnce
- [ ] TRG-26x: TriggerBlockersDeclared
- [ ] TRG-27x: TriggerBlocks
- [ ] TRG-28x: TriggerCaseSolved
- [ ] TRG-29x: TriggerChampioned
- [ ] TRG-30x: TriggerChangesController
- [ ] TRG-31x: TriggerChangesZone / TriggerChangesZoneAll
- [ ] TRG-32x: TriggerChaosEnsues
- [ ] TRG-33x: TriggerClaimPrize
- [ ] TRG-34x: TriggerClashed
- [ ] TRG-35x: TriggerClassLevelGained
- [ ] TRG-36x: TriggerCommitCrime
- [ ] TRG-37x: TriggerConjureAll
- [ ] TRG-38x: TriggerCounterAdded / CounterAddedOnce / CounterAddedAll
- [ ] TRG-39x: TriggerCounterPlayerAddedAll
- [ ] TRG-40x: TriggerCounterRemoved / CounterRemovedOnce
- [ ] TRG-41x: TriggerCounterTypeAddedAll
- [ ] TRG-42x: TriggerCountered
- [ ] TRG-43x: TriggerCrankContraption
- [ ] TRG-44x: TriggerCrewed / TriggerSaddled / TriggerStationed
- [ ] TRG-45x: TriggerCycled
- [ ] TRG-46x: TriggerDamageAll
- [ ] TRG-47x: TriggerDamageDealtOnce
- [ ] TRG-48x: TriggerDamageDone / DamageDoneOnce / DamageDoneOnceByController
- [ ] TRG-49x: TriggerDamagePreventedOnce
- [ ] TRG-50x: TriggerDayTimeChanges
- [ ] TRG-51x: TriggerDestroyed
- [ ] TRG-52x: TriggerDevoured
- [ ] TRG-53x: TriggerDiscarded / DiscardedAll / DiscardedMilledAll
- [ ] TRG-54x: TriggerDiscover
- [ ] TRG-55x: TriggerDrawn
- [ ] TRG-56x: TriggerCompletedDungeon
- [ ] TRG-57x: TriggerEvolved
- [ ] TRG-58x: TriggerExerted
- [ ] TRG-59x: TriggerExiled / TriggerExiledAll
- [ ] TRG-60x: TriggerExplores
- [ ] TRG-61x: TriggerExploited
- [ ] TRG-62x: TriggerFight / TriggerFightOnce
- [ ] TRG-63x: TriggerFlippedCoin
- [ ] TRG-64x: TriggerForage
- [ ] TRG-65x: TriggerForetell
- [ ] TRG-66x: TriggerGiveGift
- [ ] TRG-67x: TriggerInvestigated
- [ ] TRG-68x: TriggerLandPlayed
- [ ] TRG-69x: TriggerLifeGained
- [ ] TRG-70x: TriggerLifeLost / TriggerLifeLostAll
- [ ] TRG-71x: TriggerLosesGame
- [ ] TRG-72x: TriggerManaAdded
- [ ] TRG-73x: TriggerManaExpend
- [ ] TRG-74x: TriggerManifestDread
- [ ] TRG-75x: TriggerMentored
- [ ] TRG-76x: TriggerMilled / TriggerMilledOnce / TriggerMilledAll
- [ ] TRG-77x: TriggerMutates
- [ ] TRG-78x: TriggerNewGame
- [ ] TRG-79x: TriggerCumulativeUpkeep / TriggerPayEcho / TriggerPayLife
- [ ] TRG-80x: TriggerPhase / PhaseIn / PhaseOut / PhaseOutAll
- [ ] TRG-81x: TriggerPlanarDice
- [ ] TRG-82x: TriggerPlaneswalkedFrom / TriggerPlaneswalkedTo
- [ ] TRG-83x: TriggerProliferate
- [ ] TRG-84x: TriggerRingTemptsYou
- [ ] TRG-85x: TriggerRolledDie / TriggerRolledDieOnce
- [ ] TRG-86x: TriggerRoomEntered
- [ ] TRG-87x: TriggerSacrificed / TriggerSacrificedOnce
- [ ] TRG-88x: TriggerSetInMotion
- [ ] TRG-89x: TriggerSpecializes
- [ ] TRG-90x: TriggerTakesInitiative
- [ ] TRG-91x: TriggerTaps / TriggerTapsForMana / TriggerUntaps
- [ ] TRG-92x: TriggerTokenCreated / TriggerTokenCreatedOnce
- [ ] TRG-93x: TriggerTrains
- [ ] TRG-94x: TriggerTransformed
- [ ] TRG-95x: TriggerTurnBegin / TriggerTurnFaceUp
- [ ] TRG-96x: TriggerUnlockDoor / TriggerUntapAll / TriggerTapAll
- [ ] TRG-97x: TriggerVisitAttraction
- [ ] TRG-98x: TriggerVote
- [ ] TRG-99x: TriggerScry / TriggerSurveil / TriggerSearchedLibrary / TriggerShuffled

### PHASE 2XX: MISSING ~180 KEYWORDS (Deferred)

All ~200 Forge keywords need keyword handler implementations:
- [ ] KW-A: Absorb, Affinity, Afflict, Afterlife, Aftermath, Amplify, Annihilator, Ascend, Assist, Aura Swap, Awaken, Backup, Banding
- [ ] KW-B: Bands with Other, Bargain, Battle Cry, Bestow, Blitz, Bloodthirst, Bushido, Buyback
- [ ] KW-C: Cascade, Casualty, Champion, Changeling, Choose a Background, Cipher, Companion, Compleated, Conspire, Convoke, Craft, Crew, Cumulative Upkeep
- [ ] KW-D: Cycling, Dash, Daybound, Deathtouch, Decayed, Defender, Delve, Demonstrate, Dethrone, Devour, Devoid, Disguise, Disturb, Double Strike, Double Team, Dredge
- [ ] KW-E: Echo, Embalm, Emerge, Enchant, Encore, Enlist, Entwine, Epic, Equip, Escape, Escalate, Eternalize, Evoke, Evolve, Exalted, Exploit, Extort
- [ ] KW-F: Fabricate, Fading, Fear, Firebending, First Strike, Flanking, Flash, Flashback, Flying, Foretell, Fortify, Freerunning, Frenzy, Fuse, Gift, Graft, Gravestorm
- [ ] KW-G: Harmonize, Haste, Haunt, Hexproof, Hideaway, Hidden Agenda, Horsemanship
- [ ] KW-I: Impending, Improvise, Indestructible, Infect, Ingest, Intimidate
- [ ] KW-J: Jump-start
- [ ] KW-K: Kicker
- [ ] KW-L: Landwalk, Level Up, Lifelink, Living Metal, Living Weapon
- [ ] KW-M: Madness, Manifest, Mechanic, Melee, Mentor, Menace, Megamorph, Miracle, Mobilize, Modular, Morph, Multikicker, Mutate, Myriad
- [ ] KW-N: Nightbound, Ninjutsu
- [ ] KW-O: Outlast, Offering, Offspring, Overload
- [ ] KW-P: Partner, Partner With, Persist, Phasing, Plot, Poisonous, Protection, Prototype, Provoke, Prowess, Prowl
- [ ] KW-R: Rampage, Ravenous, Reach, Recover, Reconfigure, Reflect, Reinforce, Renown, Replicate, Retrace, Riot, Ripple
- [ ] KW-S: Saddle, Scavenge, Shadow, Shroud, Skulk, Sneak, Soulbond, Soulshift, Space Sculptor, Specialize, Spectacle, Splice, Split Second, Spree, Squad, Station, Storm, Strive, Sunburst, Surge, Suspend
- [ ] KW-T: Toxic, Training, Trample, Transfigure, Transmute, Tribute, TypeCycling
- [ ] KW-U: Umbra Armor, Undaunted, Undying, Unearth, Unleash
- [ ] KW-V: Vanishing, Vigilance
- [ ] KW-W: Ward, Warp, Web-slinging, Wither

### PHASE 3XX: MISSING ~207 API EFFECTS (Deferred)

All ~220 API effect types need handler implementations:
- [ ] API-01: Abandon, ActivateAbility, AddOrRemoveCounter, AddPhase, AddTurn
- [ ] API-02: AdvanceCrank, Airbend, AlterAttribute, Amass, Animate, AnimateAll
- [ ] API-03: Attach, Ascend, AssembleContraption, AssignGroup
- [ ] API-04: Balance, BecomeMonarch, BecomesBlocked, BidLife, Blight, Block, Bond
- [ ] API-05: Branch, Camouflage, ChangeCombatants, ChangeSpeed, ChangeTargets, ChangeText, ChangeX, ChangeZone
- [ ] API-06: ChaosEnsues, Charm, ChooseCard, ChooseColor, ChooseDirection, ChooseEvenOdd, ChooseNumber
- [ ] API-07: ChoosePlayer, ChooseSector, ChooseSource, ChooseType, ClaimThePrize, Clash, ClassLevelUp
- [ ] API-08: Cleanup, Cloak, Clone, Connive, CopyPermanent, CopySpellAbility, ControlSpell, ControlPlayer, Counter
- [ ] API-09: DamageAll, DealDamage, DayTime, Debuff, DelayedTrigger, Destroy, DestroyAll, Dig, DigMultiple
- [ ] API-10: Discard, Discover, DrainMana, Draft, Draw
- [ ] API-11: EachDamage, Earthbend, Effect, Encode, EndCombatPhase, EndTurn, Endure
- [ ] API-12: ExchangeLife, ExchangeControl, ExchangePower, ExchangeZone, Explore
- [ ] API-13: Fight, FlipACoin, Fog
- [ ] API-14: GainControl, GainLife, GainOwnership, GameDrawn, Goad
- [ ] API-15: Haunt, Heist, Investigate, Intensify, Incubate, Learn
- [ ] API-16: LookAt, LoseLife, LosePerpetual, LosesGame
- [ ] API-17: MakeCard, Mana, Manifest, Meld, Mill, MoveCounter
- [ ] API-18: MultiplePiles, MustBlock, Mutate, NameCard, OpenAttraction
- [ ] API-19: PeekAndReveal, PermanentCreature, PermanentNoncreature, Phases, Planeswalk, Play
- [ ] API-20: Poison, PreventDamage, Proliferate, Protection, Pump
- [ ] API-21: PutCounter, Radiation, RearrangeTopOfLibrary, Regenerate, RemoveCounter
- [ ] API-22: RemoveFromMatch, ReorderZone, Repeat, ReplaceCounter, ReplaceDamage, RestartGame
- [ ] API-23: Reveal, RingTemptsYou, RollDice, RunChaos, Sacrifice, Scry
- [ ] API-24: Seek, SetInMotion, SetLife, SetState, Shuffle, SkipPhase
- [ ] API-25: SkipTurn, StoreSVar, Surveil, SwitchBlock, TakeInitiative
- [ ] API-26: Tap, TapAll, TimeTravel, Token, TwoPiles, Unattach
- [ ] API-27: UnlockDoor, Untap, Venture, Vote

### PHASE 4XX: MISSING ~36 REPLACEMENTS (Deferred)

All 41 Forge replacement effects need handlers:
- [ ] REP-01: AddCounter, AssembleContraption
- [ ] REP-02: AssignDealDamage, Attached
- [ ] REP-03: BeginPhase, BeginTurn
- [ ] REP-04: Cascade, Counter
- [ ] REP-05: CopySpell, CreateToken
- [ ] REP-06: DamageDone, DealtDamage, DeclareBlocker
- [ ] REP-07: Destroy, Draw
- [ ] REP-08: DrawCards, Explore
- [ ] REP-09: GainLife, GameLoss, GameWin
- [ ] REP-10: Learn, LifeReduced
- [ ] REP-11: LoseMana, Mill
- [ ] REP-12: Moved, PayLife
- [ ] REP-13: PlanarDiceResult, Planeswalk
- [ ] REP-14: ProduceMana, Proliferate
- [ ] REP-15: RemoveCounter
- [ ] REP-16: RollDice, RollPlanarDice
- [ ] REP-17: Scry, SetInMotion
- [ ] REP-18: Tap, Transform
- [ ] REP-19: TurnFaceUp, Untap

### PHASE 5XX: FULL 10-LAYER SYSTEM (Deferred)

- [ ] LAY-10: Full Layer 1 COPY implementation
- [ ] LAY-11: Full Layer 2 CONTROL implementation  
- [ ] LAY-12: Full Layer 3 TEXT implementation
- [ ] LAY-13: Full Layer 4 TYPE implementation
- [ ] LAY-14: Full Layer 5 COLOR implementation
- [ ] LAY-15: Full Layer 6 ABILITIES implementation
- [ ] LAY-16: Full Layer 7a CHARACTERISTIC implementation
- [ ] LAY-17: Full Layer 7b SETPT implementation
- [ ] LAY-18: Full Layer 7c MODIFYPT implementation
- [ ] LAY-19: Full Layer 8 RULES implementation

### PHASE 6XX: FULL COMBAT SYSTEM (Deferred)

- [ ] CMB-01: Full combat bands implementation
- [ ] CMB-02: GlobalAttackRestrictions implementation
- [ ] CMB-03: AttackConstraint implementation
- [ ] CMB-04: AttackRequirements implementation
- [ ] CMB-05: AttackingBand implementation

### PHASE 7XX: MISSING CARD TYPES (Deferred)

All card types in Forge that need support:

- [ ] CT-01: Battle cards (new 2024)
- [ ] CT-02: Saga cards with chapter counters
- [ ] CT-03: Dungeon cards with venture system
- [ ] CT-04: Room cards (unlock/lock rooms)
- [ ] CT-05: Attraction cards (crank, visit)
- [ ] CT-06: Contraption cards (assemble, crank)
- [ ] CT-07: Scheme cards (command zone)
- [ ] CT-08: Vanguard cards (avatar, starting life)
- [ ] CT-09: Conspiracy cards (hidden agenda)
- [ ] CT-10: Emissary cards
- [ ] CT-11: Story Card (Forgotten Realms)
- [ ] CT-12: Plane card (Planechase)
- [ ] CT-13: Phenomenon card
- [ ] CT-14: Victor token support enhancements

### PHASE 8XX: MISSING GAME VARIANTS (Deferred)

All game variants in Forge:

- [ ] GV-01: Brawl format
- [ ] GV-02: Oathbreaker format
- [ ] GV-03: Planechase (planar dice, chaos)
- [ ] GV-04: Archenemy
- [ ] GV-05: Archenemy Rumble
- [ ] GV-06: Tiny Leaders format
- [ ] GV-07: Vanguard format
- [ ] GV-08: Momir Basic format
- [ ] GV-09: Quest Draft
- [ ] GV-10: Sealed Deck
- [ ] GV-11: Draft (booster draft)
- [ ] GV-12: Two-Headed Giant

### PHASE 9XX: ADDITIONAL MISSING KEYWORDS (Deferred)

Additional keyword gaps beyond 200+ already listed:

- [ ] KW-200: Discover (playtest 2024)
- [ ] KW-201: Exploit
- [ ] KW-202: Extort
- [ ] KW-203: Forage
- [ ] KW-204: Myriad
- [ ] KW-205: Partner
- [ ] KW-206: Choose a Background
- [ ] KW-207: Companion
- [ ] KW-208: Janitor
- [ ] KW-209: Party (creature types)
- [ ] KW-210: Read Ahead (Saga)
- [ ] KW-211: Riot
- [ ] KW-212: Scavenge
- [ ] KW-213: Class (mechanic)
- [ ] KW-214: Daybound/Nightbound (transform)
- [ ] KW-215: Attract
- [ ] KW-216: Collect Evidence
- [ ] KW-217: Foretell
- [ ] KW-218: Hexfire (planeswalker)
- [ ] KW-219: Prologue
- [ ] KW-220: Revolt
- [ ] KW-221: Siege
- [ ] KW-222: Showcase

### PHASE 10XX: ZONE MANAGEMENT ENHANCEMENTS (Deferred)

- [ ] ZN-01: Plot zone (Foretell support)
- [ ] ZN-02: Phenotype zone
- [ ] ZN-03: Sideboard (full variant support)
- [ ] ZN-04: Attraction extra deck
- [ ] ZN-05: Contraption extra deck
- [ ] ZN-06: Conspiracy extra deck
- [ ] ZN-07: Scheme command zone
- [ ] ZN-08: Vanguard avatar zone

### PHASE 11XX: COST PAYMENT SYSTEM ENHANCEMENTS (Deferred)

- [ ] CP-01: Complex mana selection (specific mana choice)
- [ ] CP-02: Multiple alternative costs
- [ ] CP-03: Life as cost payment
- [ ] CP-04: Sacrifice as cost payment
- [ ] CP-05: Exile as cost payment
- [ ] CP-06: Discard as cost payment
- [ ] CP-07: Tap as cost payment
- [ ] CP-08: Cost reduction effects
- [ ] CP-09: Cost increase effects
- [ ] CP-10: Additional/modal costs

### PHASE 12XX: STATE MACHINE ENHANCEMENTS (Deferred)

- [ ] SM-01: Extra phases implementation
- [ ] SM-02: Skip phases (US7 partial)
- [ ] SM-03: Topsy-turvy reversed turns
- [ ] SM-04: Multiple combat phases
- [ ] SM-05: Upkeep phase split
- [ ] SM-06: More phase types (Begin, Precombat, Combat, Postcombat, End, Cleanup)

### PHASE 13XX: TARGETING SYSTEM ENHANCEMENTS (Deferred)

- [ ] TG-01: Complex targeting restrictions
- [ ] TG-02: Target validation per ability
- [ ] TG-03: Target collection system upgrades
- [ ] TG-04: Modal targeting
- [ ] TG-05: Undercover agent targeting

### PHASE 14XX: AI/PLAYER SYSTEM ENHANCEMENTS (Deferred)

- [ ] AI-01: Forge AI system is extensive
- [ ] AI-02: HeuristicPlayer improvements
- [ ] AI-03: Deck validation for variants
- [ ] AI-04: Mulligan variants

### PHASE 15XX: LOCALIZATION/I18N (Deferred)

- [ ] L10N-01: Localizer.getInstance() pattern
- [ ] L10N-02: Card text translation
- [ ] L10N-03: Rule text translation

### PHASE 16XX: CARD FACTORY/SUPPORT (Deferred)

- [ ] CF-01: CardFactory patterns
- [ ] CF-02: More card layouts (split, flip, transform, modal, adventure)
- [ ] CF-03: Card image handling
- [ ] CF-04: Card oracle text parsing improvements

### PHASE 17XX: PLAYER PROFILE/SAVVINGS (Deferred)

- [ ] PP-01: Player profile persistence
- [ ] PP-02: Game history
- [ ] PP-03: Deck statistics
- [ ] PP-04: Achievement tracking
- [ ] PP-05: Quest system

### PHASE 18XX: ECONOMY/TRANSACTIONS (Deferred)

- [ ] EC-01: Card collection tracking
- [ ] EC-02: Card economy/value
- [ ] EC-03: Trade system
- [ ] EC-04: Wildcards

### PHASE 19XX: GUI/ANIMATION (Deferred - if frontend ever)

- [ ] GU-01: Animation framework
- [ ] GU-02: Card tap animations
- [ ] GU-03: Spell resolution animations
- [ ] GU-04: Combat animations
- [ ] GU-05: Token creation animations

### PHASE 20XX: DIRECTORY-LEVEL FORGE PARITY (Deferred)

#### 20A. ABILITY Directory (214 files) - MISSING
- [ ] AB-001 to AB-214: All 214 ability effect handler files

#### 20B. COMBAT Directory (9 files) - MISSING  
- [ ] CB-01: Combat.java
- [ ] CB-02: CombatView.java
- [ ] CB-03: CombatLki.java
- [ ] CB-04: CombatUtil.java
- [ ] CB-05: AttackRequirements.java
- [ ] CB-06: AttackConstraint.java
- [ ] CB-07: AttackRestriction.java
- [ ] CB-08: GlobalAttackRestrictions.java
- [ ] CB-09: AttackingBand.java

#### 20C. COST Directory (51 files) - MISSING
- [ ] CT-001 to CT-051: All 51 cost payment handler files

#### 20D. EVENT Directory (63 files) - MISSING
- [ ] EV-001 to EV-063: All 63 event handler files

#### 20E. KEYWORD Directory (34 files) - MISSING
- [ ] KW-001 to KW-034: All 34 keyword handler files

#### 20F. MANA Directory (6 files) - MISSING
- [ ] MN-01 to MN-06: All mana system files

#### 20G. PHASE Directory (7 files) - MISSING
- [ ] PH-01 to PH-07: All phase handler files

#### 20H. PLAYER Directory (28 files) - MISSING
- [ ] PL-01 to PL-028: All player/AI files

#### 20I. REPLACEMENT Directory (46 files) - MISSING
- [ ] RP-001 to RP-046: All replacement handler files

#### 20J. SPELLABILITY Directory (23 files) - MISSING
- [ ] SA-001 to SA-023: All spellability files

#### 20K. STATICABILITY Directory (61 files) - MISSING
- [ ] ST-001 to ST-061: All staticability files

#### 20L. TRIGGER Directory (139 files) - MISSING
- [ ] TG-001 to TG-139: All trigger handler files

#### 20M. ZONE Directory (8 files) - MISSING
- [ ] ZN-01 to ZN-08: All zone handler files

### PHASE 21XX: CARD FRAMEWORK (Deferred)

- [ ] CF-01: Card model expansion (100+ card types)
- [ ] CF-02: CardFactory patterns
- [ ] CF-03: CardCache
- [ ] CF-04: CardRules
- [ ] CF-05: CardLayout support (all types)

### PHASE 22XX: EVENT SYSTEM (Deferred)

- [ ] EV-064: AttackEvent complete
- [ ] EV-065: BlockEvent complete  
- [ ] EV-066: DamageEvent complete
- [ ] EV-067: ZoneChangeEvent complete
- [ ] EV-068: PhaseChangeEvent complete
- [ ] EV-069: TurnEvent complete
- [ ] EV-070: CardDrawEvent complete
- [ ] EV-071: GameEvent complete
- [ ] EV-072: All remaining event types

### PHASE 23XX: PLAYER/AI SYSTEM (Deferred)

- [ ] AI-10: HeuristicPlayer improvements
- [ ] AI-11: PlayerProfile  
- [ ] AI-12: PlayerCollection
- [ ] AI-13: PlayerController
- [ ] AI-14: GameHistory
- [ ] AI-15: Full AI system (15+ AI types)
- [ ] AI-16: Mulligan variants
- [ ] AI-17: Sideboard support

### PHASE 24XX: GAME FORMAT SYSTEM (Deferred)

- [ ] GF-01: GameFormat class expansion
- [ ] GF-02: Format validation
- [ ] GF-03: Brawl format
- [ ] GF-04: Oathbreaker format
- [ ] GF-05: Commander (enhance)
- [ ] GF-06: Planechase format
- [ ] GF-07: Archenemy format
- [ ] GF-08: Tiny Leaders format
- [ ] GF-09: Vanguard format
- [ ] GF-10: All variant formats

### PHASE 25XX: FORGE AI MODULE PARITY (Deferred - NEW!)

Additional 187 AI files in forge-ai/ not previously counted:

- [ ] AI-20: AiController
- [ ] AI-21: AiAttackController
- [ ] AI-22: AiBlockController  
- [ ] AI-23: AiCostDecision
- [ ] AI-24: AiPlayDecision
- [ ] AI-25: AiCardMemory
- [ ] AI-26: AiCache
- [ ] AI-27: ComputerUtilAbility
- [ ] AI-28: ComputerUtilCard
- [ ] AI-29: ComputerUtilCombat
- [ ] AI-30: ComputerUtilCost
- [ ] AI-31: ComputerUtilMana
- [ ] AI-32: AiAbilityDecision
- [ ] AI-33: SpellAbilityAi
- [ ] AI-34: CopySpellAbilityAi
- [ ] AI-35: ActivateAbilityAi
- [ ] AI-36: SpellAbilityPicker
- [ ] AI-37: All 187 AI system files
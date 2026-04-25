# SPEC: Forge Parity - COMPREHENSIVE Gap Analysis (FINAL)

## Overview

Comprehensive gap analysis comparing our engine to Forge's MTG implementation.

## Status: INCOMPLETE - ALL GAPS DOCUMENTED

This spec documents EVERY gap between our engine and Forge.

---

## DIRECTORY STRUCTURE COMPARISON

### Forge Game Directory (`forge-game/src/main/java/forge/game/`)

| Directory | Files | Purpose |
|-----------|-------|---------|
| ability | 214 | Effect handlers, API, factories |
| combat | 10 | Combat system |
| cost | 51 | Cost payment handlers |
| event | 63 | Event handlers |
| keyword | 34 | Keyword implementations |
| mana | 6 | Mana production |
| phase | 7 | Phase handlers |
| player | 28 | Player/AI logic |
| replacement | 46 | Replacement effects |
| spellability | 23 | Spell/ability base |
| staticability | 61 | Static abilities |
| trigger | 139 | Trigger handlers |
| zone | 8 | Zone management |
| **TOTAL** | **786** | **Java files** |

### Our Engine (`mtg_engine/engine/`)

| Directory | Files | Purpose |
|-----------|-------|---------|
| engine/ | 12 | All core game logic |

**GAP**: 786 files vs 12 files = **774 missing implementations**

---

## GAP BY CATEGORY

### 1. ABILITY DIRECTORY (214 files vs 0)

- [ ] 214 ability effect classes need implementation
- [ ] ApiType enum (~220 values)
- [ ] EffectFactory patterns
- [ ] SpellAbilityEffect base

### 2. COMBAT DIRECTORY (10 files vs 1)

- [ ] Combat.java
- [ ] CombatView.java
- [ ] CombatLki.java
- [ ] CombatUtil.java
- [ ] AttackRequirements.java
- [ ] AttackConstraint.java
- [ ] AttackRestriction.java
- [ ] GlobalAttackRestrictions.java
- [ ] AttackingBand.java

Our: combat.py (basic)

### 3. COST DIRECTORY (51 files vs ~1)

- [ ] Cost (base)
- [ ] CostPayment (multiple types)
- [ ] CostPaymentStack
- [ ] CostMana
- [ ] CostLife
- [ ] CostSacrifice
- [ ] CostTap
- [ ] CostExile
- [ ] CostDiscard
- [ ] CostAlternative
- [ ] CostKicker
- [ ] CostMultiply
- [ ] ...45 more cost types

Our: Basic mana in mana.py

### 4. EVENT DIRECTORY (63 files vs 0)

- [ ] AttackEvent
- [ ] BlockEvent
- [ ] DamageEvent
- [ ] ZoneChangeEvent
- [ ] PhaseChangeEvent  - [ ] TurnEvent
- [ ] CardDrawEvent
- [ ] ...56 more event types

Our: Basic in triggers.py, zones.py

### 5. KEYWORD DIRECTORY (34 files vs 1)

- [ ] Keyword (200+ keywords)
- [ ] Keyword abilities implementation
- [ ] All keyword-specific classes

Our: ability_parser.py (basic keyword list)

### 6. MANA DIRECTORY (6 files vs ~1)

- [ ] ManaType
- [ ] ManaPoolBase
- [ ] ManaPool
- [ ] ManaProduced
- [ ] ManaAbilities

Our: mana.py

### 7. PHASE DIRECTORY (7 files vs 1)

- [ ] PhaseType
- [ ] PhaseHandler
- [ ] SubPhase
- [ ] PhaseType with sub-phases (12+ types)

Our: turn_manager.py (basic)

### 8. PLAYER DIRECTORY (28 files vs ~1)

- [ ] Player
- [ ] PlayerProfile
- [ ] PlayerCollection
- [ ] PlayerController
- [ ] GameHistory
- [ ] PlayerAI (15+ AI types)
- [ ] Mulligan
- [ ] Sideboard
- [ ] ...and more

Our: Very basic player model

### 9. REPLACEMENT DIRECTORY (46 files vs ~1)

- [ ] ReplacementEffect base
- [ ] 41+ replacement types
- [ ] ReplacementHandler

Our: replacement.py (basic ~5 types)

### 10. SPELLABILITY DIRECTORY (23 files vs ~1)

- [ ] SpellAbility (base)
- [ ] Ability
- [ ] Spell
- [ ] SpellAbilityStackInstance
- [ ] SpellAbilityView
- [ ] SpellAbilityEffect

Our: stack.py (basic)

### 11. STATICABILITY DIRECTORY (61 files vs 1)

- [ ] StaticAbility (base)
- [ ] 50+ static ability types
- [ ] StaticAbilityLayer

Our: staticability.py (~5 types)

### 12. TRIGGER DIRECTORY (139 files vs ~1)

- [ ] Trigger (base)
- [ ] TriggerType (159 values)
- [ ] TriggerHandler
- [ ] 137+ individual trigger handlers

Our: triggers.py (~18 patterns)

### 13. ZONE DIRECTORY (8 files vs 1)

- [ ] Zone (base)
- [ ] ZoneType
- [ ] ZoneChangeEvent
- [ ] ...

Our: zones.py

---

## ADDITIONAL FORGE SYSTEMS (NOT IN GAME/)

### card/ (~50 files)
- Card, CardFactory, CardCache, CardRules, etc.

### mana/ (~6 files)
- Full mana system

### phase/ (~7 files)
- Full phase system

### event/ (~63 files)  
- Full event system

### player/ (~28 files)
- Full player system with AI

---

## COMPREHENSIVE GAP LISTING

### G1. ABILITY (214 MISSING)
All ability effect implementation classes

### G2. COMBAT (9 MISSING)
- File-by-file combat gaps

### G3. COST (50 MISSING)
All cost payment types

### G4. EVENT (62 MISSING)
All event handlers

### G5. KEYWORD (33 MISSING)
All keyword handlers

### G6. MANA (5 MISSING)
Full mana system gaps

### G7. PHASE (6 MISSING)
Full phase gaps

### G8. PLAYER (27 MISSING)
Player/AI gaps

### G9. REPLACEMENT (45 MISSING)
All replacement effect types

### G10. SPELLABILITY (22 MISSING)
Spell/ability hierarchy gaps

### G11. STATICABILITY (60 MISSING)
All static ability types

### G12. TRIGGER (138 MISSING)
All trigger handlers

### G13. ZONE (7 MISSING)
Zone management gaps

---

## COMPLETE FORGE TRIGGER TYPES (159 types)

### A-Abandoned (1)
- TriggerAbandoned

### Ability Casting (6)
- TriggerAbilityCast
- TriggerSpellAbilityCast  
- TriggerSpellCast
- TriggerSpellCastOrCopy
- TriggerAbilityResolves
- TriggerAbilityTriggered

### Adaptation (1)
- TriggerAdapt

### Alignment Bending (5)
- TriggerAirbend
- TriggerEarthbend
- TriggerFirebend
- TriggerWaterbend
- TriggerElementalBend

### Always (1)
- TriggerAlways

### Attachments (1)
- TriggerAttached
- TriggerUnattach

### Attacker Blocking (5)
- TriggerAttackerBlocked
- TriggerAttackerBlockedOnce
- TriggerAttackerBlockedByCreature
- TriggerAttackerUnblocked
- TriggerAttackerUnblockedOnce

### Attack Declaration (1)
- TriggerAttacks

### B-Become (5)
- TriggerBecomeMonarch
- TriggerBecomeMonstrous
- TriggerBecomeRenowned
- TriggerBecomesCrewed
- TriggerBecomesSaddled
- TriggerBecomesPlotted

### Becomes Target (2)
- TriggerBecomesTarget
- TriggerBecomesTargetOnce

### Blockers (1)
- TriggerBlockersDeclared

### Blocking (1)
- TriggerBlocks

### C-Case (1)
- TriggerCaseSolved

### Champion (1)
- TriggerChampioned

### Changes (4)
- TriggerChangesController
- TriggerChangesZone
- TriggerChangesZoneAll

### Chaos (1)
- TriggerChaosEnsues

### Claim (1)
- TriggerClaimPrize

### Clash (1)
- TriggerClashed

### Class Level (1)
- TriggerClassLevelGained

### Commit (1)
- TriggerCommitCrime

### Conjure (1)
- TriggerConjureAll

### Counter Collection (9)
- TriggerCounterAdded
- TriggerCounterAddedOnce
- TriggerCounterAddedAll
- TriggerCounterPlayerAddedAll
- TriggerCounterTypeAddedAll
- TriggerCounterRemoved
- TriggerCounterRemovedOnce

### Countered (1)
- TriggerCountered

### Crank (1)
- TriggerCrankContraption

### Crew/Saddle/Station (3)
- TriggerCrewed
- TriggerSaddled
- TriggerStationed

### Cycle (1)
- TriggerCycled

### D-Damage (7)
- TriggerDamageAll
- TriggerDamageDealtOnce
- TriggerDamageDone
- TriggerDamageDoneOnce
- TriggerDamageDoneOnceByController
- TriggerDamagePreventedOnce
- TriggerExcessDamage
- TriggerExcessDamageAll

### Day/Night (1)
- TriggerDayTimeChanges

### Destroy (1)
- TriggerDestroyed

### Devour (1)
- TriggerDevoured

### Discard (3)
- TriggerDiscarded
- TriggerDiscardedAll
- TriggerMilledAll

### Discover (1)
- TriggerDiscover

### Drawn (1)
- TriggerDrawn

### Dungeon (1)
- TriggerCompletedDungeon

### E-Evolve (1)
- TriggerEvolved

### Exert (1)
- TriggerExerted

### Exile (3)
- TriggerExiled
- TriggerExiledAll

### Explore/Exploit (2)
- TriggerExplores
- TriggerExploited

### F-Fight (2)
- TriggerFight
- TriggerFightOnce

### Flip Coin (2)
- TriggerFlippedCoin

### Forage (1)
- TriggerForage

### Foretell (1)
- TriggerForetell

### G-Give (1)
- TriggerGiveGift

### I-Investigate (1)
- TriggerInvestigated

### L-Land (1)
- TriggerLandPlayed

### Life (4)
- TriggerLifeGained
- TriggerLifeLost
- TriggerLifeLostAll

### Lose Game (1)
- TriggerLosesGame

### M-Mana (2)
- TriggerManaAdded
- TriggerManaExpend

### Manifest (1)
- TriggerManifestDread

### Mentor (1)
- TriggerMentored

### Mill (3)
- TriggerMilled
- TriggerMilledOnce
- TriggerMilledAll

### Mutate (1)
- TriggerMutates

### N-New (1)
- TriggerNewGame

### O-Origin (4)
- TriggerScry
- TriggerSurveil
- TriggerSearchedLibrary
- TriggerShuffled

### P-Pay (3)
- TriggerPayCumulativeUpkeep
- TriggerPayEcho
- TriggerPayLife

### Phase (5)
- TriggerPhase
- TriggerPhaseIn
- TriggerPhaseOut
- TriggerPhaseOutAll

### Planeswalker (4)
- TriggerPlanarDice
- TriggerPlaneswalkedFrom
- TriggerPlaneswalkedTo

### Proliferate (1)
- TriggerProliferate

### R-Ring (1)
- TriggerRingTemptsYou

### Roll Die (3)
- TriggerRolledDie
- TriggerRolledDieOnce

### Room (1)
- TriggerRoomEntered

### S-Sacrifice (3)
- TriggerSacrificed
- TriggerSacrificedOnce

### Set Motion (1)
- TriggerSetInMotion

### Specialize (1)
- TriggerSpecializes

### Takes Initiative (1)
- TriggerTakesInitiative

### Tap/Untap (4)
- TriggerTaps
- TriggerTapsForMana
- TriggerUntaps

### Token (2)
- TriggerTokenCreated
- TriggerTokenCreatedOnce

### Trains (1)
- TriggerTrains

### Transform (1)
- TriggerTransformed

### Turn (3)
- TriggerTurnBegin
- TriggerTurnFaceUp

### U-V-Visit (4)
- TriggerUnlockDoor
- TriggerUntapAll
- TriggerTapAll
- TriggerVisitAttraction
- TriggerVote

---

## COMPLETE FORGE KEYWORDS (~200 keywords)

### A (19)
- Absorb, Affinity, Afflict, Afterlife, Aftermath, Amplify, Annihilator, Ascend, Assist, Aura Swap, Awaken, Backup, Banding, Bands with Other, Bargain, Battle Cry, Bestow, Blitz, Bloodthirst

### B-F (19)
- Bushido, Buyback, Cascade, Casualty, Champion, Changeling, Choose a Background, Cipher, Companion, Compleated, Conspire, Convoke, Craft, Crew, Cumulative Upkeep, Cycling, Dash, Daybound, Deathtouch, Decayed, Defender, Delve, Demonstrate, Dethrone, Devour, Devoid, Disguise, Disturb, Double Strike, Double Team, Dredge, Echo, Embalm, Emerge, Enchant, Encore, Enlist, Entwine, Epic, Equip, Escape, Escalate, Eternalize, Evoke, Evolve, Exalted, Exploit, Extort

### G-O (41)
- Fabricate, Fading, Fear, Firebending, First Strike, Flanking, Flash, Flashback, Flying, Foretell, Fortify, Freerunning, Frenzy, Fuse, Gift, Graft, Gravestorm, Harmonize, Haste, Haunt, Hexproof, Hideaway, Hidden Agenda, Horsemanship, Impending, Improvise, Indestructible, Infect, Ingest, Intimidate, Jump-start, Kicker, Landwalk, Level Up, Lifelink, Living Metal, Living Weapon, Madness, Manifest, Mechanic, Melee, Mentor, Menace, Megamorph, Miracle, Mobilize, Modular, Morph, Multikicker, Mutate, Myriad

### N-R (20)
- Nightbound, Ninjutsu, Outlast, Offering, Offspring, Overload, Partner, Partner With, Persist, Phasing, Plot, Poisonous, Protection, Prototype, Provoke, Prowess, Prowl, Rampage, Ravenous, Reach, Recover, Reconfigure, Reflect, Reinforce, Renown, Replicate, Retrace, Riot, Ripple

### S-W (48)
- Saddle, Scavenge, Shadow, Shroud, Skulk, Sneak, Soulbond, Soulshift, Space Sculptor, Specialize, Spectacle, Splice, Split Second, Spree, Squad, Station, Storm, Strive, Sunburst, Surge, Suspend, Toxic, Training, Trample, Transfigure, Transmute, Tribute, TypeCycling, Umbra Armor, Undaunted, Undying, Unearth, Unleash, Vanishing, Vigilance, Ward, Warp, Web-slinging, Wither

---

## COMPLETE FORGE API/EFFECT TYPES (~220)

### A (20)
- Abandon, ActivateAbility, AddOrRemoveCounter, AddPhase, AddTurn, AdvanceCrank, Airbend, AlterAttribute, Amass, Animate, AnimateAll, Attach, Ascend, AssembleContraption, AssignGroup

### B-D (30)
- Balance, BecomeMonarch, BecomesBlocked, BidLife, Blight, Block, Bond, Branch, Camouflage, ChangeCombatants, ChangeSpeed, ChangeTargets, ChangeText, ChangeX, ChangeZone, ChangeZoneAll, ChaosEnsues, Charm, ChooseCard, ChooseColor, ChooseDirection, ChooseEvenOdd, ChooseNumber, ChoosePlayer, ChooseSector, ChooseSource, ChooseType, ClaimThePrize, Clash, ClassLevelUp, Cleanup, Cloak, Clone, Connive, CopyPermanent, CopySpellAbility, ControlSpell, ControlPlayer, Counter

### D-E (30)
- DamageAll, DealDamage, DayTime, Debuff, DelayedTrigger, Destroy, DestroyAll, Dig, DigMultiple, DigUntil, Discard, Discover, DrainMana, Draft, Draw, EachDamage, Earthbend, Effect, Encode, EndCombatPhase, EndTurn, Endure, ExchangeLife, ExchangeLifeVariant, ExchangeControl, ExchangeControlVariant, ExchangePower, ExchangeZone, ExchangeTextBox, Explore, Fight

### F-L (30)
- FlipACoin, FlipOntoBattlefield, Fog, GainControl, GainControlVariant, GainLife, GainOwnership, GameDrawn, GenericChoice, Goad, Haunt, Heist, Investigate, Intensify, ImmediateTrigger, Incubate, Learn, LookAt, LoseLife, LosePerpetual, LosesGame

### M-P (40)
- MakeCard, Mana, ManaReflected, Manifest, ManifestDread, Meld, Mill, MoveCounter, MultiplePiles, MultiplyCounter, MustBlock, Mutate, NameCard, OpenAttraction, PeekAndReveal, PermanentCreature, PermanentNoncreature, Phases, Planeswalk, Play, PlayLandVariant, Poison, PreventDamage, Proliferate, Protection, ProtectionAll, Pump, PumpAll, PutCounter, PutCounterAll

### R-S (30)
- Radiation, RearrangeTopOfLibrary, Regenerate, Regeneration, RemoveCounter, RemoveCounterAll, RemoveFromCombat, RemoveFromGame, RemoveFromMatch, ReorderZone, Repeat, RepeatEach, ReplaceCounter, ReplaceEffect, ReplaceMana, ReplaceDamage, ReplaceToken, ReplaceSplitDamage, RestartGame, Reveal, RevealHand, ReverseTurnOrder, RingTemptsYou, RollDice, RollPlanarDice, RunChaos, Sacrifice, SacrificeAll, Scry, Seek, SetInMotion, SetLife

### S-W (25)
- SetState, Shuffle, SkipPhase, SkipTurn, StoreSVar, Subgame, Surveil, SwitchBlock, TakeInitiative, Tap, TapAll, TapOrUntap, TapOrUntapAll, TimeTravel, Token, TwoPiles, Unattach, UnlockDoor, Untap, UntapAll, Venture, VillainousChoice, Vote, WinsGame

---

## COMPLETE FORGE REPLACEMENT TYPES (41)

- AddCounter, AssembleContraption, AssignDealDamage, Attached, BeginPhase, BeginTurn, Cascade, Counter, CopySpell, CreateToken, DamageDone, DealtDamage, DeclareBlocker, Destroy, Draw, DrawCards, Explore, GainLife, GameLoss, GameWin, Learn, LifeReduced, LoseMana, Mill, Moved, PayLife, PlanarDiceResult, Planeswalk, ProduceMana, Proliferate, RemoveCounter, RollDice, RollPlanarDice, Scry, SetInMotion, Tap, Transform, TurnFaceUp, Untap

---

## COMPLETE FORGE LAYER SYSTEM (10 layers)

1. COPY - Copiable values
2. CONTROL - Control-changing effects  
3. TEXT - Text-changing effects
4. TYPE - Type-changing effects
5. COLOR - Color-changing effects
6. ABILITIES - Ability effects
7a. CHARACTERISTIC - CDA P/T
7b. SETPT - Set P/T  
7c. MODIFYPT - Modify P/T
8. RULES - Game rule changes

---

## DEFERRED ITEMS ADDED TO PLAN

The following gaps need to be added to plan.md and tasks.md:

### 1. MISSING TRIGGER TYPES (149)
All 159 trigger types from above need individual handlers

### 2. MISSING KEYWORDS (180)
All 200 keywords need implementation

### 3. MISSING EFFECTS (207)
All 220 API effects need handlers

### 4. MISSING REPLACEMENTS (36)
All 41 replacement effects need handlers

### 5. MISSING LAYERS (7)
Full 10-layer system needs implementation

### 6. MISSING COMBAT SYSTEM
Full combat with bands, restrictions, requirements

---

## Files Needing Updates

- plan.md - Add all missing items
- tasks.md - Add all missing tasks  
- SPEC.md - This document (updated)
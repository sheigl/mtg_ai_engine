# Forge Parity Gap Analysis

**Date:** 2026-07-24  
**Scope:** Compare mtg_ai_engine (49 keyword files, 32 trigger patterns) against Forge MTG engine (201 keywords, ~140 trigger types)

---

## 1. Keyword Module Inventory

### Real Implementations (~21 modules with working `apply()` logic)

These have detection/parsing AND real game-state-transforming behavior:

| # | Keyword | CR | Status | Notes |
|---|---------|----|--------|-------|
| 1 | Deathtouch | 702.2 | ✅ Real | Query helpers + damage transforms (combat/core.py wired) |
| 2 | Lifelink | 702.6 | ✅ Real | Query helpers + gain life transforms (combat/core.py wired) |
| 3 | Infect | 702.90 | ✅ Real | Infect/Wither/PoisonousKeyword classes, combat/replacement wired |
| 4 | Afterlife | 702.108 | ✅ Real | Death trigger queuing (triggers.py) + token creation (stack.py) |
| 5 | Undying | 702.51 | ✅ Real | Death trigger queuing (triggers.py) + graveyard return (stack.py) |
| 6 | Persist | 702.61 | ✅ Real | Death trigger queuing (triggers.py) + graveyard return (stack.py) |
| 7 | Sunburst | 702.103 | ✅ Real | ETB counter effect via `apply_sunburst_counters()` wired in zones.py |
| 8 | Cascade | 702.85 | ✅ Real | `apply_cascade()`, `resolve_cascade_choice()` with pending choice |
| 9 | Storm | 702.41a | ✅ Real | `create_storm_copies()` LIFO stack copies |
| 10 | Kicker | 702.33 | ✅ Real | Pending choice + AI resolution, mana deduction |
| 11 | Flashback | 702.34 | ✅ Real | Pending choice + AI resolution, exile on resolve |
| 12 | Escape | 702.45 | ✅ Real | Pending choice + AI resolution, exile from graveyard |
| 13 | Delve | 702.66 | ✅ Real | Cost payment via graveyard cards, regex bugfixes done |
| 14 | Madness | 702.35 | ✅ Real | Pending choice + AI resolution, mana deduction |
| 15 | Dredge | 702.59 | ✅ Real | Pending choice + AI resolution, mill from library |
| 16 | Ninjutsu | 702.61 | ✅ Real | Pending choice + AI resolution, return-to-hand swap |
| 17 | Dash | 702.138 | ✅ Real | Pending choice + AI resolution, haste + end-step return |
| 18 | Hexproof | 702.54 | ✅ Real | Query helpers `is_hexproof()`, `can_target_hexproof()` |
| 19 | Shroud | 702.41 | ✅ Real | Query helpers `is_shrouded()`, `can_target_shrouded()` |
| 20 | Menace | 702.146 | ✅ Real | Query helpers `is_menacing()`, `can_block_menacing()` |
| 21 | Reach | 702.165 | ✅ Real | Query helpers `has_reach()`, `can_block_flying()` |

### Stub Modules (~28 files with NOOP `apply()`)

These have detection/parsing but `apply()` returns `game_state` unchanged:

| # | Keyword | CR | Detection | Parsing | apply() Status |
|---|---------|----|-----------|---------|----------------|
| 1 | Crew | 702.147 | ✅ regex | ✅ value | ❌ NOOP — needs crew logic + end-of-turn cleanup |
| 2 | Equip | 702.5 | ✅ regex | ✅ cost | ❌ NOOP — needs attachment + sorcery timing |
| 3 | Cycle/Cycling | 702.36 | ✅ regex | ✅ cost | ❌ NOOP — has `type_cycle()` helper but not wired |
| 4 | Scry | 701.20 | ✅ regex | ✅ value | ❌ NOOP — needs library manipulation + human choice |
| 5 | Ward | 702.145 | ✅ regex | ✅ cost | ❌ NOOP — needs targeting interception + counter logic |
| 6 | Toxic | 702.134 | ✅ regex | ✅ value | ⚠️ Partial — has `apply_toxic()` but not wired into combat |
| 7 | Buyback | 702.28 | ✅ regex | ✅ cost | ❌ NOOP — needs spell resolution interception |
| 8 | Entwine | 702.39 | ✅ regex | ✅ cost | ❌ NOOP — needs multimode selection override |
| 9 | Overload | 702.91 | ✅ standalone fns | ✅ cost | ❌ NOOP — has `get_overload_targets()` but not wired |
| 10 | Miracle | 702.41 | ✅ regex | ✅ cost | ❌ NOOP — needs first-card-of-turn tracking |
| 11 | Bloodthirst | 702.31 | ✅ regex | ✅ value | ⚠️ Partial — has `create_trigger()` but not wired into ETB |
| 12 | Convoke | 702.77 | ✅ regex | ❌ cost | ❌ NOOP — needs mana payment integration |
| 13 | Unearth | 702.75 | ✅ regex | ✅ cost | ❌ NOOP — needs graveyard-to-battlefield + end-of-turn sacrifice |
| 14 | Transmute | 702.98 | ✅ regex | ✅ value | ❌ NOOP — has `transmute()` helper but not wired |
| 15 | Replicate | 702.63 | ✅ regex | ✅ cost | ❌ NOOP — needs copy-on-ETB logic |
| 16 | Surge | 702.138b | ✅ regex | ✅ cost | ❌ NOOP — needs "spell cast this turn" tracking |
| 17 | Level Up | 702.44 | ✅ regex | ✅ cost | ❌ NOOP — needs leveler transformation logic |
| 18 | Flanking | 702.69 | ✅ regex | ✅ value | ❌ NOOP — has `apply_flanking()` but not wired into combat |
| 19 | Extort | 702.63b | ✅ regex | ✅ cost | ❌ NOOP — needs spell resolution hook + life drain/gain |
| 20 | Counter | 701.5 | ✅ regex | ✅ type | ⚠️ Partial — has `apply_counter()` but not wired into stack |
| 21 | Meld | 702.146b | ✅ regex | ✅ pair name | ❌ NOOP — needs two-card meld logic + battlefield placement |
| 22 | ETB (generic) | various | ✅ regex | ❌ n/a | ⚠️ Partial — detection only, resolution via stack effect patterns |
| 23 | Leave (LTB) | various | ✅ regex | ❌ n/a | ❌ NOOP — LTB triggers not reliably detected |
| 24 | Morph | 702.37 | ✅ regex | ✅ cost | ⚠️ Partial — real logic in `engine/morph.py`, keyword module is stub |
| 25 | Suspend | 702.65 | ✅ regex | ✅ counters | ⚠️ Partial — real logic in turn_manager.py + `engine/suspend.py` |
| 26 | Evoke | 702.45b | ✅ regex | ❌ n/a | ⚠️ Partial — real logic in `engine/evoke.py`, keyword module is stub |
| 27 | Scavenge | 702.138a | ✅ regex | ✅ value | ❌ NOOP — needs power/toughness transfer from graveyard |
| 28 | base (abstract) | n/a | n/a | n/a | Abstract classes only (KeywordAbility, PassiveKeyword, etc.) |

### Completely Missing Keywords (~25+ not in our codebase at all)

These exist in Forge but have NO file in `mtg_engine/ability/keywords/`:

| Priority | Keyword | First Set (Year) | CR | Frequency | Description |
|----------|---------|-------------------|----|-----------|-------------|
| **P0** | Fortify | 2013 (M13) | 702.54a | Very High | Equipment-like: put +N/+N counters on target creature |
| **P0** | Phasing | 1994 (Alpha) | 702.26 | Medium | Permanent phases out/in, skips untap |
| **P1** | Modulate | 2023 (MOM) | 702.XX | High | Exile target creature, create X/X colorless creature token |
| **P1** | Craft | 2024 (OTJ) | 702.XX | Medium | Create artifact tokens with specific abilities |
| **P1** | Compleated | 2024 (OTJ) | 702.XX | Medium | Put counters on artifact, transforms when threshold met |
| **P1** | Plot | 2024 (OTJ) | 702.XX | Medium | Exile target creature face down, can be revealed later |
| **P1** | Saddle | 2025 (BLI) | 702.XX | High | Attach to creature like Equipment but from hand/spell |
| **P1** | Backup | 2024 (OTJ) | 702.XX | Medium | Create tokens that can be sacrificed for effects |
| **P1** | Bargain | 2025 (BLI) | 702.XX | Medium | Pay life to draw/search, common in modern sets |
| **P1** | Gift | 2024 (OTJ) | 702.XX | Medium | Give a card/token to opponent with upside |
| **P1** | Prototype | 2025 (BLI) | 702.XX | High | Create artifact tokens that copy other artifacts |
| **P2** | Intensify | 2023 (LCI) | 702.XX | Medium | Hybrid kicker: pay any combination of colors |
| **P2** | Endure | 2024 (OTJ) | 702.XX | Low | Creature survives lethal damage once per turn |
| **P2** | Set In Motion | 2025 (BLI) | 702.XX | Medium | Create token that enters tapped/attacking |
| **P2** | Goad | 2021 (TBH) | 702.148a | High | Creature must attack, can't attack goader |
| **P2** | Detain | 2020 (BTW) | 702.XX | Medium | Creature can't attack or block flying |
| **P2** | Heist/Protect | 2022 (PHD) | 702.XX | Medium | Buy artifact from sideboard, attach to opponent's creature |
| **P2** | Battle/Siege | 2021 (KHM) | 702.XX | Medium | Two-sided MDFC: Siege enchantment → Battle creature |
| **P2** | Amass | 2019 (THS) | 702.138a | High | Create "the army" token, put +1/+1 counters on it |
| **P2** | Incubate | 2023 (MOM) | 701.XX | Medium | Create egg artifact with N counters, hatches into creature |
| **P2** | Forage | 2024 (INR) | 702.XX | Medium | Discard cards to create Food tokens |
| **P2** | Explore | 2021 (SHD) | 702.138b | High | Draw, untap lands, create Frog token |
| **P2** | Connive | 2020 (BTW) | 702.XX | Medium | Exile target nonland until spell resolves, draw a card |

---

## 2. Trigger Pattern Inventory

### Implemented Triggers (~32 categories with regex + check functions)

| Category | Regex Patterns | Check Function | Wired Into Engine? |
|----------|---------------|----------------|-------------------|
| cast | ✅ 5 patterns | `check_cast_triggers()` | ✅ stack.py resolve_top |
| attack | ✅ 5 patterns | `check_attack_triggers()` | ✅ combat/core.py |
| block | ✅ 3 patterns | `check_block_triggers()` | ✅ combat/core.py |
| upkeep | ✅ 4 patterns | via `check_phase_triggers()` | ✅ turn_manager.py |
| end_step | ✅ 2 patterns | via `check_phase_triggers()` | ✅ turn_manager.py |
| death | ✅ 5 patterns | `_on_zone_change()` | ✅ zones.py listener |
| draw | ✅ 2 patterns | `check_draw_triggers()` | ⚠️ Not wired into draw flow |
| damage | ✅ 3 patterns | `check_damage_triggers()` | ✅ combat/core.py + stack.py |
| etb | ✅ 3 patterns | `_on_zone_change()` | ✅ zones.py listener |
| ltb | ✅ 2 patterns | `_on_zone_change()` | ⚠️ Partial — LTB detection unreliable |
| end_turn | ✅ 1 pattern | via `check_phase_triggers()` | ✅ turn_manager.py |
| combat_start | ✅ 2 patterns | via `check_phase_triggers()` | ✅ turn_manager.py |
| discard | ✅ 2 patterns | `check_discard_triggers()` | ⚠️ Not wired into discard flow |
| token | ✅ 2 patterns | `check_token_triggers()` | ⚠️ Not wired into token creation |
| counter | ✅ 3 patterns | `check_counter_triggers()` | ⚠️ Not wired into counter placement |
| landfall | ✅ 3 patterns | `_on_zone_change()` (inline) | ✅ zones.py listener |
| planeswalk | ✅ 2 patterns | `check_planeswalk_triggers()` | ⚠️ Not wired into loyalty ability flow |
| face_up | ✅ 2 patterns | via phase triggers | ⚠️ Partial — Morph face-up not wired |
| mana_production | ✅ 5 patterns | `check_mana_production_triggers()` | ⚠️ Not wired into mana tap flow |
| sacrifice | ✅ 4 patterns | `check_sacrifice_triggers()` | ⚠️ Has check fn, needs call site wiring |
| life_gain_lost | ✅ 3 patterns | `check_life_gain_lost_triggers()` | ⚠️ Has check fn, needs call site wiring |
| fight | ✅ 2 patterns | `check_fight_triggers()` | ⚠️ Has check fn, needs call site wiring |
| proliferated | ✅ 2 patterns | `check_proliferated_triggers()` | ✅ wired in replacement.py |
| transformed | ✅ 2 patterns | `check_transformed_triggers()` | ⚠️ Has check fn, needs MDFC transform wiring |
| tutor (search library) | ✅ 2 patterns | `check_tutor_triggers()` | ⚠️ Has check fn, needs call site wiring |
| becomes_target | ✅ 2 patterns | `check_becomes_target_triggers()` | ⚠️ Has check fn, needs targeting flow wiring |
| attach | ✅ 2 patterns | `check_attach_triggers()` | ⚠️ Has check fn, needs equip wiring |
| day_night_change | ✅ 2 patterns | `check_day_night_change_triggers()` | ✅ wired in DNG-01 |
| completed_dungeon | ✅ 2 patterns | `check_completed_dungeon_triggers()` | ✅ wired in dungeon.py |
| mana_spent | ✅ 2 patterns | `check_mana_spent_triggers()` | ⚠️ Has check fn, needs mana payment wiring |

### Missing Triggers (~108 categories not in triggers.py)

**P0 — Blocks gameplay:**
- **countered**: "Whenever a spell is countered" — needed for any card that responds to counterspells (e.g., [[Dark Ritual]] with [[Spell Pierce]])
- **investigated**: "Whenever you investigate" / "Whenever a land is investigated" — needed for clue token triggers

**P1 — Common modern patterns:**
- **scry**: "Whenever you scry" — needed for cards like [[Rest in Peace]], [[Teferi, Time Raveler]]
- **cycled**: "Whenever you cycle a card" — distinct from generic discard; needed for cycling archetypes
- **abandoned**: "Whenever a permanent is abandoned" — MDFC-specific (Phyrexia sets)
- **mutates**: "Whenever this creature mutates" — Stack creatures mechanic (Amonkhet, Phyrexia)

**P2 — Useful but less common:**
- **loyalty_change**: "Whenever loyalty is put on a planeswalker" / "changes"
- **phase_out/phase_in**: Phasing triggers
- **revealed**: "Whenever a card is revealed" — needed for reveal mechanics (e.g., [[Teferi, Hero of Dominaria]])
- **exile_from_graveyard**: "Whenever a card is exiled from a graveyard"
- **shuffle_library**: "Whenever you shuffle your library"
- **equip_attach**: "Whenever this becomes attached" — separate from generic attach (Equipment-specific)
- **untap**: "Whenever a permanent untaps"
- **copy_card**: "Whenever a copy of a spell is created" / "Whenever a creature copies another"

---

## 3. Trigger Wiring Gaps

**Critical finding:** ~10 trigger categories have regex patterns AND check functions in triggers.py, but are NOT wired into the engine's event flow. They exist as dead code:

| Trigger | Has Regex? | Has Check Fn? | Wired Into Engine? | Gap |
|---------|-----------|---------------|-------------------|-----|
| sacrifice | ✅ | ✅ `check_sacrifice_triggers()` | ❌ | Need call site in zones.py when permanent sacrificed |
| life_gain_lost | ✅ | ✅ `check_life_gain_lost_triggers()` | ❌ | Need call site in stack.py `_gain_life()` / `_lose_life()` |
| fight | ✅ | ✅ `check_fight_triggers()` | ❌ | Need call site in stack.py `_apply_fight()` |
| transformed | ✅ | ✅ `check_transformed_triggers()` | ❌ | Need call site in zones.py `_transform_mdfc()` |
| tutor (search) | ✅ | ✅ `check_tutor_triggers()` | ❌ | Need call site wherever library search happens |
| becomes_target | ✅ | ✅ `check_becomes_target_triggers()` | ❌ | Need call site in stack.py target validation |
| attach | ✅ | ✅ `check_attach_triggers()` | ❌ | Need call site when equip/fortify attaches |
| mana_spent | ✅ | ✅ `check_mana_spent_triggers()` | ❌ | Need call site in mana.py payment flow |
| draw | ✅ | ✅ `check_draw_triggers()` | ❌ | Need call site in zones.py `draw_card()` |
| discard | ✅ | ✅ `check_discard_triggers()` | ❌ | Need call site wherever discard happens |
| token | ✅ | ✅ `check_token_triggers()` | ❌ | Need call site in stack.py `_create_token_with_pt_and_keywords()` |
| counter | ✅ | ✅ `check_counter_triggers()` | ❌ | Need call site when counters placed/removed |
| mana_production | ✅ | ✅ `check_mana_production_triggers()` | ❌ | Need call site in mana.py tap-for-mana flow |

---

## 4. Priority Matrix

### P0: Blocks Gameplay (must fix before engine is usable for modern sets)

| Item | Type | Impact | Effort |
|------|------|--------|--------|
| Countered trigger pattern + wiring | Trigger | Any counterspell interaction broken | M |
| Investigated trigger pattern + wiring | Trigger | Clue token archetypes broken | S |
| Fortify keyword module | Keyword | Equipment-like mechanic, very common | L |
| Wire 13 existing check functions into engine flow | Wiring | Dead code → working triggers | L |

### P1: Common Modern Mechanics (2019-2025 sets)

| Item | Type | Impact | Effort |
|------|------|--------|--------|
| Phasing keyword module | Keyword | Classic mechanic, appears in modern sets | L |
| Modulate keyword module | Keyword | MOM set, very common token replacement | M |
| Saddle keyword module | Keyword | BLI 2025, Equipment-like from hand | M |
| Prototype keyword module | Keyword | BLI 2025, artifact copying | M |
| Amass keyword module | Keyword | THS+, zombie tribal / token armies | M |
| Explore keyword module | Keyword | SHD+, frog tokens common in green decks | S |
| Goad keyword module | Keyword | TBH+, combat restriction mechanic | M |
| Scry trigger wiring + real apply() | Trigger+Keyword | Most common action word in MTG | M |
| Cycling trigger wiring + real apply() | Trigger+Keyword | Cycling archetypes need proper detection | M |

### P2: Set Coverage (newer sets, less frequent)

| Item | Type | Impact | Effort |
|------|------|--------|--------|
| Craft keyword module | Keyword | OTJ 2024, artifact token creation | M |
| Compleated keyword module | Keyword | OTJ 2024, counter threshold transform | L |
| Plot keyword module | Keyword | OTJ 2024, face-down exile | M |
| Backup keyword module | Keyword | OTJ 2024, sacrifice-for-effect tokens | M |
| Bargain keyword module | Keyword | BLI 2025, life-to-draw mechanic | S |
| Gift keyword module | Keyword | OTJ 2024, give card to opponent | M |
| Intensify keyword module | Keyword | LCI 2023, hybrid kicker variant | M |
| Endure keyword module | Keyword | OTJ 2024, survive lethal once | S |
| Set In Motion keyword module | Keyword | BLI 2025, token enters attacking | M |
| Detain keyword module | Keyword | BTW+, combat restriction | M |
| Heist/Protect keyword module | Keyword | PHD, sideboard equipment mechanic | L |
| Battle/Siege keyword module | Keyword | KHM, MDFC upgrade mechanic | L |
| Incubate keyword module | Keyword | MOM, egg tokens with delayed hatching | L |
| Forage keyword module | Keyword | INR 2024, Food token creation | M |
| Connive keyword module | Keyword | BTW+, exile-until-resolve + draw | M |

### P3: Niche / Legacy Mechanics

| Item | Type | Impact | Effort |
|------|------|--------|--------|
| Mutates trigger pattern | Trigger | Amonkhet/Phyrexia stack creatures | S |
| Abandoned trigger pattern | Trigger | Phyrexia MDFC-specific | S |
| Loyalty change triggers | Trigger | Planeswalker counter interactions | M |
| Reveal triggers | Trigger | Various reveal mechanics | M |
| Exile from graveyard triggers | Trigger | Graveyard exile interactions | S |
| Shuffle library triggers | Trigger | Library shuffle effects | S |
| Untap triggers | Trigger | Untap timing effects | S |
| Copy card triggers | Trigger | Copy effect interactions | M |

---

## 5. Summary Statistics

| Category | Count | Details |
|----------|-------|---------|
| **Total Forge keywords** | ~201 | From Keyword.java |
| **Our keyword files** | 49 | Including base.py (abstract) |
| Real implementations | 21 | Working apply() with game state transforms |
| Stub modules (NOOP apply) | 28 | Detection/parsing only, no behavior |
| Completely missing keywords | ~25+ | No file exists in ability/keywords/ |
| **Total Forge trigger types** | ~140 | From trigger directory |
| Our trigger categories | 32 | Regex patterns + check functions defined |
| Triggers wired into engine | ~18 | Actually called from event flow |
| Triggers with dead code (check fn exists but not called) | ~13 | Have regex + check function, no call site |
| Completely missing triggers | ~95 | No regex or check function exists |

---

## 6. Recommendations

### Immediate Priority (Sprint 7 continuation):
1. **Wire the 13 dead-code trigger check functions** into their respective engine flows — this is free functionality already written but unused
2. **Add Countered + Investigated triggers** — P0 blockers for modern gameplay
3. **Build Fortify keyword** — most common missing mechanic, blocks entire Equipment-like archetype

### Medium Priority (Sprint 8):
4. **Build Phasing + Modulate + Saddle keywords** — high-frequency modern mechanics
5. **Build Amass + Explore + Goad keywords** — common in 2019+ sets
6. **Wire Scry real apply()** — most common action word, currently NOOP

### Lower Priority (Sprint 9+):
7. **Batch remaining missing keywords** by set era (OTJ batch, BLI batch, etc.)
8. **Add remaining trigger patterns** as needed for specific card support

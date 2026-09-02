# Keyword Module Inventory (2026-07-16)

## Overview
- **Total keyword modules**: 47 files in `mtg_engine/ability/keywords/*.py`
- **Base class hierarchy**: `KeywordAbility(ABC)` → `PassiveKeyword`, `TriggeredKeyword`, `CostKeyword` (in `base.py`)
- **CR reference**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Spec template**: `specs/templates/KW-design-template.md`

---

## Existing Modules (47)

### Cost Keywords (modify casting cost)
| Module | Keyword | CR Section | Has apply() | Has Tests | Status |
|--------|---------|------------|-------------|-----------|--------|
| `buyback.py` | Buyback | 702.31 | ✅ | ⏳ | Needs spec |
| `delve.py` | Delve | 702.66 | ✅ (bugfixed) | ✅ 10 int. tests | Needs spec |
| `dredge.py` | Dredge | 702.52 | ✅ | ✅ 9 int. tests | Needs spec |
| `escape.py` | Escape | 702.138 | ✅ | ✅ 11 int. tests | Needs spec |
| `entwine.py` | Entwine | 702.64 | ⏳ stub | ❌ | Needs spec + impl |
| `flashback.py` | Flashback | 702.34 | ✅ | ✅ 10 int. tests | Needs spec |
| `kicker.py` | Kicker | 702.33 | ✅ | ✅ 10 int. tests | Needs spec |
| `madness.py` | Madness | 702.35 | ✅ | ✅ 10 int. tests | Needs spec |
| `miracle.py` | Miracle | 702.94 | ⏳ stub | ❌ | Needs spec + impl |
| `overload.py` | Overload | 702.38 | ⏳ stub | ❌ | Needs spec + impl |

### Triggered/Replacement Keywords (fire at game moments)
| Module | Keyword | CR Section | Has apply() | Has Tests | Status |
|--------|---------|------------|-------------|-----------|--------|
| `cascade.py` | Cascade | 702.65 | ⏳ stub | ❌ | Needs spec + impl |
| `dash.py` | Dash | 702.109 | ✅ | ✅ 8 int. tests | Needs spec |
| `evoke.py` | Evoke | 702.49 | ⏳ stub | ❌ | Needs spec + impl |
| `level.py` | Level Up | 702.56 | ⏳ stub | ❌ | Needs spec + impl |
| `meld.py` | Meld | 711.5 | ⏳ stub | ❌ | Needs spec + impl |
| `morph.py` | Morph | 702.37 | ⏳ stub (detection only) | ❌ | Needs spec + impl |
| `ninjutsu.py` | Ninjutsu | 702.49 | ✅ | ✅ 6 int. tests | Needs spec |
| `persist.py` | Persist | 702.68 | ⏳ stub | ❌ | Needs spec + impl |
| `replicate.py` | Replicate | 702.59 | ⏳ stub | ❌ | Needs spec + impl |
| `scavenge.py` | Scavenge | 702.83 | ⏳ stub | ❌ | Needs spec + impl |
| `storm.py` | Storm | 702.65a-b | ⏳ stub | ❌ | Needs spec + impl |
| `suspend.py` | Suspend | 702.59a-c | ⏳ stub | ❌ | Needs spec + impl |
| `transmute.py` | Transmute | 702.84 | ⏳ stub | ❌ | Needs spec + impl |
| `unearth.py` | Unearth | 702.61a-b | ⏳ stub | ❌ | Needs spec + impl |

### Passive Keywords (query helpers, targeting/blocking)
| Module | Keyword | CR Section | Has query helper | Has Tests | Status |
|--------|---------|------------|------------------|-----------|--------|
| `deathtouch.py` | Deathtouch | 702.2b | ⏳ stub | ❌ | Needs spec + impl |
| `flanking.py` | Flanking | 702.54a-b | ⏳ stub | ❌ | Needs spec + impl |
| `hexproof.py` | Hexproof | 702.11 | ✅ | ✅ 7 int. tests | Needs spec |
| `infect.py` | Infect | 702.91b-c | ⏳ stub | ❌ | Needs spec + impl |
| `lifelink.py` | Lifelink | 702.46 | ⏳ stub | ❌ | Needs spec + impl |
| `menace.py` | Menace | 702.111 | ✅ | ✅ 12 unit + 5 int. tests | Needs spec |
| `reach.py` | Reach | 702.17 | ✅ | ✅ 8 int. tests | Needs spec |
| `shroud.py` | Shroud | 702.18 | ✅ | ✅ (with hexproof) | Needs spec |

### Static/Other Keywords
| Module | Keyword | CR Section | Has apply() | Has Tests | Status |
|--------|---------|------------|-------------|-----------|--------|
| `afterlife.py` | Afterlife | 702.69 | ⏳ stub | ❌ | Needs spec + impl |
| `bloodthirst.py` | Bloodthirst | 702.89 | ⏳ stub | ❌ | Needs spec + impl |
| `convoke.py` | Convoke | 702.34a-b | ⏳ stub | ❌ | Needs spec + impl |
| `counter.py` | Counter | — | ⏳ stub | ❌ | Needs spec + impl |
| `crew.py` | Crew | 702.120 | ⏳ stub | ❌ | Needs spec + impl |
| `cycle.py` | Cycling | 702.43 | ⏳ stub | ❌ | Needs spec + impl |
| `equip.py` | Equip | 702.6 | ⏳ stub | ❌ | Needs spec + impl |
| `extort.py` | Extort | 702.108 | ⏳ stub | ❌ | Needs spec + impl |
| `leave.py` | Leaving/ETB triggers | — | ⏳ stub | ❌ | Needs spec + impl |
| `scry.py` | Scry | 701.23 | ⏳ stub | ❌ | Needs spec + impl |
| `sunburst.py` | Sunburst | 702.62 | ⏳ stub | ❌ | Needs spec + impl |
| `surge.py` | Surge | 702.139 | ⏳ stub | ❌ | Needs spec + impl |
| `toxic.py` | Toxic | 702.164 | ⏳ stub | ❌ | Needs spec + impl |
| `undying.py` | Undying | 702.53 | ⏳ stub | ❌ | Needs spec + impl |
| `ward.py` | Ward | 702.156 | ⏳ stub | ❌ | Needs spec + impl |

### Special/Infrastructure
| Module | Purpose | Status |
|--------|---------|--------|
| `base.py` | Base class hierarchy (`KeywordAbility`, `PassiveKeyword`, `TriggeredKeyword`, `CostKeyword`) | ✅ Complete |
| `etb.py` | ETB trigger detection & handling | ✅ (separate from ETB choice system) |
| `__init__.py` | Module exports | — |

---

## Implementation Status Summary

### Fully Implemented (apply() + tests): 12 modules
Delve, Dredge, Escape, Flashback, Kicker, Madness, Ninjutsu, Dash, Hexproof*, Menace*, Reach*, Shroud*
- *Hexproof, Menace, Reach, Shroud are passive keywords with query helpers (no apply())

### Stub Only — Detection/Parsing Complete but No Real apply(): 1 module
Morph — has detection/parsing functions but `apply()` is a no-op stub (`return game_state`)

### Stub Only (no real apply(), no tests): 35 modules
All remaining modules have skeleton code but no functional implementation.

---

## Remaining Keywords from Gap Analysis (~169 total)

### A1: Engine-Inherent (no module needed) — ~20 keywords
Flying, First Strike, Double Strike, Vigilance, Haste, Trample, Flash, Defender, Indestructible, Protection, Fear, Shadow, Intimidate, Skulk, Wither

### A3: High-Value Keywords NOT yet in modules — ~45 keywords
Affinity, Amplify, Ascend, Banding, Bestow, Blitz, Bushido, Champion, Changeling, Cipher, Companion, Cumulative Upkeep, Daybound/Nightbound, Devour, Disturb, Embalm, Epic, Escalate, Eternalize, Exalted, Exploit, Fabricate, Foretell, Frenzy, Graft, Gravestorm, Haunt, Hideaway, Horsemanship, Ingest, Landwalk, Living Weapon, Melee, Mentor, Modular, Myriad, Outlast, Partner, Provoke, Prowl, Rampage, Ravenous, Recover, Reconfigure, Reinforce, Renown, Retrace, Riot, Ripple, Soulbond, Soulshift, Splice, Squad, Station, Strive, Training, Undaunted

### A4: Silly/Unlikely (no action) — ~20 keywords
Firebending, Web-slinging, Space Sculptor, etc.

---

## Sprint 6 Plan: Keyword Documentation & Implementation

### Phase 1: Retroactive Specs (Batch of 12 fully-implemented modules)
Create spec sheets for all 12 fully-implemented keyword modules using CR reference to validate correctness.

### Phase 2: Stub Modules — Priority Implementation (~35 modules)
Prioritize by gameplay impact and testability:
- **P0**: Deathtouch, Lifelink, Infect (combat damage modifiers)
- **P1**: Afterlife, Undying, Persist, Sunburst (death triggers)
- **P2**: Crew, Equip, Cycling, Scry (common mechanics)
- **P3**: Remaining stubs

### Phase 3: New Modules (~45 high-value keywords from A3)
Implement new keyword modules for A3 list, one at a time through the pipeline.

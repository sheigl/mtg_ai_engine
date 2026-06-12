# 038-gap-analysis: Fresh Gap Analysis (June 2026)

## Status
All 037-forge-parity deferred tasks (PHASE 1300-1700) have been closed.
This document identifies remaining functional gaps beyond the original spec.

---

## GAP A: Missing Keywords (~169 of 186 need formal modules)

**Severity**: Low-Medium
**Priority**: P3 (many work via inline engine rules)

We have 17 keyword modules. The remaining 169 keywords in SPEC.md fall into categories:

### A1: Engine-Inherent (no module needed) — ~20 keywords
These work through core engine mechanics (combat, static abilities, etc.):
- Flying, First Strike, Double Strike, Vigilance, Haste, Trample, Flash, Defender
- Indestructible, Protection, Fear, Shadow, Intimidate, Skulk, Reach (has module)
- Deathtouch (has module), Lifelink (has module), Hexproof (has module), Shroud (has module)
- Menace (has module), Wither, Infect (has module), Toxic (has module)

**ACCEPTANCE**: No action needed — these are structurally supported.

### A2: Implemented via parser/trigger patterns — ~30 keywords
Recognized by ability_parser.py or triggers.py but no dedicated module:
- Afterlife, Annihilator, Cascade, Conspire, Convoke, Delve, Dredge, Echo, Escape
- Evoke, Fading, Flashback, Improvise, Jump-start, Kicker, Madness, Miracle
- Morph, Mutate (has module), Persist, Phasing, Poisonous, Scavenge, Suspend
- Transfigure, Transmute, Unearth, Unleash, Vanishing

**ACCEPTANCE**: These work in gameplay but need formal keyword class modules.

### A3: Untouched high-value keywords — ~45 keywords
Not implemented as modules or structurally, require real effort:
- Affinity, Amplify, Ascend, Banding (has module), Bestow, Blitz, Bloodthirst
- Bushido, Buyback, Champion, Changeling, Cipher, Companion, Crew
- Cumulative Upkeep, Cycling (has module), Dash, Daybound/Nightbound
- Devour, Disturb, Embalm, Entwine, Epic, Equip, Escalate, Eternalize
- Exalted, Exploit, Extort, Fabricate, Foretell (has tests), Frenzy
- Graft, Gravestorm, Haunt, Hideaway, Horsemanship, Ingest, Landwalk
- Living Weapon, Melee, Mentor, Modular, Myriad, Ninjutsu, Outlast
- Overload (has module), Partner, Provoke, Prowl, Rampage, Ravenous
- Recover, Reconfigure, Reinforce, Renown, Replicate, Retrace, Riot
- Ripple, Soulbond, Soulshift, Splice, Spree, Squad, Station, Storm
- Strive, Sunburst, Surge, Training, Undaunted, Undying, Ward, Level Up (has module)

**ACCEPTANCE**: Formal keyword module + tests for each.

### A4: Silly/Unlikely keywords (no action needed) — ~20 keywords
- Firebending, Web-slinging, Space Sculptor, etc. (Un-set or mechanically trivial)

---

## GAP B: Unhandled Trigger Types (~104 of 159)

**Severity**: Medium
**Priority**: P2

Our `triggers.py` has 19 pattern categories with 55 regexes. Forge has 159 individual trigger classes. The gaps:

### B1: Missing trigger categories — ~12 trigger types
Trigger categories not covered by any regex pattern:
- `abandoned` — e.g. [[Assemble the Legion]] abandoned state
- `attached/unattach` — e.g. [[Sun Titan]] returning auras
- `loses_game` — e.g. [[Platinum Angel]] inverted
- `become_monarch/initiative` — e.g. [[Palace Jailer]]
- `becomes_target` — e.g. [[Shiny Impetus]] goad-on-target
- `class_level_gained` — e.g. [[Faceless Agent]] classes
- `committed_crime` — e.g. [[The Gaffer]]
- `completed_dungeon` — e.g. [[Hama Pashar]]
- `countered` — e.g. [[Baral, Chief of Compliance]]
- `day_time_changes` — e.g. [[Tovolar's Huntmaster]]
- `fight` — e.g. [[Ulvenwald Tracker]]
- `flipped_coin` — e.g. [[Okaun, Eye of Chaos]]
- `investigated` — e.g. [[Tamiyo's Journal]]
- `life_gained/lost` — already covered by event bridge (EVT-02)
- `mana_expend` — e.g. [[Karametra's Blessing]] for mana value paid
- `mentored` — e.g. [[Mentor of the Meek]]
- `mutates` — e.g. [[Vadrok, Apex of Thunder]]
- `proliferated` — e.g. [[Flux Channeler]]
- `ring_tempts_you` — e.g. [[The Ring]] LOTR
- `rolled_die` — e.g. [[Myr Retriever]] Un- cards
- `sacrificed` — e.g. [[Zulaport Cutthroat]]
- `tapped_for_mana` — e.g. [[Kyren Negotiations]]
- `token_created` — partial via triggers.py
- `transformed` — e.g. [[Jace, Vryn's Prodigy]]
- `tutored/searched_library` — e.g. [[Psychogenic Probe]]
- `voted` — e.g. [[Brago's Representative]]

**ACCEPTANCE**: Each new trigger category has a regex pattern + test.

---

## GAP C: Game Mechanics (8 major features)

**Severity**: Medium-High
**Priority**: P2

### C1: Commander Rules (Commander damage, tax, replacement effects)
**Files needed**: `mtg_engine/engine/formats/commander.py`
Commander exists as a model (commander zone) but no rules:
- Commander tax (+2 per cast from command zone)
- Commander damage (21+ from one commander = loss)
- Commander replacement effects (return to command zone)
- Color identity validation
- Partner / Partner With

### C2: Day/Night Cycle
**Files needed**: `mtg_engine/engine/daynight.py`
Key missed mechanic for Innistrad sets. Affects ~90+ cards.
- Game starts as day
- Day → Night when a player casts no spells on their turn
- Night → Day when a player casts 2+ spells on their turn
- Daybound/Nightbound transform at day/night transitions

### C3: The Monarch
**Files needed**: `mtg_engine/engine/monarch.py`
Affects ~30 cards (Conspiracy + Commander sets).
- Draw a card at end of turn when monarch
- Creature deals combat damage to monarch → new monarch

### C4: The Initiative
**Files needed**: `mtg_engine/engine/initiative.py`
Affects ~15 cards (Commander Legends: Baldur's Gate).
- Like monarch but also venture into Undercity dungeon

### C5: Venture into the Dungeon
**Files needed**: `mtg_engine/engine/dungeon.py`
Affects ~50 cards (Adventures in the Forgotten Realms).
- Dungeon cards: Dungeon of the Mad Mage, Lost Mine of Phandelver, Tomb of Annihilation
- Venture → advance room, complete dungeon → reward

### C6: Proliferate System
**Files needed**: `mtg_engine/engine/proliferate.py`
- Choose any number of players/permanents with counters
- Add one more of each counter they have

### C7: Companion Mechanic
**Files needed**: `mtg_engine/ability/keywords/companion.py`
- Deck-building restriction from outside the game
- Pay {3} to put into hand from sideboard

### C8: Renowned/Transform/M DF C Core
- Modal DFCs (day/night, transform triggered by conditions beyond at-will)
- Already partly handled by card model faces

---

## GAP D: Game Formats Engine

**Severity**: Low-Medium
**Priority**: P3

### D1: Format Validation
- Banned list checking per format
- Restricted list (Vintage)
- Deck minimum/maximum size per format
- Card pool validation (set legality)
- Format-specific rules (Commander color identity, Companion restrictions)

### D2: Multiplayer Rules
- Turn order for 3+ players
- Attack anyone vs attack restrictions
- Multiplayer variant-specific rules (Two-Headed Giant shared life, team turns)
- Range of influence (Emperor variant)

### D3: Sideboarding / Match System
- Best-of-3 match support
- Sideboard (zone already exists)
- Game logging per match

---

## GAP E: API & Application-Level Features

**Severity**: Low
**Priority**: P3

### E1: Card Search API
`GET /cards/search?q=...`
Text-based card search across loaded card database.

### E2: Deck Building AI
Auto-construct a deck from a card pool given constraints (format, colors, strategy).

### E3: Game Replay / Branching
Full game replay with step-through, seeking to specific turns, branching for "what-if" scenarios.

### E4: Draft / Sealed Simulation
- Draft bot pick logic
- Sealed pool generation
- Pack simulation

### E5: Game Spectator / Observer Endpoint
WebSocket endpoint for live game state streaming (for real-time frontend consumption).

### E6: Player Stats
Win/loss tracking per player, ELO rating, matchup stats.

---

## PRIORITY ORDER

### Sprint 1: Game Mechanics (highest impact)
1. **GAP C1: Commander Rules** — most requested format, engine has pieces
2. **GAP C3: Monarch** — small scope, fits existing turn_manager pattern
3. **GAP C5: Venture/Dungeon** — moderate scope, well-defined
4. **GAP C6: Proliferate** — moderate scope, cross-cuts counter system

### Sprint 2: Trigger & Keyword Gaps
5. **GAP B1: Missing trigger categories** — pick top 10 most common
6. **GAP A3: High-value keywords** — pick top 15 most played

### Sprint 3: Formats & Application
7. **GAP D1: Format validation** — banned list infra
8. **GAP C2: Day/Night** — needed for ~50+ Standard-playable cards
9. **GAP C4: The Initiative** — small, integrates with Venture

### Future
10. **GAP D2: Multiplayer** — fundamental architecture change
11. **GAP E1-E6: Application features** — depends on frontend needs

---

## METRICS

| Category | Items | Covered | Gap | Priority |
|----------|-------|---------|-----|----------|
| Keywords (formal modules) | 186 | 17 | 169 | P3 |
| Trigger categories | 159 | 55 | 104 | P2 |
| Game mechanics | 10 | ~3 | 7 | P2 |
| Game formats | 5 | 0 | 5 | P3 |
| API features | 6 | 0 | 6 | P3 |

**Current test count**: 1552 passing (baseline for gap closure tracking)

---

## HOW TO USE

Each gap section has acceptance criteria. To close a gap:
1. Create the specified file(s)
2. Add >= 1 test per feature item
3. Run `pytest tests/ -x -q` — must not regress existing 1552 tests
4. Update this document (mark item as ✅)
5. Update AGENTS.md with new active technologies

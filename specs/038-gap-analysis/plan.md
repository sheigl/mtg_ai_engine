# PLAN: 038-Gap-Analysis Implementation Plan

## Overview
Implementation plan for all remaining gaps identified in ANALYSIS.md.
Organized into 6 sprints of ~4 tasks each.

**Baseline**: 1552 passing tests
**Target**: Close 100% of high-priority gaps (Sprints 1-3)

---

## SPRINT 1: Core Game Mechanics

Adds the most impactful missing game rules. All tasks are independent.

### CMD-01: Commander Rules

- **Description**: Full Commander format support beyond the existing command zone.
- **Files**: `mtg_engine/engine/formats/commander.py`
- **Tests**: `tests/engine/formats/test_commander.py`
- **Dependencies**: None
- **Effort**: 3-4 hours
- **Acceptance**:
  - [ ] Commander tax: +{2} per previous cast from command zone (tracked in GameState)
  - [ ] Commander damage: 21+ combat damage from one commander → player loses
  - [ ] Command zone replacement: commander would go to hand/library/exile/graveyard → may go to command zone instead (CR 903.9)
  - [ ] Color identity validation for deck building
  - [ ] Partner / Partner With support (two commanders)
  - [ ] Companion from sideboard (delegate to COM-01)
  - [ ] >= 8 tests covering tax, damage, replacement, partners
  - [ ] No regressions on 1552 existing tests

### MON-01: The Monarch

- **Description**: Monarch mechanic (Conspiracy/Commander). Draw at end step, change on combat damage.
- **Files**: `mtg_engine/engine/monarch.py`
- **Tests**: `tests/engine/test_monarch.py`
- **Dependencies**: None (hooks into turn_manager.py end step)
- **Effort**: 1-2 hours
- **Acceptance**:
  - [ ] GameState tracks `monarch: str | None`
  - [ ] When creature deals combat damage to monarch, attacker becomes monarch
  - [ ] At end of monarch's turn, they draw a card
  - [ ] Effects that reference monarch (e.g., "if you're the monarch") can query
  - [ ] >= 4 tests

### VEN-01: Venture into the Dungeon

- **Description**: Dungeon mechanic (AFR). Venture → advance room in a dungeon card.
- **Files**: `mtg_engine/engine/dungeon.py`, `mtg_engine/models/dungeon.py`
- **Tests**: `tests/engine/test_dungeon.py`
- **Dependencies**: None (standalone)
- **Effort**: 3-4 hours
- **Acceptance**:
  - [ ] Dungeon data model: rooms with name, abilities, room number
  - [ ] Three dungeons: Dungeon of the Mad Mage, Lost Mine of Phandelver, Tomb of Annihilation
  - [ ] `venture()` advances current room; if no dungeon, choose one
  - [ ] Completing a dungeon → reward, may start a new one
  - [ ] `completed_dungeons` counter on GameState for cards that count completions
  - [ ] >= 6 tests

### PRO-01: Proliferate System

- **Description**: Choose permanents/players with counters, add one more of each existing counter type.
- **Files**: `mtg_engine/engine/proliferate.py`
- **Tests**: `tests/engine/test_proliferate.py`
- **Dependencies**: None (uses existing counter system)
- **Effort**: 1-2 hours
- **Acceptance**:
  - [ ] `proliferate(game_state, choices: list[str])` adds counters
  - [ ] Only affects permanents/players that already have at least one counter
  - [ ] Handles multiple counter types on one permanent (+1/+1 and flying, etc.)
  - [ ] Emits CounterPlacedEvent for each counter added
  - [ ] Legal action for proliferate choices (add to _compute_legal_actions)
  - [ ] >= 4 tests

---

## SPRINT 2: Advanced Mechanics

### DNG-01: Day/Night Cycle

- **Description**: Day/night transform mechanic (Innistrad). ~90 cards affected.
- **Files**: `mtg_engine/engine/daynight.py`
- **Tests**: `tests/engine/test_daynight.py`
- **Dependencies**: Turn manager hooks
- **Effort**: 2-3 hours
- **Acceptance**:
  - [ ] GameState tracks `is_day: bool`, starts as day
  - [ ] Day → night: when a player ends their own turn without casting any spells
  - [ ] Night → day: when a player casts 2+ spells on their turn
  - [ ] Daybound/Nightbound cards transform on transition
  - [ ] Triggers: `TriggerDayTimeChanges` fires on transition
  - [ ] >= 5 tests

### INT-01: The Initiative

- **Description**: Initiative mechanic (Commander Legends: Baldur's Gate). Like monarch + venture.
- **Files**: `mtg_engine/engine/initiative.py`
- **Tests**: `tests/engine/test_initiative.py`
- **Dependencies**: MON-01 (end-step draw pattern), VEN-01 (venture into Undercity)
- **Effort**: 1 hour
- **Acceptance**:
  - [ ] GameState tracks `initiative: str | None`
  - [ ] Combat damage to initiative holder → attacker gains initiative
  - [ ] At beginning of initiative holder's upkeep, venture into Undercity dungeon
  - [ ] Undercity dungeon defined in VEN-01
  - [ ] >= 3 tests

### COM-01: Companion Mechanic

- **Description**: Companion from outside the game (IKO, Commander Legends).
- **Files**: `mtg_engine/ability/keywords/companion.py`
- **Tests**: `tests/ability/keywords/test_companion.py`
- **Dependencies**: Sideboard zone (exists), deck validation
- **Effort**: 2-3 hours
- **Acceptance**:
  - [ ] Companion keyword recognized from oracle text
  - [ ] Deck-building restriction check (e.g., "each card has CMC >= 3")
  - [ ] Once per game: pay {3} to put companion from sideboard into hand
  - [ ] Companion tracked on GameState for restriction validation
  - [ ] >= 4 tests

---

## SPRINT 3: Trigger & Keyword Coverage

### TRG-20: Top 10 Missing Trigger Categories

- **Description**: Add regex patterns for the 10 most impactful missing trigger types.
- **Files**: `mtg_engine/engine/triggers.py`
- **Tests**: `tests/engine/test_triggers_expanded.py`
- **Dependencies**: Existing triggers.py patterns
- **Effort**: 2-3 hours
- **Acceptance**:
  - [ ] Pattern for `becomes_target` (e.g., "whenever ~ becomes the target of a spell")
  - [ ] Pattern for `sacrificed` (e.g., "whenever you sacrifice a creature")
  - [ ] Pattern for `countered` (e.g., "whenever a spell you control is countered")
  - [ ] Pattern for `transformed` (e.g., "whenever ~ transforms")
  - [ ] Pattern for `investigated` (e.g., "whenever you investigate")
  - [ ] Pattern for `fight` (e.g., "whenever ~ fights")
  - [ ] Pattern for `mana_expend` (e.g., "whenever you spend 3+ mana on a spell")
  - [ ] Pattern for `life_gained`/`life_lost` (fallback if bridge not active — bridge EVT-02 already covers)
  - [ ] Pattern for `token_created` (if not covered — TRIGGER_PATTERNS["token"] likely covers)
  - [ ] Pattern for `searched_library` (e.g., "whenever you search your library")
  - [ ] Each pattern: regex + entry in TRIGGER_PATTERNS dict + test card + test
  - [ ] >= 10 new tests (one per trigger type)

### KW-16..30: Top 15 High-Value Keywords

Pick the top 15 most-played keywords not yet formalized. Each follows the same pattern
as existing keyword modules (base.py → apply()/has_keyword() interface).

**Examples of candidates**: Scry, Ward, Kicker, Flashback, Equip, Storm, Cascade,
Cycling (exists), Foretell, Encore, Escape, Suspend, Dash, Morph, Dredge, Ninjutsu,
Crew, Convoke, Delve, Madness, Transmute, Buyback, Entwine, Fuse, Splice, Replicate,
Persist, Undying, Bestow, Evoke.

- **Files**: `mtg_engine/ability/keywords/{name}.py` (one per keyword)
- **Tests**: `tests/ability/keywords/test_{name}.py`
- **Dependencies**: KW-01 (base.py for keyword interface)
- **Effort**: 30-60 min per keyword
- **Template per keyword**:
  ```python
  class SomeKeyword(KeywordAbility):
      @staticmethod
      def has_keyword(card: dict) -> bool: ...
      @staticmethod
      def from_oracle_text(text: str) -> Optional["SomeKeyword"]: ...
      def apply(self, game_state, source, ...): ...
  ```
- **Acceptance per keyword**:
  - [ ] has_keyword() recognizes the keyword text
  - [ ] from_oracle_text() parses cost/value if applicable
  - [ ] apply() implements the keyword's mechanical effect
  - [ ] >= 3 tests per keyword

---

## SPRINT 4: Format Validation

### FMT-01: Format Rules Engine

- **Description**: Format validation for Standard, Pioneer, Modern, Legacy, Vintage, Commander, Pauper.
- **Files**: `mtg_engine/engine/formats/__init__.py`, `mtg_engine/engine/formats/banned.py`
- **Tests**: `tests/engine/formats/test_formats.py`
- **Dependencies**: Card data (Scryfall)
- **Effort**: 4-6 hours
- **Acceptance**:
  - [ ] Banned list data source (hardcoded or Scryfall-fetched) for each format
  - [ ] Restricted list (Vintage)
  - [ ] `validate_deck(cards, format)` → pass/fail + list of violations
  - [ ] Format-specific rules:
    - Commander: color identity, 100 cards singleton, commander must be legendary
    - Brawl: 60 cards, Standard-legal, commander must be legendary creature/planeswalker
    - Standard: cards from last ~2 years
    - Pauper: all common
  - [ ] Deck validation endpoint: `POST /deck/validate`
  - [ ] >= 8 tests

---

## SPRINT 5: Application Features

### APP-01: Card Search API

- **Description**: Search loaded card database by name, oracle text, mana cost, type, etc.
- **Files**: `mtg_engine/api/routers/card_search.py`
- **Tests**: `tests/api/test_card_search.py`
- **Dependencies**: Scryfall data loaded
- **Effort**: 2-3 hours

### APP-02: Deck Building AI

- **Description**: Given card pool + format + strategy, construct a legal deck.
- **Files**: `mtg_engine/ai/deck_builder.py`
- **Tests**: `tests/ai/test_deck_builder.py`
- **Dependencies**: FMT-01, card evaluation
- **Effort**: 4-6 hours

### APP-03: Game Replay

- **Description**: Step-through game replay from transcript.
- **Files**: `mtg_engine/export/replay.py`
- **Tests**: `tests/export/test_replay.py`
- **Dependencies**: Transcript system
- **Effort**: 3-4 hours

### APP-04: Spectate / WebSocket

- **Description**: WebSocket endpoint for live game state streaming.
- **Files**: `mtg_engine/api/ws.py`
- **Dependencies**: FastAPI WebSocket support
- **Effort**: 2-3 hours

### APP-05: Draft / Sealed Simulation

- **Description**: Bot-driven draft pick logic and sealed pool generation.
- **Files**: `mtg_engine/ai/draft.py`
- **Tests**: `tests/ai/test_draft.py`
- **Dependencies**: APP-02
- **Effort**: 6-8 hours

### APP-06: Player Stats / ELO

- **Description**: Win/loss tracking, ELO rating, matchup stats.
- **Files**: `mtg_engine/api/routers/stats.py`, `mtg_engine/models/stats.py`
- **Tests**: `tests/api/test_stats.py`
- **Dependencies**: Game recording exists
- **Effort**: 2-3 hours

---

## DEPENDENCY GRAPH

```
CMD-01 ──┐
MON-01 ──┤
VEN-01 ──┤── Sprint 1 (no cross-deps)
PRO-01 ──┘

DNG-01 ──┐
INT-01 ──┤── depends on MON-01, VEN-01
COM-01 ──┘

TRG-20 ───── Sprint 3 (no cross-deps)
KW-16..30 ──┘

FMT-01 ───── Sprint 4 (depends on card data)

APP-01 ─┐
APP-02 ─┤── Sprint 5 (APP-02 depends on FMT-01)
APP-03 ─┤
APP-04 ─┘
APP-05 ─── depends on APP-02
APP-06 ─── depends on recording system
```

---

## EXECUTION RULES

1. **Run full test suite after each task**: `pytest tests/ -x -q` — must not regress
2. **One task in progress at a time** (mark in AGENTS.md)
3. **Update ANALYIS.md**: mark completed items with ✅
4. **Update AGENTS.md**: note new active technologies/files
5. **Commit only when asked**

---

## FILE TREE (to be created)

```
mtg_engine/
├── engine/
│   ├── formats/
│   │   ├── __init__.py
│   │   ├── commander.py   (CMD-01)
│   │   └── banned.py      (FMT-01)
│   ├── daynight.py        (DNG-01)
│   ├── dungeon.py         (VEN-01)
│   ├── initiative.py      (INT-01)
│   ├── monarch.py         (MON-01)
│   ├── proliferate.py     (PRO-01)
│   └── triggers.py        (TRG-20 — modified)
├── ability/keywords/
│   └── companion.py       (COM-01)
├── models/
│   └── dungeon.py         (VEN-01)
├── ai/
│   ├── deck_builder.py    (APP-02)
│   └── draft.py           (APP-05)
├── export/
│   └── replay.py          (APP-03)
└── api/
    ├── routers/
    │   ├── card_search.py  (APP-01)
    │   ├── stats.py        (APP-06)
    │   └── ...
    └── ws.py               (APP-04)

tests/
├── engine/
│   ├── formats/
│   │   ├── test_commander.py  (CMD-01)
│   │   └── test_formats.py    (FMT-01)
│   ├── test_daynight.py       (DNG-01)
│   ├── test_dungeon.py        (VEN-01)
│   ├── test_initiative.py     (INT-01)
│   ├── test_monarch.py        (MON-01)
│   ├── test_proliferate.py    (PRO-01)
│   └── test_triggers_expanded.py  (TRG-20)
├── ability/keywords/
│   ├── test_companion.py      (COM-01)
│   └── test_{name}.py         (KW-16..30)
├── api/
│   ├── test_card_search.py    (APP-01)
│   └── test_stats.py          (APP-06)
├── ai/
│   ├── test_deck_builder.py   (APP-02)
│   └── test_draft.py          (APP-05)
└── export/
    └── test_replay.py         (APP-03)
```

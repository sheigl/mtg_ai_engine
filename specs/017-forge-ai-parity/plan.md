# Implementation Plan: Forge AI Parity

**Branch**: `017-forge-ai-parity` | **Date**: 2026-03-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-forge-ai-parity/spec.md`

---

## Summary

Bring the heuristic AI player to functional parity with Forge's AI system across 36 capabilities: intelligent target selection, full scoring for draw/ramp/wipes/tokens/fight/tutor/animate/goad/life-loss spells, planeswalker activation, equipment attachment, instant-speed mana holding (counterspells and combat tricks), sacrifice decisions, scry/surveil/connive/explore/mutate evaluation, mulligan decisions, graveyard casting, ETB/dies trigger scoring, safe-block classification, cascade/delayed trigger handling, Phyrexian mana cost evaluation, stack-aware responses and spell copying, transform/meld scoring, Fog defensive play, artifact/enchantment removal, next-turn attack prediction, multiplayer attack direction, cross-turn AIMemory with all 9 named categories, 1-turn lookahead simulation, holistic board position delta scoring, and a configurable AiPersonalityProfile with all AiProps flags.

Changes are concentrated in **`ai_client/`** (scoring logic, memory, profiles, lookahead) with smaller additions to **`mtg_engine/`** where new engine-side legal actions must be generated (graveyard casting, planeswalker abilities, mulligan endpoint, cascade choices).

---

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pydantic v2, httpx (all existing — no new dependencies required)
**Storage**: In-memory game state (existing GameManager); AIMemory is per-game in-process only
**Testing**: pytest (existing); tests in `tests/` from project root
**Target Platform**: Linux server (existing)
**Project Type**: Python library + FastAPI web service
**Performance Goals**: AI decision under 500ms per action on standard 6-land / 4-permanent board (including 1-turn lookahead); existing 200ms legal-actions benchmark must be preserved
**Constraints**: No new third-party dependencies; all changes must be backward-compatible with the LLM player path (LLM player still receives full game state, target selection is AI-side only)
**Scale/Scope**: ~36 new/expanded scoring functions; ~9 AIMemory categories; ~10 personality profile properties; engine endpoints for graveyard casting, mulligan, planeswalker activation, cascade choice

---

## Constitution Check

*No constitution.md found — no gates to evaluate.*

---

## Project Structure

### Documentation (this feature)

```text
specs/017-forge-ai-parity/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── graveyard-actions.md
│   ├── mulligan-endpoint.md
│   ├── planeswalker-actions.md
│   └── cascade-choice.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code Layout

```text
ai_client/
├── heuristic_player.py   # PRIMARY: all new scoring logic added here
├── models.py             # NEW: AIMemory, AiPersonalityProfile, BlockClassification
├── game_loop.py          # MODIFIED: pass AIMemory, handle mulligan, instant-speed pass
├── ai_player.py          # MINOR: pass AIMemory context to LLM prompt (optional)
└── lookahead.py          # NEW: LookaheadSimulator class

mtg_engine/
├── api/routers/game.py   # MODIFIED: graveyard casting actions, planeswalker actions,
│                         #           cascade choice endpoint, mulligan endpoint
├── engine/
│   ├── turn_manager.py   # MODIFIED: mulligan phase, graveyard zone casting
│   └── triggers.py       # MODIFIED: cascade trigger resolution, delayed triggers
├── models/
│   ├── game.py           # MINOR: graveyard zone field additions for flashback/escape
│   └── actions.py        # MINOR: mulligan request, cascade choice request models
└── card_data/
    └── ability_parser.py # MODIFIED: detect flashback/escape/graveyard keywords,
                          #           Phyrexian mana, Convoke, Delve, Emerge,
                          #           fight, goad, connive, explore, mutate, cascade,
                          #           animate, tutor/search, delayed trigger patterns

tests/
├── test_heuristic_ai.py        # NEW: all 36 acceptance scenario tests
├── test_ai_memory.py           # NEW: AIMemory category tests
├── test_personality_profile.py # NEW: profile flag and probability tests
├── test_lookahead.py           # NEW: lookahead simulation correctness + perf
├── test_mulligan.py            # NEW: mulligan decision tests
├── test_graveyard_casting.py   # NEW: flashback/escape/unearth engine tests
└── test_block_classification.py # NEW: SAFE/TRADE/CHUMP tests
```

**Structure Decision**: Single-project layout (existing). All AI-side logic remains in `ai_client/`; engine-side additions are additive to existing routers and engine modules. A new `ai_client/lookahead.py` module is created to isolate simulation complexity from the scoring module. The `models.py` in `ai_client/` is extended with the three new data structures.

---

## Complexity Tracking

No constitution violations. All additions extend existing modules or create new files within established directories.

---

## Phase 0: Research

*See [research.md](research.md)*

---

## Phase 1: Design

*See [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)*

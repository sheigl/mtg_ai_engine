# Implementation Plan: Rules Engine Completeness

**Branch**: `014-rules-engine-completeness` | **Date**: 2026-03-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-rules-engine-completeness/spec.md`

## Summary

Extend the existing MTG rules engine to correctly handle 7 categories of rules gaps identified against Forge's implementation: deck-out SBA (CR 704.5b), combat damage triggers, hybrid/Phyrexian mana validation, damage prevention replacement effects, full 7-layer continuous effect coverage, attack/block constraint enforcement (Propaganda, goad, must-attack, can't-block), and stack copy effects with phase skipping. All work is additive to existing modules — no rewrites.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pydantic v2, pytest (all existing — no new dependencies)
**Storage**: In-memory GameState (Pydantic models); no persistence changes
**Testing**: pytest (`python -m pytest tests/ -v`)
**Target Platform**: Linux server (same as existing)
**Project Type**: Library/web-service (internal rules engine + REST API)
**Performance Goals**: Existing — no new performance targets
**Constraints**: Backward-compatible; existing test suite must remain green
**Scale/Scope**: ~7 engine modules modified; ~4 new model fields; 2 new model classes

## Constitution Check

No constitution.md file found — no gate violations to evaluate.

## Project Structure

### Documentation (this feature)

```text
specs/014-rules-engine-completeness/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (not applicable — internal engine)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
mtg_engine/
├── engine/
│   ├── sba.py               # US1: add CR 704.5b deck-out SBA check
│   ├── triggers.py          # US2: add check_damage_triggers() after combat damage
│   ├── mana.py              # US3: add hybrid + Phyrexian validation in _can_pay_simple
│   ├── replacement.py       # US4: add PreventionEffect detection + damage prevention
│   ├── layers.py            # US5: add effect generators for layers 1-5 (copy/control/type/color)
│   ├── combat.py            # US6/US7: call damage triggers; enforce combat constraints
│   └── zones.py             # US1: flag player on empty-library draw
├── models/
│   ├── game.py              # US6: add CombatConstraint, prevention_effects to GameState
│   └── actions.py           # US7: add CopySpellRequest action
└── api/
    └── routers/
        └── game.py          # US3/US6/US7: wire hybrid payment, copy spell endpoint, constraint enforcement

tests/
├── rules/
│   ├── test_sba.py          # US1: deck-out, PW loyalty tests
│   ├── test_triggers.py     # US2: damage trigger tests
│   ├── test_mana.py         # US3: hybrid + Phyrexian tests
│   ├── test_replacement.py  # US4: prevention effect tests
│   ├── test_layers.py       # US5: layer 1-5 coverage tests
│   ├── test_legal_actions.py # US6: combat constraint tests
│   └── test_stack.py        # US7: copy spell tests
```

**Structure Decision**: Single project (existing layout). All changes are additive to existing engine modules. No new top-level files required except `quickstart.md` and `data-model.md` in the spec directory.

## Complexity Tracking

No constitution violations — table omitted.

# Implementation Plan: Player Default Settings

**Branch**: `028-player-default-settings` | **Date**: 2026-04-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/028-player-default-settings/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add per-player-type default settings persisted in MongoDB. Administrators can save/retrieve defaults for `human`, `ai`, and `heuristic` player types. New players created via game endpoints automatically receive the defaults for their type. Individual players can override defaults. The feature leverages the existing motor/MongoDB stack (Feature 025) and FastAPI patterns.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pydantic v2, motor (async MongoDB driver)
**Storage**: MongoDB (existing — adds `player_defaults` collection)
**Testing**: pytest
**Target Platform**: Linux server
**Project Type**: web-service
**Performance Goals**: Standard web app (<200ms p95 for CRUD, no special throughput requirements)
**Constraints**: MongoDB is optional; all settings endpoints must return 503 when MongoDB is not configured. Must not break existing game creation flow when MongoDB is absent.
**Scale/Scope**: Internal/small team use; settings documents are small (<100KB).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution file exists (`.specify/memory/constitution.md` not found). No gates to enforce.

**Re-check after Phase 1**: Design adds one new MongoDB collection (`player_defaults`), one new router module, and modifications to two existing router modules (`game.py`, `human_game.py`). No new projects, languages, or storage systems introduced. Complexity remains within existing architectural patterns.

## Project Structure

### Documentation (this feature)

```text
specs/028-player-default-settings/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
mtg_engine/
├── api/
│   ├── main.py                 # register new router
│   ├── routers/
│   │   ├── player_defaults.py  # NEW: CRUD endpoints for player-type defaults
│   │   ├── game.py             # MODIFIED: apply defaults on game creation
│   │   ├── human_game.py       # MODIFIED: apply defaults on game creation
│   │   └── ai_game.py          # MODIFIED: apply defaults on game creation
│   └── game_manager.py         # MODIFIED: accept per-player settings override
├── persistence/
│   ├── mongo_client.py         # MODIFIED: add player_defaults collection getter
│   └── player_defaults.py      # NEW: async CRUD + validation for player_defaults
├── models/
│   └── player_defaults.py      # NEW: Pydantic models for settings payload + API requests/responses
└── tests/
    ├── unit/
    │   └── test_player_defaults.py
    └── integration/
        └── test_player_defaults_api.py
```

**Structure Decision**: Single FastAPI web-service project. New modules follow existing conventions: routers in `api/routers/`, persistence helpers in `persistence/`, Pydantic models in `models/`. No frontend changes required for v1 (admin CRUD via API only).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All changes fit within the existing single-project, single-language, single-storage architecture.

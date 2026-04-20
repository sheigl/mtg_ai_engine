# Implementation Plan: MongoDB Game Data Persistence

**Branch**: `025-mongodb-persistence` | **Date**: 2026-04-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-mongodb-persistence/spec.md`

## Summary

Persist all game training data — transcript events, board snapshots, AI decisions, observer commentary, player annotations, and game outcomes — to MongoDB automatically as games are played. Data is written incrementally via the existing listener pattern on each recorder, using async fire-and-forget writes that do not block the game loop. MongoDB is optional: if `MONGODB_URL` is not set, the system behaves identically to today. A new query API (`GET /games/records`) lets training pipelines retrieve completed game records without downloading files.

## Technical Context

**Language/Version**: Python 3.11 (backend, matches existing codebase)
**Primary Dependencies**: FastAPI, Pydantic v2 (existing); `motor>=3.3.0` (new — async MongoDB driver for asyncio/FastAPI)
**Storage**: MongoDB (new, external); existing in-memory `GameExportStore` recorders unchanged
**Testing**: pytest (existing)
**Target Platform**: Linux server (existing)
**Project Type**: Web service (existing FastAPI app, additive changes only)
**Performance Goals**: All events persisted within 2 seconds of occurrence; query API returns 1,000 records in under 10 seconds
**Constraints**: MongoDB unavailability must not interrupt gameplay; `motor` is the only new dependency; no changes to game engine or rules logic
**Scale/Scope**: Per-game documents; typical size 1–5MB per completed game; designed for hundreds of games per day

## Constitution Check

No project constitution file found. Proceeding with standard quality gates:

- **No unnecessary new dependencies**: ✅ Only `motor` (the official async MongoDB driver) is added
- **Backend changes are additive**: ✅ New `mtg_engine/persistence/` module; existing recorders gain listener methods only
- **Game engine untouched**: ✅ All changes are in persistence layer and API routers — zero engine/rules changes
- **Graceful degradation**: ✅ MongoDB optional; game loop never blocked by write failures
- **Training data invariant preserved**: ✅ `rating` (original AI value) never modified; only `player_rating_override` and `player_annotation` are updatable post-write
- **Existing test suite unaffected**: ✅ New fields and module are additive; no existing tests need modification
- **File export compatibility**: ✅ Existing `GET /export/{game_id}/game-log` endpoint behavior preserved

## Project Structure

### Documentation (this feature)

```text
specs/025-mongodb-persistence/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── persistence-api.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code

```text
# New module
mtg_engine/persistence/
├── __init__.py
├── mongo_client.py          # NEW: AsyncIOMotorClient singleton
└── game_persister.py        # NEW: MongoGamePersister listener class

# Modified backend files
mtg_engine/
├── export/
│   ├── snapshots.py         # MODIFY: add listener support to SnapshotRecorder
│   └── store.py             # MODIFY: register MongoGamePersister when configured
├── api/
│   ├── main.py              # MODIFY: include game_records router; extend /health
│   ├── game_manager.py      # MODIFY: add player_1_type/player_2_type params
│   └── routers/
│       ├── game_records.py  # NEW: GET /games/records, GET /games/records/{game_id}
│       ├── human_game.py    # MODIFY: pass player_1_type="human" on game create
│       ├── debug.py         # MODIFY: call persister.update_debug_entry() after annotate/rerate
│       └── export.py        # MODIFY: read from MongoDB when available for game-log

requirements.txt             # MODIFY: add motor>=3.3.0
```

**Structure Decision**: Additive changes to a single-project FastAPI layout. New `persistence/` module isolates all MongoDB code. No new directories outside `mtg_engine/`.

## Phase 0: Research

**Status**: Complete — see [research.md](research.md)

Key decisions:
- **Driver**: `motor` (async MongoDB driver) — native asyncio integration, no event loop blocking
- **Schema**: One document per game in `games` collection; `game_id` as `_id`; arrays for transcript/snapshots/debug/rules_qa
- **Write pattern**: Async `create_task()` fire-and-forget via listener callbacks; `$push` for array appends
- **Graceful degradation**: MongoDB optional via `MONGODB_URL`; all writes silent-fail with WARNING log
- **SnapshotRecorder**: Needs listener mechanism added (5-line change, same pattern as TranscriptRecorder)
- **Player type**: `create_game()` gets optional `player_1_type`/`player_2_type` params

## Phase 1: Design & Contracts

**Status**: Complete

Artifacts:
- [data-model.md](data-model.md) — MongoDB document schema, sub-document shapes, indexes, MongoGamePersister state
- [contracts/persistence-api.md](contracts/persistence-api.md) — new query endpoints and health extension
- [quickstart.md](quickstart.md) — file map, implementation order, test commands, training pipeline usage

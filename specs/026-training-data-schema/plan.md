# Implementation Plan: Training Data Schema — Decision-Centric MongoDB Persistence

**Branch**: `026-training-data-schema` | **Date**: 2026-04-20 | **Spec**: `specs/026-training-data-schema/spec.md`

## Summary

Redesign the MongoDB persistence layer from a single `games` document with embedded arrays to normalized collections (`games`, `decisions`, `rules_qa`, `transcript`). The `decisions` collection is the primary training artifact: one document per priority grant, self-contained with board state, LLM reasoning, observer evaluation, and outcome context — all queryable without joins.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, motor ≥ 3.3.0 (existing), React 18, TanStack Query v5 (existing)
**Storage**: MongoDB via motor async driver (`decisions`, `games`, `rules_qa`, `transcript` collections)
**Testing**: pytest (existing); integration tests against a real MongoDB instance
**Target Platform**: Linux server (uvicorn/asyncio)
**Project Type**: Web service (FastAPI) with background async writes
**Performance Goals**: All MongoDB writes fire-and-forget; 10k decisions enumerable in < 60s via indexes
**Constraints**: No migration of existing data; `MONGODB_URL` env var as feature flag; writes must never block or raise in game execution path
**Scale/Scope**: ~100–1000 priority grants per game; training sets of 10k–100k decisions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Single responsibility per collection | ✅ PASS | Each collection has one clear role |
| No breaking changes to existing in-memory recorders | ✅ PASS | Only MongoDB write path changes |
| Fire-and-forget writes | ✅ PASS | All writes via `_schedule()` pattern |
| Feature flag / optional persistence | ✅ PASS | `MONGODB_URL` env var gates everything |
| No new mandatory dependencies | ✅ PASS | `motor` already in requirements.txt |
| No migration required | ✅ PASS | New collection names; old data ignored |

## Project Structure

### Documentation (this feature)

```text
specs/026-training-data-schema/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── decisions-api.md
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (affected files)

```text
mtg_engine/
├── models/
│   └── debug.py                  # Add snapshot_id, related_entry_id to DebugEntry
├── export/
│   ├── store.py                  # Expose current_snapshot_id; update persister wiring
│   ├── snapshots.py              # record_snapshot() returns snap (already does); no model change
│   └── rules_qa.py               # QAPair gains decision_id field; RulesQARecorder accepts snapshot_id
├── persistence/
│   ├── mongo_client.py           # Add get_decisions_collection(), get_rules_qa_collection(),
│   │                             #   get_transcript_collection()
│   └── game_persister.py         # Full redesign: write to normalized collections
└── api/
    └── routers/
        ├── game.py               # legal-actions returns snapshot_id in response
        ├── debug.py              # annotate/rerate update decisions collection, not games
        ├── export.py             # game-log endpoint adapts to new schema
        └── game_records.py       # Query decisions collection; new /decisions endpoint

ai_client/
└── game_loop.py                  # Pass snapshot_id when creating debug entries
    hybrid_game_loop.py           # Same: pass snapshot_id
```

**Structure Decision**: Single-project layout (existing). All changes are within the existing directory tree. No new top-level packages.

## Complexity Tracking

No constitution violations. No complexity table needed.

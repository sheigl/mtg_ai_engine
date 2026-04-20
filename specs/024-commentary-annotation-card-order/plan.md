# Implementation Plan: Commentary Annotations, Rating Override & Card Ordering

**Branch**: `024-commentary-annotation-card-order` | **Date**: 2026-04-19 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/024-commentary-annotation-card-order/spec.md`

## Summary

Add three quality-of-life and training-data features to the human-vs-AI game board:
(1) Players can annotate any completed debug/commentary entry with free-text comments, persisted server-side and included in game log exports;
(2) Players can override the observer AI's rating (Good/Acceptable/Suboptimal) on commentary entries while preserving the original AI rating for training data integrity;
(3) Players can drag cards within their hand and battlefield to reorder them cosmetically without affecting game state.

The backend approach extends the existing `DebugEntry` model with two new nullable fields and adds two focused API endpoints. The frontend extends `CommentaryBlock` and `PromptResponseBlock` with annotation/override UI, and adds intra-zone drag-to-reorder to `InteractiveHand` and `Battlefield`.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, Pydantic v2 (backend); React 18, TanStack Query v5, Framer Motion (frontend) — all existing, no new deps  
**Storage**: In-memory `DebugLogRecorder` per game (existing); no persistence changes  
**Testing**: pytest (backend); tsc + manual browser testing (frontend)  
**Target Platform**: Linux server (backend); modern browser (frontend)  
**Project Type**: Web service + SPA  
**Performance Goals**: Annotation/rerate API calls < 100ms; reorder gesture is purely client-side (zero latency)  
**Constraints**: Original AI rating must never be overwritten; card reordering must not alter game state or legal actions  
**Scale/Scope**: Single-game session scope; debug entries live in memory for game lifetime

## Constitution Check

No project constitution file found (`.specify/memory/constitution.md` does not exist). Proceeding with standard quality gates:

- **No new dependencies introduced**: ✅ All libraries already in use
- **Backend changes are additive**: ✅ Two new endpoints, two new nullable model fields
- **No server-side game state changes from card reordering**: ✅ Reorder is client-side only
- **Original AI rating invariant enforced at API layer**: ✅ Separate `/rerate` endpoint; `/annotate` endpoint never touches `rating`
- **Existing test suite unaffected**: ✅ New fields are optional (None by default); existing tests need no changes

## Project Structure

### Documentation (this feature)

```text
specs/024-commentary-annotation-card-order/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── debug-api.md     # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code

```text
# Backend
mtg_engine/
├── models/
│   └── debug.py                    # MODIFY: add player_annotation, player_rating_override
├── export/
│   ├── debug_log.py                # MODIFY: add annotate_entry(), rerate_entry()
│   └── game_log.py                 # MODIFY: accept debug_entries param; merge into output
└── api/
    └── routers/
        ├── debug.py                # MODIFY: add /annotate and /rerate endpoints
        └── export.py               # MODIFY: pass debug entries to build_game_log()

tests/
└── api/
    └── test_debug_annotations.py   # NEW: annotation + rerate endpoint tests

# Frontend
frontend/src/
├── types/
│   └── debug.ts                    # MODIFY: add player_annotation, player_rating_override to DebugEntry
├── components/
│   ├── CommentaryBlock.tsx         # MODIFY: rating override picker + annotation input/display
│   ├── PromptResponseBlock.tsx     # MODIFY: annotation input/display only
│   ├── InteractiveHand.tsx         # MODIFY: accept handOrder prop; intra-zone drag-to-reorder
│   ├── Battlefield.tsx             # MODIFY: accept permanentOrder prop; sort before render
│   └── HumanGameBoard.tsx          # MODIFY: handOrder + permanentOrder state; wire to children
└── styles/
    └── debug.css                   # MODIFY: styles for annotation input, rating override picker
```

**Structure Decision**: Single web-application layout with backend API and React SPA. No new directories created. All changes are additive modifications to existing files.

## Phase 0: Research

**Status**: Complete — see [research.md](research.md)

Key decisions:
- Add `player_annotation` and `player_rating_override` directly to `DebugEntry` model
- Two new dedicated endpoints (`/annotate`, `/rerate`) to keep AI streaming path untouched
- Game log integration via optional `debug_entries` parameter to `build_game_log()`
- HTML5 drag-and-drop for card reordering (no new dependency); distinguish from card-play drag via separate state flag

## Phase 1: Design & Contracts

**Status**: Complete

Artifacts:
- [data-model.md](data-model.md) — DebugEntry extensions, client-side card order state, game log format
- [contracts/debug-api.md](contracts/debug-api.md) — new endpoint contracts and modified response shapes
- [quickstart.md](quickstart.md) — file map, implementation order, test commands

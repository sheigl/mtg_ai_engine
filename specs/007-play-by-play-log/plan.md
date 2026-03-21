# Implementation Plan: Play-by-Play Game Log

**Branch**: `007-play-by-play-log` | **Date**: 2026-03-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-play-by-play-log/spec.md`

## Summary

Add an opt-in verbose logging mode that prints a human-readable play-by-play narrative of every substantive game event (player moves, phase transitions, life changes, zone transitions, game end) as it occurs during a game simulation. The feature surfaces data already tracked by the existing `TranscriptRecorder` — supplemented with missing life-change and draw events — and routes it to stdout/log output when a per-game verbose flag is enabled.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pydantic v2, standard `logging` module
**Storage**: In-memory only (per-game lifetime); no persistence needed for this feature
**Testing**: pytest
**Target Platform**: Linux server (Docker)
**Project Type**: Web service (REST API)
**Performance Goals**: No measurable throughput degradation when verbose mode is disabled (SC-004)
**Constraints**: Output must be human-readable plain text; no structured data format required
**Scale/Scope**: One `VerboseLogger` instance per game, active only when enabled

## Constitution Check

*No constitution.md found — no gates to evaluate.*

## Project Structure

### Documentation (this feature)

```text
specs/007-play-by-play-log/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── verbose-log-api.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
mtg_engine/
├── engine/
│   └── verbose_log.py          # NEW: VerboseLogger + PlayByPlayFormatter
├── export/
│   └── transcript.py           # MODIFY: add record_life_change, record_draw, record_game_end
└── api/
    ├── game_manager.py         # MODIFY: per-game VerboseLogger attachment + toggle method
    └── routers/
        └── game.py             # MODIFY: accept verbose flag on POST /game; add toggle endpoint

tests/
└── rules/
    └── test_verbose_log.py     # NEW: unit + integration tests
```

**Structure Decision**: Single project (Option 1). This feature is a pure enhancement to the existing `mtg_engine` package — no new top-level directories needed.

## Complexity Tracking

*(No constitution violations to justify.)*

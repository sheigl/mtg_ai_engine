# Implementation Plan: UI Game Creator

**Branch**: `015-ui-game-creator` | **Date**: 2026-03-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-ui-game-creator/spec.md`

## Summary

Add a game creation form to the web UI that exposes all options available in the `ai_client` CLI. A new `POST /ai-game` backend endpoint accepts the full game config, creates the game via the existing engine, and starts the AI decision loop in a background thread — returning a `game_id` immediately so the UI can navigate to the live game board. The frontend gains a modal form accessible from the game list page.

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, httpx, openai (all existing); React 18, TanStack Query v5 (all existing) — no new dependencies
**Storage**: In-memory game state (existing); no persistence changes
**Testing**: pytest (backend); no new frontend test framework needed
**Target Platform**: Linux server + browser (same as existing)
**Project Type**: Web service + SPA (existing architecture)
**Performance Goals**: Game creation endpoint responds within 2 seconds; form submission feedback within 3 seconds
**Constraints**: AI loop must not block the FastAPI event loop; must reuse existing `GameLoop` and `ai_client` machinery
**Scale/Scope**: 1 new backend router, 1 new frontend component, 2 modified existing files

## Constitution Check

No constitution.md file found — no gate violations to evaluate.

## Project Structure

### Documentation (this feature)

```text
specs/015-ui-game-creator/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── ai-game-api.md   # POST /ai-game contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
mtg_engine/
├── api/
│   ├── main.py                    # MODIFY: register ai_game router
│   └── routers/
│       └── ai_game.py             # NEW: POST /ai-game endpoint

ai_client/
├── game_loop.py                   # MODIFY: accept optional pre-created game_id
│                                  # (skip game creation step when game_id provided)

frontend/src/
├── components/
│   ├── GameList.tsx               # MODIFY: add "New AI Game" button
│   └── CreateGameForm.tsx         # NEW: game creation modal form
└── styles/
    └── create-game.css            # NEW: form styles
```

**Structure Decision**: Additive to the existing web-service + SPA architecture. The backend gains one new router module; the frontend gains one new component and one CSS file. No new top-level directories.

## Complexity Tracking

No constitution violations — table omitted.

# Implementation Plan: Observer AI Debug Panel

**Branch**: `011-observer-ai-commentary` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/011-observer-ai-commentary/spec.md`

## Summary

Add an opt-in debug panel to the observer UI that shows (1) the exact prompt sent to each playing AI and its streaming response as it decides, and (2) a third-party observer AI's commentary rating each non-pass action as good/acceptable/suboptimal with alternative play suggestions. The panel is off by default; no extra LLM calls are made unless explicitly enabled.

The primary technical challenge is bridging three separate processes — the engine (FastAPI), the AI client (CLI), and the browser — so the browser can see AI prompts and streaming tokens in near-real time. The chosen approach is: the AI client POSTs structured debug entries to the engine, the engine fans them out over Server-Sent Events (SSE) to any connected browser, and the frontend subscribes to the SSE stream when the debug panel is enabled.

## Technical Context

**Language/Version**: Python 3.11 (backend + AI client), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, httpx, openai (OpenAI-compatible client), React 18, TanStack Query v5
**Storage**: In-process memory (DebugLogRecorder added alongside existing TranscriptRecorder/SnapshotRecorder)
**Testing**: pytest (backend unit + integration), vitest (frontend)
**Target Platform**: Linux server (localhost), browser (Chrome/Firefox)
**Project Type**: Web service + CLI + SPA
**Performance Goals**: First debug entry visible <1s after action; streaming updates ≥5×/sec
**Constraints**: No Docker; `uvicorn` on localhost; must not slow down game actions; panel off by default
**Scale/Scope**: 2-player games; 200 debug entries per game maximum in v1

## Constitution Check

No constitution.md is present in this project. All design decisions are made against the existing codebase conventions:

- ✅ **New models use Pydantic v2** — DebugEntry/DebugLog follow existing model patterns in `mtg_engine/models/`
- ✅ **New endpoints follow existing router pattern** — prefix `/game`, wrapped in `{"data": ...}` envelope
- ✅ **New recorder follows existing export pattern** — DebugLogRecorder mirrors TranscriptRecorder
- ✅ **AI client changes are additive** — existing `AIPlayer.decide()` contract preserved; debug forwarding is opt-in
- ✅ **Frontend follows existing hook+component pattern** — `useDebugLog` mirrors `useTranscript`, `DebugPanel` mirrors `ActionLog`
- ✅ **SSE is the minimal addition** — avoids WebSocket complexity; EventSource is native browser API

## Project Structure

### Documentation (this feature)

```text
specs/011-observer-ai-commentary/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── debug-entry-post.md
│   └── debug-sse-stream.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code

```text
mtg_engine/
├── models/
│   └── debug.py                    # NEW — DebugEntry, DebugLog Pydantic models
├── export/
│   └── debug_log.py                # NEW — DebugLogRecorder (in-memory per game)
└── api/
    └── routers/
        └── debug.py                # NEW — /game/{id}/debug endpoints + SSE stream

ai_client/
├── observer.py                     # NEW — ObserverAI class (commentary generation)
├── ai_player.py                    # MODIFIED — capture prompt + stream, POST to engine
└── game_loop.py                    # MODIFIED — wire up debug posting and observer

frontend/src/
├── components/
│   ├── DebugPanel.tsx              # NEW — outer panel container + toggle
│   ├── PromptResponseBlock.tsx     # NEW — collapsible prompt + streaming response
│   └── CommentaryBlock.tsx         # NEW — observer AI commentary entry
├── hooks/
│   └── useDebugLog.ts              # NEW — SSE subscription + fallback polling
├── styles/
│   └── debug.css                   # NEW — debug panel layout and block styles
└── types/
    └── debug.ts                    # NEW — TypeScript interfaces for DebugEntry
```

**Structure Decision**: Additive — all new files follow existing patterns. `debug.py` router registered in `main.py` under the existing `/game` prefix. `DebugLogRecorder` created alongside `TranscriptRecorder` in `store.py`.

## Complexity Tracking

No constitution violations. No unusual complexity introduced.

## Implementation Phases

### Phase A — Backend Debug Log Infrastructure

**Goal**: Engine can accept, store, and stream debug entries.

1. **`mtg_engine/models/debug.py`** — Pydantic models:
   - `DebugEntryType` enum: `prompt_response`, `commentary`
   - `DebugEntry` model: `entry_id` (UUID), `entry_type`, `source` (player name or "Observer AI"), `turn`, `phase`, `step`, `timestamp`, `prompt` (str), `response` (str, may be partial), `is_complete` (bool), `rating` (str | None), `explanation` (str | None), `alternative` (str | None)
   - `DebugLog` model: `game_id`, `entries: list[DebugEntry]`

2. **`mtg_engine/export/debug_log.py`** — `DebugLogRecorder`:
   - `append_entry(entry: DebugEntry)` — adds to in-memory list
   - `patch_entry(entry_id, response_chunk, is_complete)` — appends to response text of an existing entry (streaming updates)
   - `get_all()` → `list[DebugEntry]`
   - `register_listener(callback)` — same listener pattern as `TranscriptRecorder`; called on every append/patch

3. **Register in `mtg_engine/export/store.py`** — Add `debug_log: DebugLogRecorder` to `GameExportStore`; initialize on game creation.

4. **`mtg_engine/api/routers/debug.py`** — New router under `/game/{game_id}/debug`:
   - `POST /game/{game_id}/debug/entry` — Accepts a `DebugEntry` body; appends to the game's `DebugLogRecorder`. Returns 200 or 404.
   - `PATCH /game/{game_id}/debug/entry/{entry_id}` — Appends a `response_chunk` to an existing entry; marks complete if `is_complete=true`.
   - `GET /game/{game_id}/debug` — Returns all entries as `{"data": [DebugEntry, ...]}`. Used for historical games.
   - `GET /game/{game_id}/debug/stream` — SSE endpoint. Registers a listener on the recorder and fans out every new/patched entry as a `data:` SSE event. Keeps connection alive until game ends or client disconnects.

5. **Register debug router in `mtg_engine/api/main.py`**.

---

### Phase B — AI Client Prompt Capture

**Goal**: Every LLM call made by a playing AI is captured and forwarded to the engine as a debug entry.

1. **Modify `ai_client/ai_player.py`**:
   - Add optional `debug_callback: Callable[[str, str], None] | None = None` to `AIPlayer.__init__`
   - In `decide(prompt)`:
     - If callback set: call `callback("prompt", prompt)` immediately before the LLM call
     - After response received: call `callback("response", response_text)`
   - This keeps `AIPlayer` decoupled from HTTP; the caller (game_loop) wires up the callback.

2. **Modify `ai_client/game_loop.py`**:
   - If `--debug` flag is set (new CLI arg), create a `DebugForwarder` helper:
     - `post_prompt_entry(player_name, turn, phase, step, prompt)` → `POST /game/{id}/debug/entry` returns `entry_id`
     - `patch_response(entry_id, chunk, is_complete)` → `PATCH /game/{id}/debug/entry/{entry_id}`
   - Wire `DebugForwarder` callbacks into each player's `AIPlayer` before the game loop runs.
   - After each non-pass action resolves, if debug enabled, invoke the observer AI (Phase C).

---

### Phase C — Observer AI

**Goal**: After each non-pass action, an LLM-backed observer analyzes the play and posts commentary.

1. **`ai_client/observer.py`** — `ObserverAI` class:
   - `__init__(client_config, engine_client)` — takes same LLM config as `AIPlayer`
   - `analyze(game_state, chosen_action, legal_actions, player_name, turn, phase, step)` → posts a commentary `DebugEntry` to the engine
   - Builds an observer prompt: presents the game state snapshot, the action chosen, and the full legal action list; asks the LLM to rate the play (good/acceptable/suboptimal), explain why, and suggest a better alternative if applicable
   - Calls the LLM (non-streaming is fine for observer since it's async and doesn't gate gameplay)
   - POSTs the completed `DebugEntry` with `entry_type=commentary`

2. **Wire into `game_loop.py`**:
   - After a non-pass action is submitted and resolved, if debug enabled, call `observer.analyze(...)` asynchronously (does not block next priority poll)

---

### Phase D — Frontend Debug Panel

**Goal**: The observer UI shows the debug panel when enabled, updating in real time via SSE.

1. **`frontend/src/types/debug.ts`** — TypeScript interfaces matching `DebugEntry` Pydantic model.

2. **`frontend/src/hooks/useDebugLog.ts`**:
   - Accepts `gameId` and `enabled: boolean`
   - When `enabled=true` and game is live: opens `EventSource` to `GET /game/{gameId}/debug/stream`
   - On each SSE event: parses the `DebugEntry` JSON and updates a local `entries` array (upsert by `entry_id` to handle streaming patches)
   - When `enabled=true` and game is completed: falls back to polling `GET /game/{gameId}/debug` via TanStack Query (same pattern as `useTranscript`)
   - When `enabled=false`: returns empty entries and makes no requests

3. **`frontend/src/components/PromptResponseBlock.tsx`**:
   - Collapsible block; expanded by default, collapses on click of header
   - Header: source label (player name), turn/step badge
   - Body: prompt text in a monospace scrollable box + response text (auto-scrolls as tokens arrive)
   - Visual: left border color keyed to player (P1 = green, P2 = blue)
   - Shows "(incomplete)" indicator while `is_complete=false`

4. **`frontend/src/components/CommentaryBlock.tsx`**:
   - Collapsible block; visually distinct from prompt/response blocks (amber left border)
   - Header: "Observer AI" label + rating badge (color-coded: green=good, yellow=acceptable, red=suboptimal)
   - Body: explanation text + optional "Better play:" section

5. **`frontend/src/components/DebugPanel.tsx`**:
   - Container rendered alongside `GameBoard`
   - Toggle button: "Debug Panel" with on/off state (persisted in `localStorage`)
   - Renders list of blocks from `useDebugLog` in chronological order, mixing `PromptResponseBlock` and `CommentaryBlock` by `timestamp`
   - Auto-scrolls to bottom when new entries arrive (same pattern as `ActionLog`)
   - Shows "Debug panel disabled — enable to see AI prompts and commentary" when off

6. **Integrate into `frontend/src/components/GameBoard.tsx`**:
   - Import and render `DebugPanel` alongside the existing `ActionLog` sidebar
   - Pass `gameId` and `enabled` state down

7. **`frontend/src/styles/debug.css`** — Panel layout, block styles, rating badges.

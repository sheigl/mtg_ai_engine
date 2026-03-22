# Research: Observer AI Debug Panel

**Feature**: 011-observer-ai-commentary
**Date**: 2026-03-22

---

## Decision 1: How to get AI prompts/responses to the browser in near-real time

**Question**: The AI client (a separate CLI process) makes LLM calls. The browser needs to see tokens as they stream. What's the minimal architecture that achieves ≥5 updates/second?

**Decision**: AI client POSTs structured debug entries to the engine via HTTP; engine fans them out to the browser over Server-Sent Events (SSE).

**Rationale**:
- The AI client already talks to the engine via HTTP (`httpx`) — adding debug POSTs requires no new transport.
- SSE is a one-way stream from server → browser over a plain HTTP connection. The browser's native `EventSource` API requires no library. FastAPI supports SSE via `StreamingResponse` with `text/event-stream` content-type.
- SSE satisfies the ≥5 updates/second requirement: each streaming patch from the AI client is immediately forwarded to any listening `EventSource` connections.
- WebSocket was considered but rejected: it requires a two-way protocol and a more complex FastAPI integration (e.g., `starlette.websockets`), with no benefit over SSE for a unidirectional server-push use case.
- Long-polling was considered but rejected: each poll closes and reopens the connection, introducing 100-500ms round-trip overhead that violates the streaming latency requirement.

**Alternatives considered**:
- WebSocket — bidirectional, more complex, no benefit here
- Long polling — too much latency for token-by-token streaming
- Redis pub/sub — introduces a new infrastructure dependency; unnecessary for a single-host dev tool
- AI client writes to a shared file; frontend polls the file — doesn't work across network; not REST-native

---

## Decision 2: Where does the Observer AI run?

**Question**: The observer AI needs to call an LLM. Should it run inside the engine process or in the AI client process?

**Decision**: Observer AI runs in the AI client process, as a new `ObserverAI` class in `ai_client/observer.py`.

**Rationale**:
- The engine currently has no LLM dependencies. Adding one would couple the engine to Ollama configuration and introduce latency on the action-processing path.
- The AI client already manages `openai`-compatible LLM calls, retry logic, and prompt building. The observer pattern fits naturally alongside `AIPlayer`.
- The observer is invoked after each non-pass action is confirmed (game state has advanced), so it never blocks priority processing.
- The observer posts its result to the engine via the same `POST /game/{id}/debug/entry` endpoint as the prompt/response entries, keeping the engine as the single source of truth for debug data.

**Alternatives considered**:
- Engine-side observer — tightly couples engine to LLM infrastructure; adds latency on action paths
- Separate observer process — more operational complexity; shared nothing between observer and AI client; the observer needs the same game state the AI client already has

---

## Decision 3: Streaming — full response at once vs. incremental patches

**Question**: Should the AI client send the full response after it completes, or send chunks as they arrive? The OpenAI-compatible API supports streaming mode (`stream=True`).

**Decision**: Use streaming mode (`stream=True`) for playing AI calls when debug is enabled; send an initial `POST` with the prompt, then `PATCH` as chunks arrive, marking `is_complete=True` on the final chunk.

**Rationale**:
- Streaming mode is required to meet the "≥5 updates/second" success criterion. Without it, the full response is withheld until the LLM finishes, then sent all at once.
- The current `AIPlayer.decide()` uses non-streaming mode. When debug is enabled, the call switches to `stream=True` and collects chunks for both the browser (forwarded via PATCH) and internal response parsing (accumulated for JSON extraction).
- When debug is disabled, behavior is unchanged — no streaming, no extra HTTP calls.

**Alternatives considered**:
- Non-streaming + single POST after completion — simpler but violates SC-002; response appears all at once after LLM finishes
- Streaming without storing partial responses — the frontend would need to reconstruct tokens from events, adding client complexity

---

## Decision 4: How the frontend manages the SSE stream vs. polling for historical games

**Question**: SSE is appropriate for live games. For completed games, the stream is closed. How does the frontend handle this?

**Decision**: `useDebugLog` hook checks game status. For live games, it opens an `EventSource` connection. For completed games (or when the stream closes), it falls back to a single `GET /game/{id}/debug` fetch via TanStack Query (no refetch interval needed for completed games).

**Rationale**:
- Games already have an `is_game_over` flag available from `useGameState`. The hook uses this to decide which fetch strategy to use.
- TanStack Query is already used for all polling in the project — consistent approach.
- `EventSource` reconnects automatically on drop but does NOT reconnect if the server closes the connection cleanly (status 200 with no more events). We signal game-over to the frontend by having the SSE endpoint send a final `event: game_over` event before closing, so the frontend knows to switch to the static fetch.

**Alternatives considered**:
- Always poll — simpler but cannot meet the 1s/5×-per-second streaming requirement
- Always SSE even for completed games — SSE endpoint would need to replay history on connect; simpler to just return a plain JSON response for the historical case

---

## Decision 5: Opt-in toggle persistence

**Question**: Should the debug panel toggle be stored in localStorage (survives page refresh), in React state (resets on reload), or in a backend setting per game?

**Decision**: `localStorage` with key `mtg_debug_panel_enabled`.

**Rationale**:
- Developers typically want the debug panel on or off consistently across multiple games. `localStorage` preserves this preference without any backend change.
- Per-game backend setting was considered (e.g., `POST /game/{id}/debug/enable`) but would require an extra endpoint and means different games could be in different states. The debug panel toggle is a UI preference, not a game setting.
- FR-002 says "panel is off by default" — `localStorage` defaults to `false` if key is absent.

---

## Decision 6: In-memory vs. persistent storage for debug logs

**Question**: Should debug entries be persisted to MongoDB or kept in-memory like the rest of the game state?

**Decision**: In-memory, consistent with all other game data in the project.

**Rationale**:
- All existing game data (GameState, TranscriptRecorder, SnapshotRecorder, RulesQARecorder) lives in-process memory. The spec note says MongoDB is used for training data "storage" but the actual implementation is in-memory only (confirmed by codebase exploration — `_store` dict in `store.py`).
- Adding MongoDB for debug logs alone would create an inconsistent two-tier storage architecture with no benefit for a single-host dev tool.
- Debug logs are ephemeral developer tools, not training data. They are accessible via `GET /game/{id}/debug` for the lifetime of the process.

**Alternatives considered**:
- MongoDB — consistent with spec description but inconsistent with actual implementation; adds infrastructure dependency
- SQLite — lighter than MongoDB but still a dependency; in-memory is sufficient

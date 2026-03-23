# Research: UI Game Creator

**Branch**: `015-ui-game-creator` | **Date**: 2026-03-23

## Decision 1: How to run the AI game loop from a web request

**Decision**: Start the AI loop in a daemon `threading.Thread` from the FastAPI endpoint handler, then return `game_id` immediately.

**Rationale**: The existing `GameLoop.run()` is synchronous and makes blocking HTTP calls (to the engine itself and optionally to LLM endpoints). Running it with `asyncio.run_in_executor` or `BackgroundTasks` inside FastAPI's async event loop would eventually block when the thread pool fills. A daemon thread is the simplest approach that keeps the request handler non-blocking and reuses all existing `GameLoop` code unchanged.

**Alternatives considered**:
- `asyncio.run_in_executor(None, loop.run)` — would work but shares FastAPI's default thread pool executor (max 5 threads on some systems), which could starve other requests during long games.
- FastAPI `BackgroundTasks` — runs after response is sent but still in the same asyncio task context; blocking calls inside it would stall the event loop.
- Celery / task queue — massive overkill for a local developer tool with no persistence or retry requirements.

---

## Decision 2: How the AI loop creates (or skips creating) the game

**Decision**: Modify `GameLoop` to accept an optional `game_id: str | None` parameter. When provided, skip the `create_game()` call and use the supplied ID directly. The backend endpoint creates the game first (via `GameManager` directly, not via HTTP), sets `game_id` on the loop, then starts the thread.

**Rationale**: The game must be created synchronously before the endpoint returns so the response can include `game_id`. The loop then only needs to drive actions. This keeps the existing loop logic intact and avoids double-creation.

**Alternatives considered**:
- Let the loop create the game as usual via HTTP self-call — works but adds one unnecessary round trip and requires knowing the engine's own URL.
- Extract a `run_from_existing_game(game_id)` method alongside `run()` — cleaner but more code duplication.

---

## Decision 3: LLM calls from the backend AI loop

**Decision**: The backend AI loop calls external LLM endpoints directly using the existing `AIPlayer` (httpx + openai-compatible client). The browser does not proxy or initiate LLM calls.

**Rationale**: LLM endpoints may not allow CORS from a browser; the existing `AIPlayer` class handles retries, fallback, and streaming callbacks. Running it server-side is consistent with CLI behaviour and does not expose LLM credentials to the browser.

**Alternatives considered**:
- Browser-side LLM calls — blocked by CORS on most LLM servers; also leaks endpoint URLs to the client.

---

## Decision 4: Frontend form as modal vs. separate route

**Decision**: Inline modal on the game list page (no new route). The form opens over the game list, the user fills it in and submits, then the modal closes and the browser navigates to the new game board.

**Rationale**: The form is a one-shot flow from the game list. A separate route (`/create`) would require managing navigation back if creation fails, and adds complexity for no user benefit.

**Alternatives considered**:
- Separate `/create` route — reasonable but more navigation complexity.
- Drawer/side panel — similar to modal; modal is simpler to implement.

---

## Decision 5: Observer AI when debug is enabled and only heuristic players

**Decision**: Match CLI behaviour exactly: if debug is enabled but all players are heuristic and no observer endpoint is provided, the game starts without observer commentary (no error). A UI warning is shown before submission.

**Rationale**: The CLI prints a warning but continues. The UI should match this behaviour and not block game creation.

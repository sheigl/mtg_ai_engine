# Research: AI CLI Client for MTG Games

**Branch**: `008-ai-cli-client` | **Date**: 2026-03-21

## Decision 1: HTTP Client Library

**Decision**: Use `httpx` (synchronous mode)

**Rationale**: The existing test suite already uses `httpx` via `TestClient` from `starlette`. Using the same library for the CLI client keeps dependencies consistent. Synchronous mode is appropriate because the game loop is inherently sequential — one action per turn, no benefit to async here.

**Alternatives considered**:
- `requests` — simpler API but not already in the project; `httpx` is a strict superset
- `aiohttp` + `asyncio` — unnecessary complexity for a sequential game loop

---

## Decision 2: LLM Client Library

**Decision**: Use the `openai` Python package pointed at a custom `base_url`

**Rationale**: The `openai` package natively supports OpenAI-compatible endpoints via the `base_url` parameter on the `OpenAI` client constructor. This works with Ollama, LM Studio, llama.cpp server, vLLM, and any other OpenAI-compatible local server without any custom HTTP code.

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

**Alternatives considered**:
- Raw `httpx` calls to `/v1/chat/completions` — eliminates dependency but re-implements retry, timeout, streaming, and error handling that the `openai` SDK provides for free
- `litellm` — too heavy; overkill for direct local LLM calls

---

## Decision 3: CLI Argument Parsing

**Decision**: Use `argparse` (Python stdlib)

**Rationale**: No external dependencies needed. `argparse` handles repeating flags (`action="append"`), `--help` generation, and type validation. The argument surface is small enough that click/typer would add complexity without benefit.

**Alternatives considered**:
- `click` — more ergonomic for large CLIs, unnecessary here
- `typer` — adds a runtime dependency; not worth it for ~5 flags

---

## Decision 4: AI Response Format

**Decision**: Instruct the LLM to respond in JSON with fields `action_index` and `reasoning`

**Rationale**: Structured JSON output is the most reliable way to extract a chosen action from an LLM without complex text parsing. The prompt presents legal actions as a numbered list and asks the AI to reply with `{"action_index": N, "reasoning": "..."}`. The client validates the index is in range; if parsing fails it retries once with a corrective prompt, then falls back to action 0 (typically "pass priority").

```json
{"action_index": 2, "reasoning": "I cast Lightning Bolt targeting the opponent to bring them to 17 life."}
```

**Alternatives considered**:
- Free-text with action name — brittle; names can be ambiguous or abbreviated by the LLM
- OpenAI function calling / structured outputs — not universally supported by local LLMs
- Always passing (no LLM) — useful only for smoke tests, not useful as the primary mode

---

## Decision 5: Game Loop Driver

**Decision**: The CLI polls `GET /game/{game_id}/legal-actions` to determine whose turn it is and what actions are available, then submits via the appropriate action endpoint.

**Rationale**: The `legal-actions` endpoint returns `priority_player`, `phase`, `step`, and a full list of legal actions with descriptions. This gives the AI all the information it needs to make a decision. The client does not need to interpret game rules — it just feeds the engine's output to the LLM and maps the response back to an API call.

**Engine action endpoint mapping**:

| Action type from legal-actions | API endpoint |
|-------------------------------|--------------|
| `pass` | `POST /game/{id}/pass` |
| `play_land` | `POST /game/{id}/play-land` |
| `cast` | `POST /game/{id}/cast` |
| `activate` | `POST /game/{id}/activate` |
| `declare_attackers` | `POST /game/{id}/declare-attackers` |
| `declare_blockers` | `POST /game/{id}/declare-blockers` |
| `order_blockers` | `POST /game/{id}/order-blockers` |
| `assign_combat_damage` | `POST /game/{id}/assign-combat-damage` |
| `put_trigger` | `POST /game/{id}/put-trigger` |

**Alternatives considered**:
- AI constructs action payload from scratch — requires the AI to know the API schema; fragile
- Polling `GET /game/{game_id}` for state changes — gives state but not legal actions; more work to compute legality client-side

---

## Decision 6: Default Deck

**Decision**: Provide a minimal built-in test deck (20 basic Plains + 20 White Weenie creatures) as the default, with optional `--deck1` / `--deck2` CLI arguments accepting comma-separated card names.

**Rationale**: The engine requires `deck1` and `deck2` arrays at game creation. A default deck means users can run the CLI with no deck configuration for quick tests. Custom decks are supported for meaningful AI evaluation.

**Built-in test deck** (40 cards):
- 20× Plains
- 4× Llanowar Elves
- 4× Grizzly Bears
- 4× Giant Growth
- 4× Lightning Bolt
- 4× Counterspell

**Alternatives considered**:
- Require deck arguments — creates friction for quick tests; no good for demos
- Load from a `.txt` file — a future extension; out of scope for this feature

---

## Decision 7: Error Handling Strategy

**Decision**: On LLM endpoint failure, retry once after 2 seconds, then submit action index 0 (pass priority) and log a warning. On engine API failure, log the error and exit with code 1.

**Rationale**:
- LLM failures are transient (timeout, rate limit) and a single retry covers most cases
- Falling back to "pass" keeps the game moving without deadlocking on a stuck AI
- Engine failures are non-recoverable (game state is inconsistent) and should terminate the process cleanly

**Alternatives considered**:
- Infinite retry loop on LLM — risks infinite hang; explicit retry cap is safer
- Ignore engine errors and continue — risks submitting illegal actions and corrupting game state

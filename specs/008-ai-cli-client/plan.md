# Implementation Plan: AI CLI Client for MTG Games

**Branch**: `008-ai-cli-client` | **Date**: 2026-03-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-ai-cli-client/spec.md`

## Summary

Build a standalone Python CLI that connects two or more OpenAI-compatible LLM players to the MTG engine REST API and runs a fully automated game. Each player is configured independently via `--player name,url,model` flags. The game loop fetches legal actions, prompts the appropriate LLM, extracts its chosen action and reasoning, submits the action to the engine, and logs everything to the console until the game ends.

## Technical Context

**Language/Version**: Python 3.11 (matches existing codebase)
**Primary Dependencies**: `httpx` (HTTP to engine API), `openai` (OpenAI-compatible LLM client), `argparse` (stdlib CLI parsing)
**Storage**: None — stateless client; game state lives in the engine
**Testing**: pytest (matches existing test suite)
**Target Platform**: Linux/macOS terminal
**Project Type**: CLI tool
**Performance Goals**: No strict latency requirement; throughput is bottlenecked by LLM response time (~1–30s per turn depending on model)
**Constraints**: Sequential game loop (one action at a time); must not deadlock if LLM endpoint is unreachable
**Scale/Scope**: Single game per invocation; 2–4 players supported

## Constitution Check

No `constitution.md` exists for this project. Applying minimal sensible defaults:

- **Simplicity gate**: PASS — single CLI module, no new server, no new DB, no new framework
- **Scope gate**: PASS — fully additive; does not modify the engine API
- **Dependency gate**: PASS — `httpx` and `openai` are lightweight, widely used packages appropriate for the task

## Project Structure

### Documentation (this feature)

```text
specs/008-ai-cli-client/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── cli-arguments.md ← CLI argument contract
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
ai_client/
├── __init__.py
├── __main__.py      # Entry point: parse args, build players, run game loop
├── client.py        # EngineClient — HTTP wrapper around the MTG engine API
├── ai_player.py     # AIPlayer — queries one OpenAI-compatible LLM endpoint
├── game_loop.py     # GameLoop — orchestrates turns, logging, termination
└── prompts.py       # Prompt templates: game state → LLM message

tests/
└── cli/
    ├── __init__.py
    ├── test_engine_client.py   # Unit tests for EngineClient (mock httpx)
    ├── test_ai_player.py       # Unit tests for AIPlayer (mock openai)
    └── test_game_loop.py       # Integration test with stub engine & stub AI
```

**Structure Decision**: New top-level `ai_client/` package so the client can be run as `python -m ai_client` without coupling to the engine internals. Tests go in `tests/cli/` alongside existing test directories.

## Complexity Tracking

No constitution violations. No complexity justification required.

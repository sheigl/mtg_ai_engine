# Spec: MTG Rules Engine

## Purpose

A Python-based Magic: The Gathering rules engine that enforces the full
Comprehensive Rules, exposes a REST API, and allows AI agents to play
complete games against each other. The primary output is structured
training data for downstream MTG AI model training.

## Problem Statement

Training an MTG AI requires exposure to real game situations — legal
board states, correct priority sequences, valid action sets, and outcome
labels. Hand-crafted examples are slow and limited. This engine enables
AI self-play at scale, generating thousands of labeled game records
automatically without human involvement in each game.

## Context

- Standalone Python service, runs locally alongside Ollama
- AI agents (LLMs via Ollama or scripted bots) call the REST API to
  take actions; the engine enforces legality and advances game state
- Four types of training data are exported per game:
    1. Game state snapshots (board state → legal actions → chosen action)
    2. Play-by-play decision transcripts (full annotated game log)
    3. Rules Q&A pairs derived from actual rule triggers during play
    4. Win/loss outcome records for reinforcement learning
- Card data sourced from Scryfall API (or local cache); engine does not
  hard-code card text — it reads oracle text and interprets it via a
  card ability parser
- Integrates with existing MongoDB instance for training data storage

## Success Criteria

- Two AI agents can play a full game from opening hand to game over
  with zero unhandled exceptions on any legal card interaction
- All four training data types are exported for every completed game
- Full competitive rules coverage: layers (613), replacement effects,
  state-based actions, split-second, copy effects, and the stack
- REST API response time under 200ms per action on local hardware
- Engine correctly handles a suite of 50 known-tricky interactions
  (e.g. Humility + Opalescence, Leyline of Anticipation + split second,
  clone entering as a copy, damage prevention replacement effects)
- Training data output is valid JSON conforming to defined schemas

## Performance Considerations

- Benchmark deck load times for decks with 100+ cards (REQ-P01)
- Ensure API latency remains under 200ms for all core game actions (REQ-P02)
- Support 100+ concurrent game sessions without degradation (REQ-P03)

## Security Validation

- Validate all file uploads for malicious content (REQ-S01)
- Enforce strict content-type validation for uploaded deck files (REQ-S02)
- Implement rate-limiting for file upload endpoints (REQ-S03)

## User Interface & Experience

- Import workflow includes: file selection → format validation → preview → confirmation (REQ-U01)
- Clear error messages for invalid deck formats (REQ-U02)
- Progress indicators for large file uploads (REQ-U03)

## Error Code Alignment

- Map all error responses to specific requirement numbers in `requirements.md`:
  - 400: Invalid deck format → REQ-D01
  - 403: File upload rejected → REQ-S02
  - 500: Internal rule engine error → REQ-R01

## Test Coverage

- Integration tests for edge cases:
  - Invalid file formats (REQ-T01)
  - Large file uploads (>10MB) (REQ-T02)
  - Concurrent imports (REQ-T03)
  - Malformed JSON in deck files (REQ-T04)

## Out of Scope (v1)

- Multiplayer (more than 2 players)
- Commander-specific rules (commander tax, command zone, partner)
- Ante rules
- Subgames (Shahrazad)
- Silver-bordered / acorn cards
- Digital-only mechanics (perpetually, conjure, etc.)
- Draft or sealed deck simulation
- GUI or human-facing interface

## Architecture Overview

```
AI Agent (LLM / bot)
        |
        | HTTP REST
        v
 ┌─────────────────┐
 │   FastAPI App   │  ← game router, data export router
 └────────┬────────┘
          |
 ┌────────▼────────┐     ┌─────────────────┐
 │  GameEngine     │────▶│  RulesEngine    │  ← CR 613 layers,
 │  (state mgr)   │     │  (legality &    │     SBAs, stack,
 └────────┬────────┘     │   resolution)   │     replacement fx
          |              └─────────────────┘
 ┌────────▼────────┐     ┌─────────────────┐
 │  CardResolver   │────▶│  ScryfallClient │  ← oracle text,
 │  (ability parse)│     │  (card data)    │     type line, etc.
 └────────┬────────┘     └─────────────────┘
          |
 ┌────────▼────────┐
 │  DataExporter   │────▶ MongoDB (training data)
 └─────────────────┘
```

## Key Constraints

- Python 3.11+
- FastAPI for the REST layer
- Pydantic v2 for all game state models (enables clean JSON serialization)
- Must be runnable with `uvicorn` on localhost, no Docker required
- Card ability parsing must be data-driven (oracle text → effect objects),
  not a giant if/else tree of card names
- All game state must be fully serializable to JSON at any point
- Engine must be deterministic given a fixed random seed (for replay)

## Non-Goals

- The engine does not decide what action an AI should take — it only
  enforces legality, resolves actions, and reports state. Strategy is
  entirely the AI agent's responsibility.
- The engine does not train models — it generates data consumed by the
  existing training pipeline.

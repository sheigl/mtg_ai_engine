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

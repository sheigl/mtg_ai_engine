# MTG AI Engine

A Python REST API that enforces the full Magic: The Gathering Comprehensive Rules, enabling AI agents to play complete games against each other and generate structured training data for downstream MTG model fine-tuning.

## Overview

The engine acts as a rules referee — it enforces legality, resolves actions, and reports state. Strategic decisions are entirely the responsibility of the calling AI agent.

Each completed game produces four types of training data:
1. **Snapshots** — board state + legal actions + chosen action at every priority grant
2. **Transcript** — play-by-play annotated game log
3. **Rules Q&A pairs** — derived from actual rule triggers during play, with CR citations
4. **Outcome** — win/loss record for reinforcement learning

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- MongoDB (optional — training data export; engine runs without it)
- Internet access for first-time card data fetches (Scryfall API)

## Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd mtg_ai_engine

# Install dependencies
uv pip install fastapi uvicorn pydantic httpx pymongo pytest pytest-asyncio

# Download the MTG Comprehensive Rules (required for rules references)
curl -L "https://media.wizards.com/2025/downloads/MagicCompRules_20250404.txt" -o cr.txt

# Start the server
uvicorn mtg_engine.api.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Running Tests

```bash
PYTHONPATH=. uv run python -m pytest tests/ -v
```

All 193 tests should pass.

## API Usage

### 1. Create a game

```bash
curl -X POST http://localhost:8000/game \
  -H "Content-Type: application/json" \
  -d '{
    "player1_name": "Alice",
    "player2_name": "Bob",
    "player1_deck": ["Lightning Bolt", "Lightning Bolt", ...],
    "player2_deck": ["Counterspell", "Island", ...],
    "seed": 42
  }'
```

Response includes the initial `GameState` with `game_id`.

### 2. Get legal actions

```bash
curl http://localhost:8000/game/{game_id}/legal-actions
```

Returns all legal actions for the current priority holder: pass, play-land, cast spells, activate abilities, declare attackers, or put triggers on the stack.

### 3. Take an action

**Pass priority:**
```bash
curl -X POST http://localhost:8000/game/{game_id}/pass \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Cast a spell:**
```bash
curl -X POST http://localhost:8000/game/{game_id}/cast \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": "<card-uuid>",
    "targets": ["<target-permanent-id>"],
    "mana_payment": {"R": 1}
  }'
```

**Play a land:**
```bash
curl -X POST http://localhost:8000/game/{game_id}/play-land \
  -H "Content-Type: application/json" \
  -d '{"card_id": "<card-uuid>"}'
```

**Declare attackers:**
```bash
curl -X POST http://localhost:8000/game/{game_id}/declare-attackers \
  -H "Content-Type: application/json" \
  -d '{
    "attack_declarations": [
      {"attacker_id": "<creature-id>", "defending_id": "<player-name>"}
    ]
  }'
```

**Declare blockers:**
```bash
curl -X POST http://localhost:8000/game/{game_id}/declare-blockers \
  -H "Content-Type: application/json" \
  -d '{
    "block_declarations": [
      {"blocker_id": "<creature-id>", "attacker_id": "<attacker-id>"}
    ]
  }'
```

**Assign combat damage:**
```bash
curl -X POST http://localhost:8000/game/{game_id}/assign-combat-damage \
  -H "Content-Type: application/json" \
  -d '{
    "assignments": [
      {"source_id": "<attacker-id>", "target_id": "<player-or-creature>", "damage": 3}
    ]
  }'
```

**Make a choice** (e.g. replacement effect ordering):
```bash
curl -X POST http://localhost:8000/game/{game_id}/choice \
  -H "Content-Type: application/json" \
  -d '{"choice_id": "<choice-id>", "selection": "<option>"}'
```

### 4. Dry run

Add `"dry_run": true` to any action request body to validate and preview the resulting state without committing it.

```bash
curl -X POST http://localhost:8000/game/{game_id}/cast \
  -H "Content-Type: application/json" \
  -d '{"card_id": "<id>", "mana_payment": {"R": 1}, "dry_run": true}'
```

### 5. Export training data

After a game ends, retrieve training data:

```bash
# Game state snapshots (JSONL)
curl http://localhost:8000/export/{game_id}/snapshots

# Play-by-play transcript
curl http://localhost:8000/export/{game_id}/transcript

# Rules Q&A pairs
curl http://localhost:8000/export/{game_id}/rules-qa

# Win/loss outcome
curl http://localhost:8000/export/{game_id}/outcome
```

### 6. Delete a game

Deleting a completed game triggers a MongoDB write of all four export types:

```bash
curl -X DELETE http://localhost:8000/game/{game_id}
```

## AI Agent Integration Loop

The canonical agent loop:

```python
import httpx

BASE = "http://localhost:8000"

# Create game
r = httpx.post(f"{BASE}/game", json={
    "player1_name": "agent_a",
    "player2_name": "agent_b",
    "player1_deck": [...],  # 60+ card names
    "player2_deck": [...],
    "seed": 1234
})
game_id = r.json()["data"]["game_id"]

while True:
    # Get current state
    state = httpx.get(f"{BASE}/game/{game_id}").json()["data"]
    if state["players"][0]["has_lost"] or state["players"][1]["has_lost"]:
        break

    # Get legal actions
    actions = httpx.get(f"{BASE}/game/{game_id}/legal-actions").json()["data"]["actions"]

    # Pick an action (your AI logic here)
    action = pick_action(state, actions)

    # Execute the action
    httpx.post(f"{BASE}/game/{game_id}/{action['type']}", json=action["params"])

# Export training data
snapshots = httpx.get(f"{BASE}/export/{game_id}/snapshots").text
transcript = httpx.get(f"{BASE}/export/{game_id}/transcript").json()
rules_qa   = httpx.get(f"{BASE}/export/{game_id}/rules-qa").json()
outcome    = httpx.get(f"{BASE}/export/{game_id}/outcome").json()

# Clean up (writes to MongoDB if configured)
httpx.delete(f"{BASE}/game/{game_id}")
```

## Project Structure

The repository root is `mtg_ai_engine/`. The Python package lives inside it at `mtg_engine/` and is divided into four sub-packages plus an API layer.

```
mtg_ai_engine/                        ← repository root
│
├── mtg_engine/                        ← importable Python package
│   │
│   ├── models/                        ← Pydantic v2 data models (no logic)
│   │   ├── game.py                    ← Core domain types: Card, Permanent,
│   │   │                                PlayerState, GameState, StackObject,
│   │   │                                ManaPool, CombatState, PendingTrigger
│   │   └── actions.py                 ← API request/response types: CastRequest,
│   │                                     DeclareAttackersRequest, LegalAction, …
│   │
│   ├── card_data/                     ← Card data retrieval and parsing
│   │   ├── scryfall.py                ← ScryfallClient: fetches card JSON from the
│   │   │                                Scryfall API and caches results in SQLite
│   │   │                                (mtg_engine/card_data/cache.db). Rate-limited
│   │   │                                to 100ms between requests.
│   │   ├── ability_parser.py          ← Parses oracle text into structured ability
│   │   │                                objects: TriggeredAbility, ActivatedAbility,
│   │   │                                KeywordAbility, SpellEffect. Used at deck-load
│   │   │                                time so the engine never re-parses mid-game.
│   │   └── deck_loader.py             ← Accepts a list of card names, fetches each
│   │                                     from Scryfall, validates 60-card minimum,
│   │                                     assigns a fresh UUID per copy.
│   │
│   ├── engine/                        ← Rules enforcement — one file per concern
│   │   ├── zones.py                   ← Zone management (CR 400-407): move_card_to_zone,
│   │   │                                move_permanent_to_zone, draw_card, zone-change
│   │   │                                event emitter. Tokens cease to exist on leaving
│   │   │                                the battlefield (CR 704.5d).
│   │   ├── turn_manager.py            ← Turn structure (CR 500-514): 13-step TURN_SEQUENCE,
│   │   │                                begin_step / advance_step / pass_priority. Handles
│   │   │                                untap, draw, and cleanup step side effects.
│   │   ├── mana.py                    ← Mana pool arithmetic: parse_mana_cost,
│   │   │                                can_pay_cost, pay_cost, add_mana. Supports
│   │   │                                generic (X/N), colored, and colorless symbols.
│   │   ├── stack.py                   ← Spell casting and stack resolution (CR 601-608):
│   │   │                                timing enforcement, split-second check, target
│   │   │                                validation, mana payment, resolve_top. Permanents
│   │   │                                enter the battlefield; instants/sorceries resolve
│   │   │                                their effect then go to the graveyard.
│   │   ├── sba.py                     ← State-based actions (CR 704): loops check-and-apply
│   │   │                                until no SBAs fire. Covers 704.5a–q: lethal damage,
│   │   │                                zero toughness, legend rule, planeswalker loyalty,
│   │   │                                aura/equipment validity, token removal, poison, etc.
│   │   ├── triggers.py                ← Triggered ability detection (CR 603): registers a
│   │   │                                zone-change listener, matches events against ability
│   │   │                                conditions, checks phase triggers (upkeep/end/combat).
│   │   │                                Simultaneous triggers ordered by APNAP (CR 603.3b).
│   │   ├── layers.py                  ← Continuous effect layer system (CR 613): seven
│   │   │                                layers (copy → control → type → color → ability →
│   │   │                                P/T set → P/T modify) applied in timestamp order
│   │   │                                with dependency override. CDA (characteristic-
│   │   │                                defining ability) P/T handled in layer 7a.
│   │   ├── replacement.py             ← Replacement and prevention effects (CR 614-616):
│   │   │                                process_event intercepts GameEvents and applies
│   │   │                                "instead" modifications. Handles infect (-1/-1
│   │   │                                counters), shield counters, regeneration shields,
│   │   │                                and damage prevention/reduction.
│   │   └── combat.py                  ← Full combat phase (CR 508-511): declare_attackers
│   │                                     (summoning sickness, vigilance, defender checks),
│   │                                     declare_blockers (flying/reach enforcement),
│   │                                     order_blockers, assign_combat_damage with trample
│   │                                     overflow, deathtouch 1-damage lethal, and lifelink.
│   │
│   ├── export/                        ← Training data generation (one recorder per type)
│   │   ├── store.py                   ← GameExportStore: per-game-id dict holding all four
│   │   │                                recorders. get_export_store / delete_export_store
│   │   │                                provide global access without singleton coupling.
│   │   ├── snapshots.py               ← SnapshotRecorder: called at every priority grant.
│   │   │                                Captures compressed board state, legal action set,
│   │   │                                and — once an action is taken — the chosen action
│   │   │                                and who took it. Serializes to JSONL.
│   │   ├── transcript.py              ← TranscriptRecorder: event-driven log of every
│   │   │                                meaningful game event (phase changes, casts, resolves,
│   │   │                                SBAs, zone changes, damage, choices). Each entry has
│   │   │                                seq, event_type, description, turn, phase, step.
│   │   ├── rules_qa.py                ← RulesQARecorder: 24 Q&A template functions triggered
│   │   │                                by engine events (SBAs, damage, trample, layers,
│   │   │                                replacement effects). Each pair includes the question,
│   │   │                                answer, and the CR citation it demonstrates.
│   │   └── outcome.py                 ← build_outcome: assembles the final GameOutcome record
│   │                                     (winner, loser, turn count, snapshot count, how the
│   │                                     game ended) after a player has_lost.
│   │
│   └── api/                           ← FastAPI application
│       ├── main.py                    ← App factory: creates FastAPI instance, mounts both
│       │                                routers, exposes GET /health.
│       ├── game_manager.py            ← GameManager singleton: in-memory dict of game_id →
│       │                                GameState. Provides create_game (seeded RNG shuffle,
│       │                                7-card opening hands), get, update, delete, and
│       │                                snapshot (deep copy for dry_run support).
│       └── routers/
│           ├── game.py                ← 16 game endpoints: POST /game, GET/DELETE /game/{id},
│           │                            pass, play-land, cast, activate, put-trigger,
│           │                            special-action, declare-attackers, declare-blockers,
│           │                            order-blockers, assign-combat-damage, legal-actions,
│           │                            pending-triggers, stack, choice. All success responses
│           │                            wrapped in {"data": ...}; errors return HTTP 422 with
│           │                            {"error": ..., "error_code": ...}.
│           └── export.py              ← 4 export endpoints: GET /export/{id}/snapshots (JSONL),
│                                         /transcript (JSON array), /rules-qa (JSON array),
│                                         /outcome (single object).
│
├── tests/
│   ├── conftest.py                    ← Adds project root to sys.path
│   ├── rules/                         ← Pure rules engine unit tests (no HTTP)
│   │   ├── test_mana.py               ← Mana parsing and cost payment
│   │   ├── test_zones.py              ← Zone transitions and token rules
│   │   ├── test_stack.py              ← Casting timing, mana, stack resolution
│   │   ├── test_sba.py                ← State-based action scenarios
│   │   ├── test_combat.py             ← Attacker/blocker declaration, damage assignment
│   │   ├── test_layers.py             ← Layer ordering and Humility interactions
│   │   ├── test_replacement.py        ← Replacement/prevention effect scenarios
│   │   ├── test_ability_parser.py     ← Oracle text parsing
│   │   ├── test_actions.py            ← Action model validation
│   │   └── test_rules_interactions.py ← 50 complex multi-system interaction tests
│   └── api/                           ← API integration tests
│       ├── test_api.py                ← Core endpoint contract tests
│       ├── test_scryfall.py           ← Scryfall cache and fetch tests
│       ├── test_export.py             ← Export endpoint tests
│       ├── test_bot_games.py          ← Scripted bot games (TASK-25) and concurrent
│       │                                isolation with 10 simultaneous games (TASK-27)
│       └── test_performance.py        ← p99 latency benchmarks: empty board, 20 permanents,
│                                         stack-heavy scenarios — all well under 200ms
│
├── spec.md                            ← Architecture, goals, and out-of-scope rules
├── requirements.md                    ← Numbered requirements (REQ-XXX)
├── tasks.md                           ← Phase-by-phase implementation task list
└── cr.txt                             ← MTG Comprehensive Rules (downloaded separately)
```

### Data flow

```
POST /game/{id}/cast
        │
        ▼
  game_manager.py          ← snapshot for dry_run isolation
        │
        ▼
  engine/stack.py           ← validate timing, targets, cost; move card to stack
        │
        ├─▶ engine/mana.py  ← deduct mana payment from pool
        │
  (after all players pass)
        │
        ▼
  engine/stack.py           ← resolve_top: permanent → zones.py; spell → effect
        │
        ├─▶ engine/sba.py   ← loop SBAs until none fire
        ├─▶ engine/triggers.py ← queue any triggered abilities
        └─▶ export/          ← record snapshot, transcript entry, rules Q&A
```

### Key design decisions

- **One file per concern in `engine/`** — each rules section (stack, SBAs, layers, combat, …) is isolated so changes to one cannot silently break another.
- **Seeded `random.Random`** — all shuffle and randomness goes through a seeded instance created at game creation, never the global `random` module. Games are fully reproducible from the seed.
- **deep copy for dry runs** — `game_manager.snapshot()` returns `copy.deepcopy(state)`. Dry-run actions operate on the copy; the live state is never touched.
- **Export recorders are event-driven** — the engine calls `recorder.record_*()` methods inline; there is no post-hoc log parsing.
- **MongoDB is best-effort** — the `_write_to_mongodb()` call in the DELETE handler is wrapped in `try/except` so the engine is fully usable without a running MongoDB instance.

## Rules Coverage

The engine implements the following MTG Comprehensive Rules sections:

| Area | CR Section | Notes |
|------|-----------|-------|
| Zones | 400-407 | All 7 zones; tokens cease to exist outside battlefield |
| Turn structure | 500-514 | All phases and steps in correct sequence |
| State-based actions | 704 | Full CR 704.5a–q coverage, looping until none apply |
| Casting spells | 601-608 | Timing, targets, split-second, copy effects |
| Triggered abilities | 603 | APNAP ordering for simultaneous triggers |
| Layer system | 613 | All 7 layers with timestamp and dependency ordering |
| Replacement effects | 614-616 | Shield counters, regeneration, "instead" effects |
| Combat | 508-511 | First/double strike, trample, deathtouch, lifelink, infect |
| Keywords | 702 | Flash, haste, vigilance, flying, reach, defender, and more |

## Error Responses

Illegal actions return HTTP 422:

```json
{
  "detail": {
    "error": "Cannot cast sorcery during opponent's turn",
    "error_code": "INVALID_TIMING"
  }
}
```

Unknown game IDs return HTTP 404.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| SQLite cache | `mtg_engine/card_data/cache.db` | Card data cache path |
| MongoDB URI | `mongodb://localhost:27017` | Training data export target |
| MongoDB DB | `mtg_training` | Database name |
| MongoDB collection | `games` | Collection name |

MongoDB writes are best-effort — if unavailable, the DELETE endpoint still succeeds and export endpoints still return data.

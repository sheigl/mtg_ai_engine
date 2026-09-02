# Architecture: MTG AI Engine

## High-Level Overview

The MTG AI Engine is a Python-based Magic: The Gathering rules engine that enforces the full Comprehensive Rules (CR), exposes a REST API, and enables AI agents to play complete games against each other. It generates structured training data for downstream MTG model fine-tuning.

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  AI Agent A  │◄────│                  │◄────│  AI Agent B      │
│  (LLM/Bot)   │────►│   FastAPI Server │────►│  (LLM/Bot)       │
└──────────────┘     └────────┬─────────┘     └──────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌───────────┐  ┌───────────┐  ┌──────────────┐
        │  Engine    │  │   AI      │  │   Export     │
        │  (rules)   │  │  (deck)   │  │  (training)  │
        └───────────┘  └───────────┘  └──────────────┘
              │               │               │
              ▼               ▼               ▼
         GameState      Card Pool       Snapshots,
    (in-memory dict)   + Format Rules  Transcript, Q&A
```

## Core Components

### 1. API Layer (`mtg_engine/api/`)

FastAPI application providing REST endpoints for game lifecycle and state management.

- **`main.py`** — App factory; mounts all routers, exposes `GET /health`
- **`game_manager.py`** — In-memory singleton storing `game_id → GameState`; provides create/get/update/delete/snapshot operations
- **`routers/game.py`** — 16 game endpoints: pass, cast, play-land, declare attackers/blockers, assign damage, legal actions, choices, etc.
- **`routers/export.py`** — 4 export endpoints for training data (snapshots, transcript, rules Q&A, outcome)
- **`routers/card_search.py`** — `GET /cards/search`: queries local SQLite Scryfall cache with filtering/pagination/sorting
- **`routers/deck_build_ai.py`** — `POST /ai/deck/build`: stateless deck construction from card pool
- **`routers/replay.py`** — 4 replay endpoints at `/replay/{game_id}/*`: `GET /info`, `GET /events` (paginated), `POST /step`, `GET /timeline`; reconstructs board state from snapshots + transcript
- **`routers/spectate.py`** — WebSocket endpoint at `WS /ws/game/{game_id}`: real-time spectator streaming via pub/sub listener pattern; sends initial_state on connect, streams transcript events live, sends game_end notification with winner/loser info; read-only (non-pong messages ignored); rejects non-existent/completed games (close code 4004)
- **`routers/draft_ai.py`** — Draft/sealed simulation endpoints: `POST /ai/draft/start`, `GET /ai/draft/{id}/state`, `POST /ai/draft/{id}/pick`, `GET /ai/draft/{id}/results`, `POST /ai/sealed/start`; snake-draft pick order with bot auto-pick; LRU session eviction (MAX_DRAFT_SESSIONS=100); delegates post-draft deck construction to APP-02 `build_deck()`
- **`routers/player_stats.py`** — Player stats & ELO (APP-06): `POST /stats/player/{name}` (idempotent create/update), `GET /stats/player/{name}` (full stats with computed total_games/win_rate), `GET /leaderboard?format=&limit=10`, `GET /stats/player/{name}/matchups`; async game completion hook `update_stats_for_game_completion()` with atomic MongoDB `$inc` for existing players and `$set` upsert for new players; per-player try/except isolation; returns HTTP 503 when MongoDB unconfigured

### 2. Engine Layer (`mtg_engine/engine/`)

Rules enforcement — one file per concern, each returning new GameState via `model_copy(update={...})`.

| Module | CR Section | Responsibility |
|--------|-----------|----------------|
| `zones.py` | 400-407 | Zone management, zone-change events, token lifecycle (CR 704.5d) |
| `turn_manager.py` | 500-514 | Turn structure: 13-step TURN_SEQUENCE, phase/step advancement |
| `mana.py` | — | Mana pool arithmetic: parse costs, payment validation, colored/generic/colorless |
| `stack.py` | 601-608 | Spell casting, timing enforcement, target validation, resolve_top |
| `sba.py` | 704 | State-based actions loop (704.5a–q): lethal damage, zero toughness, legend rule, etc. |
| `triggers.py` | 603 | Triggered ability detection (15 `check_*_triggers()` functions wired into event paths), zone-change listener, APNAP ordering; per-token firing (CR 110.6) at all token-creation sites |
| `layers.py` | 613 | Continuous effect layer system (7 layers with timestamp/dependency ordering) |
| `replacement.py` | 614-616 | Replacement/prevention effects: shield counters, regeneration, "instead" effects |
| `combat/core.py` | 508-511 | Full combat phase: attackers, blockers (flying/reach), trample, deathtouch, lifelink |
| `stats.py` | — | Player statistics & ELO rating: `calculate_new_elo()` (standard formula, K=32), `update_player_stats()` (pure transform via model_copy with deep copy of nested dicts) |

### 2b. Keyword Ability Modules (`mtg_engine/ability/keywords/`)

Keyword abilities are implemented as dedicated modules under `mtg_engine/ability/keywords/`, organized by keyword type. Each module follows a consistent pattern:

- **Class-based API**: A keyword class (e.g., `EvokeKeyword`, `MorphKeyword`, `SuspendKeyword`) with instance methods for the keyword's core operations
- **Module-level convenience functions**: Standalone functions that instantiate the class and delegate, enabling lazy imports from engine wrappers
- **Pure transforms**: All `apply()` and action methods return new GameState via `model_copy(update={...})` — never mutate directly

Engine files (`mtg_engine/engine/evoke.py`, `engine/morph.py`, `engine/suspend.py`) act as thin wrappers that import from keyword modules lazily, keeping the engine layer decoupled from specific keyword implementations. This pattern was established during Sprint 7 to consolidate all keyword logic in one location and eliminate duplicated inline code in engine files like `turn_manager.py`.

**Implemented keywords by category:**
- **Cost keywords**: Kicker (KW-16), Flashback (KW-17), Escape, Delve — modify casting costs; queue pending choices for human players, auto-resolve for AI. Fortify (CR 702.54a) — an activated ability of Fortification cards that attaches the Fortification to target land you control (the land-analogue of Equip, CR 301.7); sorcery-speed only
- **Action keywords**: Evoke (sacrifice at end of first priority), Morph (turn face-up with mana payment), Suspend (time counter management) — full lifecycle methods on keyword classes
- **Triggered/Replacement keywords**: Afterlife, Undying, Persist, Cascade, Storm, Madness, Dredge, Ninjutsu, Dash — fire at specific game moments via stack resolution. Bloodthirst (CR 702.22) — an ETB triggered ability that adds N +1/+1 counters to a creature entering the battlefield if an opponent was dealt damage this turn (tracked via `GameState.damage_dealt_this_turn`, reset each turn; both combat and non-combat damage count per CR 702.22b)
- **Passive keywords**: Hexproof/Shroud (KW-29/30), Menace (KW-31), Reach (KW-28) — query helpers returning boolean; called from targeting validation and blocker assignment

### 3. AI Layer (`mtg_engine/ai/`)

Stateless deck construction and draft simulation — does NOT interact with GameState or game zones.

- **`deck_builder.py`** — Filter → Score → Select → Validate pipeline:
  - **Filter**: removes banned cards, enforces legality windows, singleton rules (CR 905.2 basic land exemption), restricted limits (Vintage), commander color identity filtering
  - **Score**: `estimate_card_quality()` baseline × strategy_multiplier × cmc_curve_bonus
  - **Select**: greedy selection with deterministic tie-breaking via seed, ~24% land balancing, sideboard construction
  - **Validate**: FMT-01 `validate_deck()` integration
- **`draft.py`** — Draft/sealed simulation engine: pack generation from Scryfall SQLite cache with rarity-weighted distribution; snake-draft pick order (odd rounds pass left, even rounds pass right); bot auto-pick using `estimate_card_quality()` scoring with strategy-aware weighting and color synergy; sealed pool mode (one 15-card pack per player) with automatic deck construction via APP-02 `build_deck()`; LRU session eviction (`MAX_DRAFT_SESSIONS=100`); in-memory `_draft_sessions` dict (non-thread-safe, Redis recommended for production)

### 4. Card Data Layer (`mtg_engine/card_data/`)

Card retrieval and ability parsing from Scryfall API.

- **`scryfall.py`** — ScryfallClient: fetches card JSON, caches in SQLite (cache.db), rate-limited to 100ms between requests
- **`ability_parser.py`** — Parses oracle text into TriggeredAbility, ActivatedAbility, KeywordAbility, SpellEffect objects
- **`deck_loader.py`** — Accepts card names, fetches from Scryfall, validates 60-card minimum, assigns UUID per copy

### 5. Export & Replay Layer (`mtg_engine/export/`)

Training data generation and game replay — event-driven recorders called inline by the engine, plus stateless replay reconstruction from stored snapshots/transcript.

| Component | Purpose | Output Format | Triggered By |
|-----------|---------|---------------|--------------|
| `snapshots.py` | Board state + legal actions at priority grants | JSONL | Every priority grant (includes chosen action) |
| `transcript.py` | All meaningful game events + pub/sub listener system for live streaming (APP-04) | JSON array | Phase changes, casts, resolves, SBAs, zone changes; listeners notified on each entry via `register_listener()`/`unregister_listener()` |
| `rules_qa.py` | Engine events matching 24 Q&A templates with CR citations | JSON array | Engine events matching Q&A patterns |
| `outcome.py` | Game result on player loss (winner, loser, turn count, end reason) | Single object | Player has_lost |
| `replay_engine.py` | Stateless replay: two-tier board state reconstruction from snapshot anchors + incremental event replay; timeline generation; pagination helpers | N/A (reads snapshots/transcript) | N/A (read-only consumer) |

### 6. Models (`mtg_engine/models/`)

Pydantic v2 data models — no logic, pure data containers.

- **`game.py`** — GameState, Card, Permanent, PlayerState, StackObject, ManaPool, CombatState, PendingTrigger
- **`stats.py`** — PlayerStats, FormatRecord, MatchupRecord, StatsResponse, LeaderboardEntry, MatchupResult (APP-06)
- **`actions.py`** — API request/response types: CastRequest, DeclareAttackersRequest, LegalAction, etc.

## Key Design Decisions

### Stateless vs Stateful Operations

| Operation | Type | Interacts with GameState? |
|-----------|------|--------------------------|
| Game actions (cast, pass, combat) | Stateful | Yes — modifies GameState via model_copy |
| Card search (`GET /cards/search`) | Stateless | No — queries SQLite Scryfall cache only |
| Deck building (`POST /ai/deck/build`) | Stateless | No — takes card pool, returns deck list |
| Format validation (`validate_deck()`) | Stateless | No — takes card lists, returns violations |
| Game replay (`GET/POST /replay/{game_id}/*`) | Stateless | No — reads from export store snapshots/transcript only |
| Spectate WebSocket (`WS /ws/game/{game_id}`) | Stateful (connection) | Indirectly — subscribes to TranscriptRecorder listeners; no GameState mutation |
| Draft/Sealed Simulation (`POST /ai/draft/*`, `POST /ai/sealed/start`) | Stateless (session) | No — uses in-memory `_draft_sessions` dict; delegates deck construction to APP-02 `build_deck()` |
| Player Stats & ELO (`GET/POST /stats/player/{name}`, `GET /leaderboard`) | Stateful (MongoDB) | No — reads/writes MongoDB `player_stats` collection; game completion hook auto-updates on `DELETE /game/{id}` |

### Pure Transform Pattern

All engine functions follow a pure transform pattern: they accept GameState as input and return a new GameState via `model_copy(update={...})`. This enables:
- **Dry-run support**: actions tested on deep copies without affecting live state
- **Reproducibility**: seeded random.Random ensures identical games from same seed
- **Testability**: each function independently testable with minimal setup

### Seeded Randomness

All shuffle and randomness uses a seeded `random.Random` instance created at game creation, never the global `random` module. Games are fully reproducible from the seed value.

### MongoDB Best-Effort Storage

MongoDB writes (via motor async driver) are wrapped in try/except so the engine functions without a running database. Training data is always available via REST export endpoints regardless of MongoDB status.

## Data Flow: Cast Spell Example

```
POST /game/{id}/cast
        │
        ▼
  game_manager.py          ← snapshot for dry_run isolation (deep copy)
        │
        ▼
  engine/stack.py           ← validate timing, targets, cost; move card to stack
        │
        ├─▶ engine/mana.py  ← deduct mana payment from pool
        │
  (after all players pass priority)
        │
        ▼
  engine/stack.py           ← resolve_top: permanent → zones.py; spell → effect
        │
        ├─▶ engine/sba.py   ← loop SBAs until none fire
        ├─▶ engine/triggers.py ← queue any triggered abilities (APNAP order)
        └─▶ export/          ← record snapshot, transcript entry, rules Q&A
```

## WebSocket Spectator Architecture (APP-04)

The spectate endpoint uses a pub/sub listener pattern layered on top of the existing TranscriptRecorder:

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Spectator   │◄────│                  │◄────│  Engine (game.py) │
│  WS Client   │────►│  spectate.py     │     │                   │
└──────────────┘     └────────┬─────────┘     └────────┬──────────┘
                              │                         │
                     register_listener()        transcript.record_cast(...)
                              │                         │
                              ▼                         │
                    ┌───────────────────┐               │
                    │ TranscriptRecorder│◄──────────────┘
                    │  _notify_listeners│
                    └───────────────────┘
```

**Flow:**
1. Spectator connects via `WS /ws/game/{game_id}`; endpoint validates game exists and is active (rejects with code 4004 otherwise)
2. Per-connection `asyncio.Queue(maxsize=256)` created, listener callback registered on TranscriptRecorder
3. Full GameState sent as `initial_state` message on connect
4. Every transcript event flows through `_notify_listeners()` → queue → WebSocket send
5. Game-end detected via periodic idle checks (1s timeout) and post-event checks; sends `game_end` notification with winner/loser/reason
6. On disconnect, listener unregistered and connection removed from registry by identity

**Key design decisions:**
- **No heartbeat task**: competing `ws.receive_json()` calls caused deadlocks in TestClient scenarios; replaced with `queue.get(timeout=1.0)` idle checks that also detect game-end during quiet periods
- **Queue overflow protection**: events silently dropped when queue is full (256 max) to prevent crashing the engine for slow clients
- **Identity-based cleanup**: connections tracked by `(ws, queue, listener)` tuples; removal uses `queue` identity comparison to avoid removing wrong entries

## Format Support

Eight MTG formats supported via `mtg_engine/engine/formats/`:

| Format | Deck Size | Key Rules |
|--------|----------|-----------|
| Standard | 60 ± sideboard 15 | Legality window (recent sets), banned list |
| Pioneer | 60 ± sideboard 15 | Legality window from Return to Ravnica forward |
| Modern | 60 ± sideboard 15 | Legality window from Eighth Edition forward |
| Legacy | 60 ± sideboard 15 | Banned list only (no restricted) |
| Vintage | 60 ± sideboard 15 | Banned + restricted lists (max 1 copy for restricted) |
| Commander | 100 singleton | Legendary creature commander, color identity filtering, CR 903.8 tax, CR 903.9 zone replacement |
| Brawl | 60 singleton | 1 legendary creature commander, Standard banned list |
| Pauper | 60 ± sideboard 15 | Common-rarity cards only (CR 109.5) |

## Test Organization

```
tests/
├── rules/          ← Pure engine unit tests (no HTTP)
│   ├── test_mana.py, test_zones.py, test_stack.py, ...
│   └── test_rules_interactions.py  ← 50 complex multi-system interactions
├── api/            ← API integration tests (FastAPI TestClient)
│   ├── test_api.py, test_scryfall.py, test_export.py, test_replay.py, test_spectate_websocket.py, ...
├── engine/         ← Engine-specific integration tests
│   └── test_keywords_integration.py  ← Keyword ability integration
├── ai/             ← Deck Building AI and Draft Simulation tests
│   ├── test_deck_builder.py          ← 52 unit + 7 API tests
│   └── test_draft.py                 ← 37 engine tests (pack gen, pick order, bot scoring, sealed flow, LRU eviction)
└── formats/        ← Format validation tests
    └── test_commander_integration.py ← Commander rules integration
```

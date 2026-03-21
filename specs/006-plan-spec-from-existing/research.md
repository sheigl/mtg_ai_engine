# Research: MTG Rules Engine

**Generated**: 2026-03-20  
**Source**: `/specs/006-plan-spec-from-existing/spec.md`

---

## Technical Decisions

### 1. Game State Architecture

**Decision**: Use Pydantic v2 models for all game state objects with full JSON serialization

**Rationale**: 
- Pydantic v2 provides superior performance over v1 (2-3x faster validation)
- Automatic JSON serialization via `model_dump_json()` ensures training data is always serializable
- Type hints enable IDE support and static analysis
- Nested models cleanly represent MTG hierarchy (Game → Player → Zone → Card)

**Alternatives Considered**:
- Raw dicts: Rejected - no type safety, manual serialization
- dataclasses: Rejected - no built-in validation, no JSON serialization
- Pydantic v1: Rejected - deprecated, slower performance

**References**: 
- Spec: "Pydantic v2 for all game state models (enables clean JSON serialization)"
- QWEN: "Use Pydantic v2 models for all data that crosses a function boundary"

---

### 2. Engine Architecture Pattern

**Decision**: Separate GameEngine (state management) from RulesEngine (legality & resolution)

**Rationale**:
- Single Responsibility: GameEngine manages turn structure, zones, card movement; RulesEngine enforces CR 613 layers, SBAs, stack, replacement effects
- Testability: Rules logic can be tested independently of game flow
- Determinism: RulesEngine is pure function given game state, making replay deterministic with fixed seed
- Alignment with spec architecture diagram

**Alternatives Considered**:
- Monolithic engine: Rejected - too complex, harder to test rules in isolation
- Event sourcing: Rejected - overkill for 2-player local game, adds complexity

**References**:
- Spec: Architecture diagram showing GameEngine → RulesEngine separation

---

### 3. Card Data Strategy

**Decision**: Hybrid approach with Scryfall API + local SQLite cache

**Rationale**:
- Scryfall is the authoritative source for MTG oracle text and card data
- Local cache avoids rate limiting and enables offline development
- SQLite is stdlib, no external dependencies
- Card data is read-only; cache invalidated periodically or on-demand

**Alternatives Considered**:
- Pure API: Rejected - rate limiting, network failures break games
- Full local database: Rejected - too large (~500MB), hard to keep sync
- Hardcoded card text: Rejected - spec explicitly forbids this

**References**:
- Spec: "Card data sourced from Scryfall API (or local cache)"
- QWEN: "ScryfallClient, ability parser, local cache"

---

### 4. Training Data Export Strategy

**Decision**: Four separate export streams to MongoDB with JSON Lines format

**Rationale**:
- MongoDB fits the schema-less nature of game state snapshots
- JSON Lines (`.jsonl`) enables streaming writes without loading entire game
- Four streams map directly to spec requirements:
  1. `game_snapshots`: Board state at each priority grant
  2. `decision_transcripts`: Full play-by-play with annotations
  3. `rules_qa`: Q&A pairs derived from rule triggers
  4. `outcomes`: Win/loss records for RL

**Alternatives Considered**:
- Single MongoDB collection: Rejected - different schemas, harder to query
- File-based (Parquet/Avro): Rejected - spec requires MongoDB integration
- In-memory buffers: Rejected - risk of data loss on crash

**References**:
- Spec: "Four types of training data are exported per game"

---

### 5. Testing Strategy

**Decision**: pytest with pytest-asyncio, tests organized by engine module

**Rationale**:
- pytest provides superior fixtures and parametrize for rules testing
- pytest-asyncio handles async test cases (API tests)
- Test structure mirrors engine modules for maintainability
- 50 known-tricky interactions test suite (TASK-24)

**Alternatives Considered**:
- unittest: Rejected - pytest's fixtures and parametrize are superior
- hypothesis: Rejected - good complement but not primary test runner
- Property-based testing only: Rejected - need concrete rules interaction tests

**References**:
- QWEN: "pytest — test runner", "Always run tests with PYTHONPATH set to the project root"

---

### 6. Determinism Strategy

**Decision**: Seeded random.Random instances, never global random module

**Rationale**:
- MTG games must be replayable for training data validation
- Global random is not seedable per-game, leads to non-determinism
- Pass Random instance explicitly through game flow
- All card draws, shuffles, coin flips use seeded instance

**Alternatives Considered**:
- Global random with setseed: Rejected - not thread-safe, easy to forget
- UUID for everything: Rejected - loses probability distributions (e.g., 50/50 coin flip)

**References**:
- QWEN: "The engine must be deterministic given a fixed random seed. Use random.Random(seed) instances, never the global random module."

---

### 7. Error Handling Strategy

**Decision**: HTTP 422 with structured error response for illegal actions

**Rationale**:
- FastAPI's 422 Unprocessable Entity is semantically correct for validation failures
- Structured JSON response enables AI agents to handle errors programmatically
- Human-readable `error` + machine-readable `error_code` for debugging
- Never crash on illegal action - return error and maintain game state

**Alternatives Considered**:
- HTTP 400: Rejected - 422 is more specific for validation failures
- HTTP 500: Rejected - not a server error, client made invalid request
- Exception only: Rejected - need consistent API response format

**References**:
- QWEN: "Illegal game actions return HTTP 422 with a JSON body containing error (human-readable) and error_code (machine-readable string)"

---

### 8. Rules Implementation Strategy

**Decision**: Implement rules engine in strict phase order (TASK-09 through TASK-15)

**Rationale**:
- Stack (TASK-11) is prerequisite for triggers (TASK-12), layers (TASK-13), replacement (TASK-14), combat (TASK-15)
- SBAs (TASK-09) can be implemented early but integrated after stack
- Layer system (CR 613) is most complex - build and test in isolation
- Combat damage (CR 510, 702.19) depends on stack and triggers

**Implementation Order**:
1. TASK-09: State-based actions (CR 704)
2. TASK-11: Stack (CR 601-608)
3. TASK-12: Triggers (CR 603)
4. TASK-13: Layers (CR 613) - layers 1-7 in order
5. TASK-14: Replacement effects (CR 616)
6. TASK-15: Combat (CR 508-511)

**References**:
- QWEN: "Before implementing TASK-09 (SBAs): read CR 704 in full"
- QWEN: "Before implementing TASK-11 (stack): read CR 601-608 in full"
- QWEN: "Before implementing TASK-13 (layers): read CR 613 in full"

---

### 9. API Design Strategy

**Decision**: RESTful endpoints with Pydantic request/response models, dry_run support

**Rationale**:
- FastAPI auto-generates OpenAPI docs from Pydantic models
- `dry_run: bool` field on action requests enables AI agents to validate actions without state change
- All request bodies are Pydantic models (never raw dicts)
- Consistent response format: `{ data: {...} }` on success, `{ error: "...", error_code: "..." }` on failure

**Endpoints** (derived from spec):
- `POST /game` - Create new game
- `GET /game/{id}` - Get game state
- `POST /game/{id}/action` - Take game action
- `POST /game/{id}/choice` - Handle multi-option choices (replacement effects)
- `GET /game/{id}/export` - Export training data

**References**:
- QWEN: "Include a `dry_run: bool = False` field on all action request models"
- QWEN: "All request bodies are Pydantic models, never raw dicts or `Body(...)` with arbitrary types"

---

### 10. Card Ability Parsing Strategy

**Decision**: Data-driven parser that converts oracle text to effect objects, not card-name if/else

**Rationale**:
- 30,000+ MTG cards - impossible to hardcode behavior
- Oracle text follows consistent patterns (e.g., "When ~ enters the battlefield...", ":{T}: Add {G}")
- Parser extracts keywords (triggers, abilities, costs) and creates effect objects
- Enables AI agents to interact with any card without engine updates

**Alternatives Considered**:
- Full natural language parser: Rejected - overkill, oracle text is structured
- Regex-only: Rejected - can't handle nested brackets, complex interactions
- Hybrid: Rejected - spec requires data-driven approach

**References**:
- Spec: "Card ability parsing must be data-driven (oracle text → effect objects), not a giant if/else tree of card names"
- QWEN: "Card data from Scryfall API (not hardcoded)"

---

## Summary

All NEEDS CLARIFICATION items have been resolved using information from spec.md and QWEN.md:

| Unknown | Resolution |
|---------|------------|
| Language/Version | Python 3.11+ (from spec) |
| Dependencies | FastAPI, Pydantic v2, uvicorn, httpx, pymongo, pytest (from spec + QWEN) |
| Storage | MongoDB + SQLite (from spec) |
| Testing | pytest + pytest-asyncio (from QWEN) |
| Platform | Linux server (from spec) |
| Performance | <200ms p95 (from spec) |
| Constraints | Deterministic, JSON-serializable, 2-player only (from spec + QWEN) |

**Next Steps**: Phase 1 - Generate data-model.md, contracts/, quickstart.md

# Tasks: MTG Rules Engine

## Status key
[ ] todo  [x] done  [~] in progress  [!] blocked  [s] skipped

---

## Phase 1 — Project Scaffold & Data Models

- [x] TASK-01: Initialize project structure
  ```
  mtg_engine/
    api/          ← FastAPI routers
    engine/       ← rules logic
    models/       ← Pydantic models
    card_data/    ← Scryfall client + cache
    export/       ← training data exporters
    tests/
      conftest.py ← sys.path setup so imports work without install
      rules/
      api/
  ```
  Create `tests/conftest.py` with this exact content:
  ```python
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
  ```
  This makes `import mtg_engine` work from any pytest invocation.
  Install dependencies with plain pip (no -e flag):
  ```bash
  pip install fastapi uvicorn pydantic httpx pymongo pytest pytest-asyncio
  ```
  Done when: `uvicorn mtg_engine.api.main:app` starts without errors
  and `PYTHONPATH=. pytest tests/ -v` runs without ImportError

- [x] TASK-02: Define core Pydantic models in `models/`
  - `Card` (id, name, mana_cost, type_line, oracle_text, power,
    toughness, loyalty, colors, keywords, faces for DFC/split)
  - `Permanent` (card, controller, tapped, damage_marked, counters,
    attached_to, attachments, is_token, turn_entered_battlefield)
  - `StackObject` (source_card, controller, targets, effects,
    is_copy, modes_chosen)
  - `PlayerState` (name, life, hand, library, graveyard, exile,
    poison_counters, mana_pool, lands_played_this_turn)
  - `GameState` (game_id, seed, turn, active_player, phase, step,
    priority_holder, stack, battlefield, players, pending_triggers,
    state_hash)
  Done when: all models instantiate, serialize to JSON, and
  deserialize back without data loss

- [x] TASK-03: Define action request/response Pydantic models
  - `CastRequest`, `ActivateRequest`, `PlayLandRequest`,
    `DeclareAttackersRequest`, `DeclareBlockersRequest`,
    `AssignCombatDamageRequest`, `ChoiceRequest`, `PassRequest`
  - `LegalActionsResponse`, `GameStateResponse`, `ErrorResponse`
  Done when: all models instantiate with correct types and
  `PYTHONPATH=. pytest tests/ -v` confirms no import errors or type mismatches

---

## Phase 2 — Scryfall Integration & Card Parser

- [x] TASK-04: Implement `ScryfallClient` in `card_data/scryfall.py`
  - `get_card(name: str) -> Card` — fetches by exact name
  - `get_card_by_id(scryfall_id: str) -> Card` — fetches by id
  - Local SQLite cache (`card_data/cache.db`); cache hit skips API call
  - Maps Scryfall JSON fields to `Card` model
  Done when: `get_card("Lightning Bolt")` returns correct Card with
  cached result on second call

- [x] TASK-05: Implement ability parser in `card_data/ability_parser.py`
  - Parse triggered abilities: regex on "When/Whenever/At [trigger],
    [effect]" → `TriggeredAbility(trigger_condition, effect)`
  - Parse activated abilities: "{cost}: effect" →
    `ActivatedAbility(cost, effect, timing_restriction)`
  - Parse static abilities: known keyword list → `KeywordAbility(name)`
  - Unknown oracle text segments → `UnparsedAbility(raw_text)` with
    warning logged (REQ-C03)
  Done when: Lightning Bolt, Llanowar Elves, Serra Angel, Counterspell,
  and Dark Ritual all parse with no UnparsedAbility segments

- [x] TASK-06: Implement deck loader
  - `load_deck(card_names: list[str]) -> list[Card]` — resolves all
    cards via ScryfallClient, validates 60-card minimum, assigns unique
    instance IDs to each card object
  Done when: a 60-card deck loads in under 5s on first call (API),
  under 1s on second call (cache)

---

## Phase 3 — Core Rules Engine

- [x] TASK-07: Implement `ZoneManager` in `engine/zones.py`
  - Move operations: `move_to_zone(card_id, from_zone, to_zone,
    player, position="top"|"bottom"|"random")`
  - Enforces REQ-G07 (atomic), REQ-G08 (library order)
  - Emits zone-change events consumed by trigger detection
  Done when: moving a card between all zone combinations works
  without duplication or loss; token in non-battlefield zone is removed

- [x] TASK-08: Implement turn structure and phase/step advancement
  in `engine/turn_manager.py`
  - Full phase/step sequence per REQ-T01
  - `advance_phase()` — moves to next step/phase, applies start-of-step
    effects, grants priority to active player
  - `pass_priority(player)` — implements REQ-S01/S02 priority passing
    logic; resolves top of stack or advances phase when both players pass
  Done when: an empty-hand, no-permanents game advances correctly
  through all phases for 3 turns without intervention

- [x] TASK-09: Implement state-based actions in `engine/sba.py`
  Before writing any code, read CR 704 in full:
  `awk '/^704\./{found=1} found{print} /^705\./{exit}' cr.txt`
  - `check_and_apply_sbas(game_state) -> list[SBAEvent]`
  - All SBAs listed in REQ-R01
  - Returns list of events that occurred (for transcript logging)
  - Called automatically before every priority grant
  Done when: a 0/4 creature taking 4 damage dies correctly; a
  player at 0 life is marked as losing; legend rule fires when
  two copies of the same legendary enter

- [x] TASK-10: Implement mana system in `engine/mana.py`
  - `ManaPool` — tracks available mana by type (W, U, B, R, G, C)
  - `can_pay_cost(pool, cost) -> bool`
  - `pay_cost(pool, cost, payment: dict) -> ManaPool`
  - Handles generic mana, hybrid mana, Phyrexian mana, snow mana,
    colorless-specific costs
  - Mana pool empties at end of each step/phase
  Done when: Lightning Bolt ({R}), Counterspell ({U}{U}), and
  Emrakul ({15}) costs all validate correctly against matching pools

- [x] TASK-11: Implement casting and the stack in `engine/stack.py`
  Before writing any code, read CR 601-608:
  `awk '/^601\./{found=1} found{print} /^609\./{exit}' cr.txt`
  - `cast_spell(game_state, player, card_id, targets, mana_payment,
    alternative_cost) -> GameState`
  - Validates timing (sorcery vs instant, REQ-A03), mana, targets
  - Moves card to stack as StackObject, grants priority to active player
  - `resolve_top(game_state) -> GameState` — resolves top of stack,
    applies effects, moves card to appropriate zone
  - Split-second enforcement (REQ-S03)
  Done when: Lightning Bolt can be cast at instant speed targeting
  a creature; the creature dies on resolution; Counterspell can be
  cast in response; countered Lightning Bolt goes to graveyard

- [x] TASK-12: Implement trigger detection in `engine/triggers.py`
  Before writing any code, read CR 603 in full:
  `awk '/^603\./{found=1} found{print} /^604\./{exit}' cr.txt`
  - Listen for zone-change, damage, phase-change, and other events
  - Match events against all permanents' `TriggeredAbility` conditions
  - Queue matching triggers as pending for their controller (REQ-A08)
  - APNAP ordering for simultaneous triggers (REQ-S04)
  Done when: "When this creature dies" triggers correctly on
  graveyard entry; "At the beginning of your upkeep" triggers
  once per player turn

---

## Phase 4 — Layer System & Replacement Effects

- [x] TASK-13: Implement the layer system in `engine/layers.py`
  Before writing any code, read CR 613 IN FULL — this is mandatory:
  `awk '/^613\./{found=1} found{print} /^614\./{exit}' cr.txt`
  Pay special attention to CR 613.8 (dependency) and CR 613.10
  (timestamp order). Do not begin coding until you understand both.
  - `apply_continuous_effects(game_state) -> GameState`
  - Apply effects in layer order 1–7 per REQ-R02
  - Timestamp tracking on all continuous effects
  - Dependency graph computation within a layer (REQ-R03)
  Done when: Humility (all creatures lose abilities and are 1/1) +
  a creature with a static P/T boost resolve correctly with Humility
  winning in layer 6 (ability removal) then layer 7b (set P/T to 1/1)

- [x] TASK-14: Implement replacement effects in `engine/replacement.py`
  Before writing any code, read CR 616 in full:
  `awk '/^616\./{found=1} found{print} /^617\./{exit}' cr.txt`
  Also read CR 614 (preventing damage) and CR 615 (text-changing):
  `awk '/^614\./{found=1} found{print} /^616\./{exit}' cr.txt`
  - `get_applicable_replacements(event, game_state) -> list[Effect]`
  - `apply_replacement(event, effect) -> event` — modifies the event
  - Multiple replacement effects: prompt controller for order (REQ-R05)
  - Shield counters, regeneration, "instead" effects, enters-as-copy
  Done when: a creature with a shield counter has the counter removed
  instead of being destroyed; damage prevention effect reduces
  incoming damage correctly

- [x] TASK-15: Implement combat in `engine/combat.py`
  Before writing any code, read CR 508-511 (combat phases):
  `awk '/^508\./{found=1} found{print} /^512\./{exit}' cr.txt`
  Also read CR 702.19 (trample) and CR 702.2 (deathtouch):
  `grep -A 20 "^702\.19\." cr.txt`
  `grep -A 15 "^702\.2\." cr.txt`
  - `declare_attackers(game_state, attack_declarations) -> GameState`
  - `declare_blockers(game_state, block_declarations) -> GameState`
  - `assign_combat_damage(game_state, assignments) -> GameState`
  - First/double strike damage step (REQ-A14)
  - Trample overflow (REQ-R09), deathtouch lethal (REQ-R10),
    lifelink (REQ-R11), infect (REQ-R12)
  - Minimum lethal damage assignment validation (REQ-A15)
  Done when: a 3/3 tramplers blocked by a 1/1 deals 1 to the
  blocker and 2 to the player; a deathtouch 1/1 blocks a 5/5
  and both die

---

## Phase 5 — REST API

- [x] TASK-16: Implement FastAPI app and game router in `api/`
  - All endpoints from REQ-API section
  - `GameManager` singleton: dict of `game_id → GameState` in memory
  - All action endpoints call the relevant engine function and return
    updated game state or error
  Done when: `POST /game` with two 60-card decks returns a valid
  game state with correct initial zones

- [x] TASK-17: Implement `GET /legal-actions` endpoint
  - Computes all legal actions for the priority holder
  - Action types: pass, play-land, cast (per card in hand), activate
    (per permanent ability), put-trigger, special-action, declare-attackers
  - Returns structured action objects per REQ-6.3
  Done when: at the start of a main phase with a hand of 7 cards and
  3 lands on battlefield, legal actions include all castable spells
  and all activatable abilities

- [x] TASK-18: Implement `dry_run` support on all action endpoints
  - When `dry_run: true` in request body, validate and return projected
    state but do not commit to game_state (REQ-P05)
  Done when: dry_run cast of Lightning Bolt returns next state with
  bolt on stack but does not modify live game state

- [x] TASK-19: Implement `GET /pending-triggers` and
  `POST /put-trigger` endpoints
  Done when: a "whenever a creature dies" trigger appears in pending
  after a creature dies; putting it on the stack moves it to stack

---

## Phase 6 — Training Data Export

- [x] TASK-20: Implement snapshot recorder in `export/snapshots.py`
  - Hook into priority-grant events; record snapshot at each grant
  - `record_snapshot(game_state, legal_actions)` — stores in memory
  - `finalize_snapshot(action_taken)` — attaches the chosen action
    to the last snapshot
  Done when: a 5-turn game produces snapshots at every priority grant
  with correct `action_taken` attached to each

- [x] TASK-21: Implement transcript recorder in `export/transcript.py`
  - Event listener that appends to transcript on every engine event
  - Event types: cast, resolve, trigger, sba, zone_change, damage,
    phase_change, priority_grant, choice_made
  - Generates natural-language description for each event
  Done when: a complete game transcript is human-readable and
  every action in the game appears in order

- [x] TASK-22: Implement rules Q&A generator in `export/rules_qa.py`
  - Hooks into: layer resolution, replacement effect application,
    damage assignment, SBA application, targeting validation
  - Templates Q&A pairs from context: card names, board state,
    rule numbers (REQ-D08, REQ-D09)
  - At minimum 20 Q&A templates covering most common complex interactions
  Done when: a game involving deathtouch, trample, and lifelink
  produces at least 3 rules Q&A pairs with correct answers and
  CR citations

- [x] TASK-23: Implement outcome recorder and all export endpoints
  - `GET /export/{game_id}/snapshots` → JSONL file of all snapshots
  - `GET /export/{game_id}/transcript` → JSON array of transcript events
  - `GET /export/{game_id}/rules-qa` → JSON array of Q&A pairs
  - `GET /export/{game_id}/outcome` → single outcome JSON object
  - `DELETE /game/{game_id}` triggers MongoDB write of all four exports
  Done when: deleting a completed game writes four valid documents
  to MongoDB and all export endpoints return the correct data

---

## Phase 7 — Validation & Hardening

- [x] TASK-24: Write rules interaction test suite in `tests/rules/`
  - 50 specific known-tricky interactions (spec success criteria)
  - Priority: Humility + Opalescence, clone copying a clone, damage
    prevention + lifelink, undying + -1/-1 counters, cascade into
    cascade, split-second + trigger responses, mutate interactions,
    copy of a copy
  Done when: all 50 tests pass

- [x] TASK-25: Write API integration tests in `tests/api/`
  - Full game simulation: two scripted bots play a 5-turn game via
    HTTP using only `GET /legal-actions` → pick action → POST action
  - Verify no illegal states are reachable via the API
  Done when: 100 scripted games complete without 500 errors

- [x] TASK-26: Performance benchmark
  - Measure `GET /legal-actions` latency at various game complexities
    (empty board, 20 permanents, complex stack)
  - Confirm REQ-P01 (under 200ms) on target hardware
  Done when: p99 latency is documented; any hotspot over 200ms
  has a filed optimization note

- [x] TASK-27: Concurrent game stress test
  - Spin up 10 games simultaneously, run scripted bots on all, verify
    no state bleed between games (REQ-P02)
  Done when: 10 concurrent games complete with correct, isolated
  outcomes

---

## Phase 8 — Archidekt Deck Import Integration

- [x] TASK-28: Implement Archidekt deck import feature
  Before writing any code, review the updated `spec.md` for the
  Archidekt deck import feature requirements (REQ-P01, REQ-P02,
  REQ-P03, REQ-S01, REQ-S02, REQ-S03, REQ-U01, REQ-U02, REQ-U03, REQ-T01, REQ-T02, REQ-T03, REQ-T04)

  ### Implementation Steps

  #### 1. Create Pydantic models for deck import
  - `DeckImportRequest` (Pydantic v2):
    - `archidekt_url: str | None` (URL to Archidekt deck)
    - `file_data: bytes | None` (uploaded file content)
    - `format: DeckFormat` (enum: ARCHIDEKT_JSON, ARCHIDEKT_TEXT, SCRYALLAH_TXT)
    - `deck_name: str` (optional custom name)
  - `DeckPreview` (Pydantic v2):
    - `main_deck: list[CardPreview]` (list of cards with quantities)
    - `sideboard: list[CardPreview]` (optional sideboard)
    - `total_cards: int` (main deck count)
    - `sideboard_count: int` (sideboard count)
    - `is_valid: bool` (deck legality check)
    - `errors: list[str]` (validation errors if invalid)
  - `CardPreview` (Pydantic v2):
    - `name: str`
    - `quantity: int`
    - `scryfall_id: str | None`
    - `is_legal: bool`

  #### 2. Implement deck parser in `card_data/archidekt_parser.py`
  - `parse_archidekt_json(url: str) -> dict` — fetches and parses Archidekt JSON API
  - `parse_archidekt_text(content: str) -> dict` — parses text format (card name xN)
  - `parse_scryfall_txt(content: str) -> dict` — parses Scryfall text format
  - All parsers return: `{"main": [(name, qty), ...], "sideboard": [(name, qty), ...]}`
  - Validate deck size: main deck 60+ cards, sideboard max 15
  - Validate card count: max 4 of each non-basic card
  - Handle special cases: basic lands (unlimited), token cards (warn but allow)

  #### 3. Implement deck validation in `card_data/deck_validator.py`
  - `validate_deck_format(deck_data: dict) -> tuple[bool, list[str]]`
  - `check_card_legality(card_name: str, format: str) -> bool`
  - `resolve_cards(card_names: list[str]) -> list[Card]` — uses ScryfallClient
  - Handle unknown cards: return list of names that couldn't be resolved
  - Enforce format restrictions (Standard, Modern, etc.) if specified
  - Performance: cache card lookups, batch API calls (REQ-P01)

  #### 4. Implement security validation in `card_data/security.py`
  - `validate_file_upload(file_content: bytes, content_type: str) -> bool` (REQ-S01)
  - `sanitize_input(deck_name: str) -> str` — strip dangerous characters
  - `check_file_size(content: bytes) -> bool` — max 10MB (REQ-T02)
  - `validate_content_type(content_type: str) -> bool` (REQ-S02)
  - Rate limiting: max 10 imports per minute per IP (REQ-S03)
  - Input sanitization: prevent injection attacks

  #### 5. Implement API endpoints in `api/deck_import.py`
  - `POST /deck/import` — import deck from URL or file upload
    - Request body: `DeckImportRequest`
    - Returns: `DeckPreview` with validation results
    - HTTP 200: success with preview
    - HTTP 400: invalid format (REQ-D01)
    - HTTP 403: upload rejected (REQ-S02)
    - HTTP 500: internal error (REQ-R01)
  - `POST /deck/import/{deck_id}/preview` — get preview of imported deck
  - `GET /deck/import/{deck_id}` — retrieve saved deck
  - `DELETE /deck/import/{deck_id}` — delete imported deck
  - All endpoints support `dry_run` parameter for validation without saving

  #### 6. Implement deck preview workflow (REQ-U01)
  - Step 1: File selection or URL input
  - Step 2: Format validation and parsing
  - Step 3: Preview display (card list, errors, warnings)
  - Step 4: User confirmation or edit
  - Step 5: Save to deck library or use in game
  - Progress indicators for large files (REQ-U03)
  - Clear error messages for invalid decks (REQ-U02)

  #### 7. Integrate with game creation
  - `POST /game` accepts `deck_id` parameter to use imported deck
  - `POST /game` accepts `deck_preview` parameter to create game from preview
  - Imported decks are stored in memory with TTL (24 hours)
  - Deck library persists across sessions (optional MongoDB storage)

  #### 8. Performance optimizations (REQ-P01, REQ-P02)
  - Batch card resolution: resolve 100 cards in parallel
  - Cache resolved decks in Redis/Memory (TTL 1 hour)
  - Async file processing for large decks
  - API latency under 200ms for deck preview (REQ-P02)
  - Support 100+ concurrent imports (REQ-P03)

  #### 9. Error handling and logging
  - Log all import attempts with timestamps
  - Track failed imports for debugging
  - Return structured error responses with error codes
  - Map errors to requirement numbers (REQ-D01, REQ-S02, REQ-R01)

  ### Done when:
  - [x] Pydantic models for `DeckImportRequest`, `DeckPreview`, `CardPreview` are defined
  - [x] Archidekt JSON parser works with real Archidekt deck URLs
  - [x] Text format parser handles standard decklist formats
  - [x] Deck validation enforces 60-card minimum, 4-copy limit
  - [x] Security validation rejects malicious file uploads
  - [x] Rate limiting prevents abuse (10 imports/minute/IP)
  - [x] API endpoints return correct HTTP status codes and error messages
  - [x] Preview workflow completes in under 30 seconds for valid decks
  - [x] Performance benchmarks: 100+ card deck loads in under 5s
  - [x] Integration tests pass for all edge cases (REQ-T01 to REQ-T04)
  - [x] Clear error messages displayed for invalid deck formats
  - [x] Progress indicators shown for large file uploads

  ### Testing Requirements
  - Unit tests for all parser functions
  - Integration tests for API endpoints
  - Edge case tests:
    - Invalid file formats (REQ-T01)
    - Large file uploads (>10MB) (REQ-T02)
    - Concurrent imports (REQ-T03)
    - Malformed JSON in deck files (REQ-T04)
  - Performance tests: deck load times for 100+ card decks
  - Security tests: file upload validation, rate limiting

  ### Files to Create/Modify
  - `models/deck_import.py` — Pydantic models for deck import
  - `card_data/archidekt_parser.py` — Archidekt deck parser
  - `card_data/deck_validator.py` — Deck validation logic
  - `card_data/security.py` — Security validation
  - `api/deck_import.py` — Deck import API endpoints
  - `tests/api/test_deck_import.py` — API integration tests
  - `tests/card_data/test_archidekt_parser.py` — Parser unit tests

  ### Dependencies
  - `httpx` — Async HTTP client for Archidekt API
  - `aiofiles` — Async file I/O for large files
  - `tenacity` — Retry logic for API calls
  - `pydantic` — All data models (v2)

  ### Notes
  - Do not hard-code card names — use Scryfall API for resolution
  - All game state must be fully serializable to JSON
  - Engine must be deterministic given a fixed random seed
  - Follow project coding conventions (type hints, Pydantic v2)
  - Reference CR numbers in comments for rules-related validation

---

## User Stories by Priority

### P0 - Critical Requirements (Must Have)
- [ ] US-P0-01: As a game engine, I must enforce all core game rules to ensure valid game states
- [ ] US-P0-02: As an AI agent, I must be able to query legal actions to make valid moves
- [ ] US-P0-03: As a trainer, I must receive complete training data exports for every game
- [ ] US-P0-04: As a developer, I must have a REST API that supports full game lifecycle management
- [ ] US-P0-05: As a user, I must be able to import decks from Archidekt format for game setup

### P1 - Important Requirements (Should Have)
- [ ] US-P1-01: As a game engine, I must correctly handle layer resolution and replacement effects
- [ ] US-P1-02: As a game engine, I must enforce state-based actions consistently
- [ ] US-P1-03: As a game engine, I must support full combat mechanics including damage assignment
- [ ] US-P1-04: As a game engine, I must handle complex interaction scenarios like Humility + Opalescence
- [ ] US-P1-05: As a game engine, I must correctly validate targeting and prevent illegal actions

### P2 - Nice to Have Requirements (Could Have)
- [ ] US-P2-01: As a game engine, I must support performance targets with sub-200ms latency
- [ ] US-P2-02: As a game engine, I must support concurrent game sessions
- [ ] US-P2-03: As a game engine, I must provide detailed rule explanations for illegal actions
- [ ] US-P2-04: As a developer, I must have comprehensive test coverage for game rules
- [ ] US-P2-05: As a user, I must see clear error messages when decks are invalid

### P3 - Future Enhancement Requirements (Won't Have)
- [s] US-P3-01: As a game engine, I must support multi-player games
- [s] US-P3-02: As a game engine, I must support Commander-specific rules
- [s] US-P3-03: As a game engine, I must support digital-only mechanics
- [s] US-P3-04: As a game engine, I must support GUI or human-facing interface
- [s] US-P3-05: As a game engine, I must support draft or sealed deck simulation

---

## Requirements Coverage by Category

### 1. Game Management (REQ-G01 - REQ-G05)
- [ ] REQ-G01: POST /game creates a new game, accepts two player configs
- [ ] REQ-G02: GET /game/{game_id} returns the full current game state
- [ ] REQ-G03: DELETE /game/{game_id} ends and archives a game, triggering data export
- [ ] REQ-G04: Each game is assigned a random seed at creation
- [ ] REQ-G05: Game state includes: turn number, active player, phase, step, priority holder, etc.

### 2. Turn Structure (REQ-T01 - REQ-T05)
- [ ] REQ-T01: Full turn structure is enforced in order
- [ ] REQ-T02: POST /game/{game_id}/pass advances priority to the next player
- [ ] REQ-T03: Untap step does not use the stack
- [ ] REQ-T04: Active player draws one card at the start of their Draw step
- [ ] REQ-T05: Cleanup step discards to hand size, removes damage from creatures

### 3. Actions (REQ-A01 - REQ-A16)
- [ ] REQ-A01: POST /game/{game_id}/play-land accepts card_id
- [ ] REQ-A02: Playing a land does not use the stack
- [ ] REQ-A03: POST /game/{game_id}/cast accepts card_id, mana_payment, targets
- [ ] REQ-A04: Casting a spell moves it to the stack
- [ ] REQ-A05: Alternative costs are accepted via alternative_cost field
- [ ] REQ-A06: POST /game/{game_id}/activate accepts permanent_id and ability_index
- [ ] REQ-A07: Mana abilities resolve immediately without using the stack
- [ ] REQ-A08: Engine automatically detects and generates triggered ability objects
- [ ] REQ-A09: GET /game/{game_id}/pending-triggers returns triggers waiting to be put on the stack
- [ ] REQ-A10: POST /game/{game_id}/put-trigger puts a pending trigger on the stack
- [ ] REQ-A11: POST /game/{game_id}/declare-attackers accepts array of attack declarations
- [ ] REQ-A12: POST /game/{game_id}/declare-blockers accepts array of blocker declarations
- [ ] REQ-A13: POST /game/{game_id}/order-blockers handles multiple blockers
- [ ] REQ-A14: First strike and double strike damage are handled as two separate combat damage steps
- [ ] REQ-A15: POST /game/{game_id}/assign-combat-damage validates minimum lethal damage assignment rules
- [ ] REQ-A16: POST /game/{game_id}/special-action handles special actions

### 4. Stack and Priority (REQ-S01 - REQ-S05)
- [ ] REQ-S01: Priority is granted to the active player after each spell/ability placed on the stack
- [ ] REQ-S02: The top of the stack resolves only when all players pass priority
- [ ] REQ-S03: Split-second spells prevent any player from casting spells/activating abilities
- [ ] REQ-S04: APNAP ordering for simultaneous triggers
- [ ] REQ-S05: GET /game/{game_id}/legal-actions returns complete set of legal actions

### 5. Rules Engine Coverage (REQ-R01 - REQ-R20)
- [ ] REQ-R01: State-based actions are checked and applied continuously
- [ ] REQ-R02: Continuous effects are applied in correct layer order
- [ ] REQ-R03: Dependency between effects within a layer is computed correctly
- [ ] REQ-R04: Timestamp ordering is used when no dependency exists
- [ ] REQ-R05: Replacement effects modify events before they occur
- [ ] REQ-R06: When multiple replacement effects apply, player chooses order of application
- [ ] REQ-R07: Damage to creatures uses damage-marked system
- [ ] REQ-R08: Damage to players reduces life total
- [ ] REQ-R09: Trample damage: excess damage beyond lethal to blockers is assigned to defending player
- [ ] REQ-R10: Deathtouch: any amount of damage from a deathtouch source is considered lethal for SBA purposes
- [ ] REQ-R11: Lifelink: damage dealt by a lifelink creature causes its controller to gain that much life
- [ ] REQ-R12: Infect: damage to creatures is dealt as -1/-1 counters; damage to players is poison counters
- [ ] REQ-R13: Counter types are tracked as key-value pairs
- [ ] REQ-R14: +1/+1 and -1/-1 counters annihilate each other as an SBA
- [ ] REQ-R15: Copying a spell or permanent copies copiable values but not choices, counters, or damage
- [ ] REQ-R16: A token created as a copy of a permanent copies current copiable values at creation
- [ ] REQ-R17: Token creation instantiates a permanent with specified characteristics
- [ ] REQ-R18: Targets are validated at casting/activation and resolution
- [ ] REQ-R19: Protection, shroud, and hexproof are correctly enforced
- [ ] REQ-R20: All keyword abilities listed are fully implemented

### 6. REST API (REQ-API01 - REQ-API05)
- [ ] REQ-API01: All responses are JSON
- [ ] REQ-API02: Successful responses return HTTP 200 with a data key
- [ ] REQ-API03: Illegal actions return HTTP 422 with error key
- [ ] REQ-API04: Unknown game IDs return HTTP 404
- [ ] REQ-API05: All game state objects include a state_hash field

### 7. Training Data Export (REQ-D01 - REQ-D10)
- [ ] REQ-D01: A snapshot is recorded at every point priority is granted
- [ ] REQ-D02: Each snapshot contains full serialized game state, legal actions, and action taken
- [ ] REQ-D03: Schema for game state snapshots
- [ ] REQ-D04: One transcript per game with every action, trigger, SBA, and resolution
- [ ] REQ-D05: Each transcript entry includes sequence number, event type, description, and structured data
- [ ] REQ-D06: Transcript is suitable for conversion into Q&A training pairs
- [ ] REQ-D07: Q&A pairs generated during complex rule interactions
- [ ] REQ-D08: Q&A schema with question, answer, game_id, turn, etc.
- [ ] REQ-D09: Q&A questions are templated from actual game context
- [ ] REQ-D10: One outcome record per game with winner, win condition, etc.

### 8. Card Resolution (REQ-C01 - REQ-C05)
- [ ] REQ-C01: Card abilities are parsed from Scryfall oracle text into structured effect objects
- [ ] REQ-C02: Ability parser handles triggered, activated, static, and spell effects
- [ ] REQ-C03: Unsupported cards are flagged with parse_status: "unsupported"
- [ ] REQ-C04: Scryfall responses are cached locally
- [ ] REQ-C05: Engine supports double-faced, adventure, split, and modal double-faced cards

### 9. Performance and Reliability (REQ-P01 - REQ-P05)
- [ ] REQ-P01: GET /game/{game_id}/legal-actions must respond in under 200ms
- [ ] REQ-P02: Engine must handle at least 10 concurrent games
- [ ] REQ-P03: All game state is stored in memory during play
- [ ] REQ-P04: Unhandled exceptions return HTTP 500 with error details
- [ ] REQ-P05: Engine supports dry_run flag on action endpoints

---

## Implementation Tasks by Feature Area

### Core Engine Logic
- [ ] Implement full layer system with dependency resolution and timestamp ordering (REQ-R02, REQ-R03, REQ-R04)
- [ ] Implement replacement effects system with multiple effect handling (REQ-R05, REQ-R06)
- [ ] Implement comprehensive combat system with first/double strike, trample, deathtouch, lifelink, infect (REQ-A14, REQ-R09, REQ-R10, REQ-R11, REQ-R12)
- [ ] Implement complete targeting validation system (REQ-R18, REQ-R19)
- [ ] Implement comprehensive state-based action system (REQ-R01)
- [ ] Implement mana system with complex mana types (hybrid, Phyrexian, snow, colorless) (REQ-A03)
- [ ] Implement complete trigger system with APNAP ordering (REQ-A08, REQ-S04)

### Game State Management
- [ ] Implement comprehensive game state models with all required fields (REQ-G05)
- [ ] Implement zone management with atomic operations and library ordering (REQ-G06, REQ-G07, REQ-G08)
- [ ] Implement turn structure with all phases and steps (REQ-T01)
- [ ] Implement priority system with proper granting and passing logic (REQ-S01, REQ-S02)
- [ ] Implement comprehensive card parsing for all card types and keywords (REQ-C01, REQ-C02, REQ-C05)

### API Integration
- [ ] Implement full REST API with all required endpoints (REQ-API01 - REQ-API05)
- [ ] Implement legal actions endpoint with full action computation (REQ-S05)
- [ ] Implement dry_run functionality for all action endpoints (REQ-P05)
- [ ] Implement complete deck import functionality with Archidekt and Scryfall formats (REQ-P01, REQ-P02, REQ-P03)
- [ ] Implement all data export endpoints with proper JSON schemas (REQ-D01 - REQ-D10)

### Training Data Generation
- [ ] Implement snapshot recording with proper action tracking (REQ-D01, REQ-D02, REQ-D03)
- [ ] Implement transcript generation with full event logging (REQ-D04, REQ-D05, REQ-D06)
- [ ] Implement rules Q&A generation with context-based templating (REQ-D07, REQ-D08, REQ-D09)
- [ ] Implement outcome recording with win/loss tracking (REQ-D10)
- [ ] Implement complete data export pipeline with MongoDB integration

### Security and Performance
- [ ] Implement rate limiting for deck imports (REQ-S03)
- [ ] Implement file upload validation for security (REQ-S01, REQ-S02)
- [ ] Implement performance optimization for large deck loading (REQ-P01)
- [ ] Implement concurrent game handling with no state bleed (REQ-P02)
- [ ] Implement error handling with structured responses (REQ-P04)

---

## Testing Requirements

### Unit Tests
- [ ] Test all Pydantic models for serialization/deserialization
- [ ] Test core engine logic functions (zones, turn management, SBA, mana)
- [ ] Test layer system with complex interactions
- [ ] Test replacement effects with multiple applications
- [ ] Test combat mechanics with various damage types
- [ ] Test targeting validation and protection rules
- [ ] Test deck import parsers with various formats
- [ ] Test security validation for file uploads

### Integration Tests
- [ ] Test complete game lifecycle from creation to deletion
- [ ] Test all API endpoints with valid and invalid requests
- [ ] Test legal actions computation under various game states
- [ ] Test concurrent game sessions
- [ ] Test deck import workflow from URL to game creation
- [ ] Test data export endpoints with complete game state

### Performance Tests
- [ ] Benchmark legal actions endpoint latency with complex game states
- [ ] Test concurrent game handling with 10+ simultaneous games
- [ ] Test large deck loading times (100+ cards)
- [ ] Test API latency under load conditions

### Edge Case Tests
- [ ] Test malformed deck files and invalid formats
- [ ] Test large file uploads (>10MB) with rate limiting
- [ ] Test concurrent imports with rate limiting
- [ ] Test complex rule interactions (Humility + Opalescence, etc.)
- [ ] Test error responses with correct HTTP status codes

---

## Performance and Quality Requirements

### Performance Targets
- [ ] All core API endpoints must respond in under 200ms (REQ-P01)
- [ ] Engine must handle at least 10 concurrent games without state bleed (REQ-P02)
- [ ] Deck import must complete under 5s for decks with 100+ cards (REQ-P01)
- [ ] API latency must remain under 200ms for all actions (REQ-P01)
- [ ] Support 100+ concurrent game sessions (REQ-P03)

### Quality Assurance
- [ ] All game state must be fully serializable to JSON (REQ-API05)
- [ ] Engine must be deterministic given a fixed random seed (REQ-G04)
- [ ] All rules must be enforced consistently (REQ-R01, REQ-R02, etc.)
- [ ] Error responses must include proper HTTP status codes and error messages (REQ-API03, REQ-API04)
- [ ] All data exports must conform to defined schemas (REQ-D03, REQ-D08, REQ-D10)

### Security
- [ ] All file uploads must be validated for malicious content (REQ-S01)
- [ ] Content-type validation must be enforced for uploaded files (REQ-S02)
- [ ] Rate limiting must be implemented for file upload endpoints (REQ-S03)
- [ ] Input sanitization must prevent injection attacks
- [ ] All endpoints must validate request parameters and return appropriate error codes

### Reliability
- [ ] Engine must handle unhandled exceptions gracefully (REQ-P04)
- [ ] Game state must be preserved at last valid checkpoint during errors
- [ ] All game actions must be validated before execution
- [ ] All game lifecycle events must be logged appropriately
- [ ] Data export must be triggered correctly on game deletion

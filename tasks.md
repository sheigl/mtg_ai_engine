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

- [ ] TASK-24: Write rules interaction test suite in `tests/rules/`
  - 50 specific known-tricky interactions (spec success criteria)
  - Priority: Humility + Opalescence, clone copying a clone, damage
    prevention + lifelink, undying + -1/-1 counters, cascade into
    cascade, split-second + trigger responses, mutate interactions,
    copy of a copy
  Done when: all 50 tests pass

- [ ] TASK-25: Write API integration tests in `tests/api/`
  - Full game simulation: two scripted bots play a 5-turn game via
    HTTP using only `GET /legal-actions` → pick action → POST action
  - Verify no illegal states are reachable via the API
  Done when: 100 scripted games complete without 500 errors

- [ ] TASK-26: Performance benchmark
  - Measure `GET /legal-actions` latency at various game complexities
    (empty board, 20 permanents, complex stack)
  - Confirm REQ-P01 (under 200ms) on target hardware
  Done when: p99 latency is documented; any hotspot over 200ms
  has a filed optimization note

- [ ] TASK-27: Concurrent game stress test
  - Spin up 10 games simultaneously, run scripted bots on all, verify
    no state bleed between games (REQ-P02)
  Done when: 10 concurrent games complete with correct, isolated
  outcomes

# mtg_ai_engine Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-13

## Active Technologies
- N/A (in-memory game state) (029-skip-empty-phases)

- Python 3.11 + FastAPI, Pydantic v2, motor (async MongoDB driver) (028-player-default-settings)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes
- 2026-06-13: **VEN-01 Venture/Dungeon design complete** — Design document created for CR 701.61 Venture into the Dungeon mechanic
  - Existing `dungeon.py` has correct signatures but needs mutability fix (direct dict/list mutations → model_copy transforms)
  - Stack integration missing: "venture into the dungeon" regex not in `_apply_single_effect_text()` / `_apply_spell_effect()` — card effects silently no-op
  - Missing: room choice system (`DungeonRoomChoice` model, `pending_dungeon_room_choice` on GameState), API handler for choices
  - Design doc at `specs/038-gap-analysis/VEN-01-design.md`

- 2026-06-13: **MON-01 Monarch implementation complete** — CR 702.147 The Monarch mechanic fully implemented and tested
  - Fixed `set_monarch()` mutability: now returns new GameState via `model_copy(update={"monarch": ..., "pending_triggers": ...})` instead of direct mutation
  - Added `is_monarch(game_state, player_name) -> bool` query helper for card effects referencing monarch status
  - Added game initialization in `game_manager.py`: sets `monarch=active_player` for commander/conspiracy formats; `None` otherwise
  - Fixed pre-existing bug in `triggers.py`: rewrote monarch/initiative combat damage checks to call functions with correct `(target_player, attacker_controller)` args instead of broken `(game_state, damaging_perm_ids)` signature
  - Fixed pre-existing dead code: moved unreachable `"combat_damage"` trigger detection from `check_mana_spent_triggers` (after return) into `check_damage_triggers` as fallback regex for "this creature deals combat damage" patterns
  - Created integration test suite at `tests/engine/test_monarch_integration.py` (21 tests across 6 classes)
  - Status: All 21 monarch integration tests pass, all 14 original monarch unit tests pass, full suite: 2002 passed, 3 skipped, 13 xfailed, no regressions

- 2026-06-13: **MON-01 Monarch design complete** — Design document created for CR 702.147 The Monarch mechanic
  - Existing `monarch.py` has correct signatures but needs mutability fix and `is_monarch()` helper
  - Combat hook (combat/core.py) and turn manager hook (turn_manager.py) already wired
  - Missing: game initialization for monarch in commander/conspiracy formats, integration tests
  - Design doc at `specs/038-gap-analysis/MON-01-design.md`

- 2026-06-13: **CMD-01 BUG FIX: `commander_zone_stay` card disappearance** — Fixed critical bug where choosing "let commander go to intended destination" caused the card to vanish from all zones. Root cause: API handler called `move_card_to_zone(gs, card, "battlefield", ...)` but the card had already been removed from its source zone by the initial move call that queued the pending choice. Fix: directly append card to the intended destination zone via `getattr(player_obj, intended).append(card)`.
  - Updated `mtg_engine/api/routers/game.py` line 1821: replaced hardcoded `"battlefield"` source with direct zone append
  - Updated `tests/engine/formats/test_commander_integration.py`: `_simulate_commander_zone_stay` now matches fixed logic
  - Status: 20 integration tests pass (was 18), 59 total commander tests pass, no regressions

- 2026-06-13: **CMD-01 Commander Rules implementation complete** — Partner support, CR 903.8 tax, CR 903.9 zone replacement, CR 903.10a damage loss
  - Added `commander_names`, `commander_damage` to `PlayerState`; `pending_commander_zone_choice` to `GameState`
  - Refactored `record_commander_cast`, `add_commander_to_command_zone`, `move_card_to_command_zone` to pure `model_copy` transforms
  - Updated `zones.py`: CR 903.9 human path (pending choice) vs AI path (auto-redirect) in `move_card_to_zone` / `move_permanent_to_zone`
  - Updated `combat/core.py`: commander damage tracking writes to `PlayerState.commander_damage[permanent_id]`
  - Updated `api/routers/game.py`: `commander_zone_replace`/`commander_zone_stay` choice handlers + legal actions in `_compute_legal_actions`
  - New test file: `tests/engine/formats/test_commander.py` (14 tests)
  - Updated existing `tests/engine/test_commander.py` for new data model (25 tests)
  - Status: 39 commander tests pass, 1936+ total tests pass, no regressions from CMD-01 changes

- 2026-06-13: **038-gap-analysis identified** — Fresh gap analysis (June 2026) after all 037-forge-parity tasks closed
  - 5 major gap categories: 169 keywords, 104 trigger types, 7 game mechanics, 5 formats, 6 API features
  - Implementation plan: 6 sprints with 15+ tasks (see `specs/038-gap-analysis/plan.md`)
  - Tracked in `.opencode/pipeline/status.md` under "038-Gap-Analysis Backlog"

- 2026-06-13: 034-etb-choices test coverage
  - Created `tests/engine/test_etb_detection.py` (18 tests: 13 pass, 5 xfail for fetchland/snow_dual regex issues)
  - Created `tests/engine/test_etb_ai.py` (22 tests: 18 pass, 4 xfail for checkland "or" type and snow_dual placeholder)
  - Created `tests/engine/test_etb_integration.py` (10 tests: 6 pass, 4 xfail for known TODOs)
  - Created `tests/api/test_etb_choices.py` (13 tests: 10 pass, 3 skipped for unimplemented land types)
  - Created `tests/rules/test_etb_gameplay.py` (5 tests: all pass)
  - Status: 68 total ETB tests (52 pass, 3 skip, 13 xfail), no regressions in 1931+ existing tests

- 2026-06-13: BUG-26 Spree mechanic completion
  - Added `_lose_life` and `_tutor_to_top` helpers to `mtg_engine/engine/stack.py`
  - Added Spree-specific patterns to `_apply_single_effect_text()` for tutor-to-top and combined draw+lose life effects
  - Created `tests/engine/test_spree.py` with comprehensive test coverage for Spree resolution
  - Status: Implementation complete, all 13 tests passing, 345 engine tests pass with no regressions

- 029-skip-empty-phases: Added Python 3.11 + FastAPI, Pydantic v2

- 028-player-default-settings: Added Python 3.11 + FastAPI, Pydantic v2, motor (async MongoDB driver)

<!-- MANUAL ADDITIONS START -->

## Project-Specific Coding Standards

### Testing Framework
- **pytest** for all tests
- Use `pytest.mark.comprehensive_rules` and `pytest.mark.cr("XXX.X")` for rules-engine tests
- Use `pytest.mark.skip` or `pytest.mark.xfail` for tests blocked by known TODOs
- Test fixtures go in `conftest.py` or as module-level helpers
- Prefer module-level helper functions (`_make_game`, `create_test_card`) over class fixtures for simple object creation

### Backend Code (Python 3.11 + FastAPI + Pydantic v2)
- All models use Pydantic v2 `BaseModel` with `Field(default_factory=...)` for mutable defaults
- GameState is the central immutable-ish state object; functions return modified `GameState`
- Zone changes are atomic: remove from source, then add to destination
- Use `model_copy(update={...})` for Pydantic v2 updates
- Engine functions in `mtg_engine/engine/` should be pure-ish (take GameState, return GameState)
- API routers in `mtg_engine/api/routers/` use `get_manager()` for game state persistence
- Import style: `from mtg_engine.models.game import GameState, Card, PlayerState`

### Frontend Code (React + TypeScript)
- Types defined in `frontend/src/types/game.ts`
- Components use functional style with hooks
- Game state fetched via REST API, not WebSocket
- Action submission via `POST /game/{id}/choice` with `{ choice_id: string }`

### Database (MongoDB via motor)
- `motor` is the async MongoDB driver
- Game state serialized via `model_dump()` for storage
- Not actively used in current test suite (in-memory game manager)

### Sample Backend Code (Engine Layer)
```python
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool
from mtg_engine.engine.zones import put_permanent_onto_battlefield

# Create a minimal game state
p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
gs = GameState(
    game_id="test",
    seed=1,
    active_player="p1",
    priority_holder="p1",
    players=[p1, p2],
)

# Create a card with ETB choice text
card = Card(
    name="Steam Vents",
    type_line="Land — Island Mountain",
    oracle_text="As this land enters, you may pay 2 life. If you don't, it enters tapped.",
)

# Put onto battlefield — for human player, queues pending_etb_choice
gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
```

### Sample Backend Code (API Layer)
```python
from fastapi.testclient import TestClient
from mtg_engine.api.main import app

client = TestClient(app)

# Create game with human player
resp = client.post("/game", json={
    "player1_name": "p1",
    "player2_name": "p2",
    "deck1": ["Steam Vents"] * 60,
    "deck2": ["Forest"] * 60,
    "seed": 42,
    "human_player_name": "p1",
})
game_id = resp.json()["data"]["game_id"]

# Get legal actions (should include etb_pay / etb_tapped)
la_resp = client.get(f"/game/{game_id}/legal-actions")
actions = la_resp.json()["data"]["legal_actions"]

# Submit ETB choice
choice_resp = client.post(f"/game/{game_id}/choice", json={
    "choice_id": "etb_pay",
})
```

### Sample Testing Code (pytest)
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool
from mtg_engine.engine.zones import _detect_etb_choice, ETBChoice, ETBChoiceType

# Detection test pattern
def test_detect_shockland():
    oracle = "As this land enters, you may pay 2 life. If you don't, it enters tapped."
    choice = _detect_etb_choice(oracle)
    assert choice is not None
    assert choice.choice_type == ETBChoiceType.SHOCKLAND
    assert choice.cost_amount == 2
    assert choice.cost_type == "life"

# AI resolution test pattern
def test_ai_pays_for_shockland_when_safe():
    from mtg_engine.engine.zones import _resolve_etb_choice_with_ai
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    gs = GameState(game_id="test", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    choice = ETBChoice(choice_type=ETBChoiceType.SHOCKLAND, cost_amount=2, cost_type="life")
    gs, tapped = _resolve_etb_choice_with_ai(gs, "p1", choice, "perm-1", "Steam Vents")
    assert not tapped  # AI pays 2 life, enters untapped
    assert p1.life == 18

# Engine integration test pattern
def test_human_path_queues_pending_choice():
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    p1 = PlayerState(name="p1", life=20)
    gs = GameState(game_id="test", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2], human_player_name="p1")
    card = Card(name="Steam Vents", type_line="Land", oracle_text="As this land enters, you may pay 2 life. If you don't, it enters tapped.")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    assert gs.pending_etb_choice is not None
    assert gs.pending_etb_choice["permanent_id"] == perm.id
    assert perm.tapped is True  # Default tapped until choice made

# API integration test pattern
def test_etb_choice_legal_actions():
    from fastapi.testclient import TestClient
    from mtg_engine.api.main import app
    client = TestClient(app)
    # ... create game, play land, verify legal actions include etb_pay and etb_tapped

# Monarch unit test pattern (MON-01)
def test_monarch_sets_and_queries():
    from mtg_engine.engine.monarch import set_monarch, is_monarch
    gs = GameState(game_id="test", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    assert is_monarch(gs, "p1") is False  # No monarch yet

    gs = set_monarch(gs, "p1")
    assert is_monarch(gs, "p1") is True
    assert is_monarch(gs, "p2") is False

# Monarch combat integration test pattern (MON-01)
def test_monarch_transfers_on_combat_damage():
    from mtg_engine.models.game import Phase, Step
    from mtg_engine.models.actions import AttackDeclaration
    from mtg_engine.engine.combat import declare_attackers, assign_combat_damage

    gs = GameState(
        game_id="t-monarch", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS, players=[p1, p2], monarch="p2"
    )
    card = Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2")
    gs, attacker = put_permanent_onto_battlefield(gs, card, "p1")
    attacker.summoning_sick = False

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)

    assert is_monarch(gs, "p1"), f"Expected p1 to be monarch, got {gs.monarch}"

# Monarch end step draw test pattern (MON-01)
def test_monarch_draws_at_end_step():
    from mtg_engine.engine.monarch import handle_end_step_draw
    gs = GameState(
        game_id="t-monarch-draw", seed=1, active_player="p1", priority_holder="p1",
        phase="ending", step="end", players=[p1_with_lib, p2], monarch="p1"
    )
    hand_before = len(p1_with_lib.hand)
    gs = handle_end_step_draw(gs)
    assert len(p1_with_lib.hand) == hand_before + 1
```

## Initial Codebase Details

### Core Engine Modules
- `mtg_engine/engine/zones.py` — Zone management, `put_permanent_onto_battlefield`, `_detect_etb_choice`, `_resolve_etb_choice_with_ai`
- `mtg_engine/engine/stack.py` — Spell resolution, effect application
- `mtg_engine/engine/turn_manager.py` — Phase/step advancement
- `mtg_engine/engine/monarch.py` — CR 702.147 Monarch: `set_monarch`, `handle_end_step_draw`, `check_combat_damage_monarch`, `is_monarch`
- `mtg_engine/models/game.py` — Pydantic models: GameState, Card, Permanent, PlayerState, StackObject, etc.
- `mtg_engine/api/routers/game.py` — FastAPI endpoints: game lifecycle, actions, choices, legal actions

### Key Patterns for ETB Choices
- Detection: `_detect_etb_choice(oracle_text: str) -> ETBChoice | None` uses regex to classify 4 land types
- AI Resolution: `_resolve_etb_choice_with_ai(gs, player, choice, perm_id, name) -> (gs, should_be_tapped)`
- Human Path: `put_permanent_onto_battlefield` sets `game_state.pending_etb_choice` and `tapped=True`
- API Resolution: `choice_id="etb_pay"` subtracts life and sets `perm.tapped=False`; `choice_id="etb_tapped"` clears pending choice
- Legal Actions: `_compute_legal_actions` returns `etb_pay` + `etb_tapped` + `pass` when `pending_etb_choice` exists for priority player

### Existing Test Patterns
- `tests/engine/test_spree.py` — Uses `create_test_card`, `create_test_game` helpers; tests `_apply_single_effect_text`
- `tests/api/test_api.py` — Uses `TestClient(app)`, `clear_games` fixture; tests full HTTP flows
- `tests/rules/test_legal_actions.py` — Uses `_make_game`, `_make_card`, `_make_permanent` helpers; tests `_compute_legal_actions`
- `tests/rules/test_zones.py` — Uses `_make_game` helper; tests `move_card_to_zone`, `put_permanent_onto_battlefield`
- `tests/test_020/test_020_etb_replacements.py` — Tests unconditional "enters tapped" and "enters with counters"
- `tests/ability/keywords/test_etb.py` — Tests ETB keyword triggers (separate from ETB choice system)

### Known Gaps (Documented in Code)
- `_compute_legal_actions` only fully implements shockland ETB choices (lines 2236-2252). Checkland/fetchland/snow_dual have TODO comments.
- Snow dual AI heuristic subtracts life instead of snow mana (placeholder until snow mana tracking is implemented).
- Fetchland AI heuristic does not actually exile land from graveyard (comment says "would need additional logic").

### Commander/Partner Coding Standards (CMD-01)
- **Never check `commander_name` directly** in engine code. Always use `_is_commander(card_name, player)` or `_get_commander_names(player)` from `mtg_engine/engine/formats/commander.py`.
- **Commander state transforms must be pure**: `record_commander_cast` and `add_commander_to_command_zone` return new `GameState` via `model_copy(update=...)` on the player and players list.
- **CR 903.9 replacement effect**: For human players, queue `pending_commander_zone_choice` in `GameState` and return without completing the zone change. For AI, auto-redirect to command zone.
- **Partner tax independence**: `commander_cast_counts` is keyed by card name; each partner tracks its own cast count.
- **Partner damage tracking**: `commander_damage` is keyed by permanent ID; each partner's combat damage is tracked separately. 21+ damage from a single permanent ID triggers loss.
- **Companion**: Out of scope for CMD-01. Delegate to COM-01.

### Key Patterns for Commander Zone Replacement
- Detection: `move_card_to_zone` and `move_permanent_to_zone` check `_is_commander(card.name, player)` before applying CR 903.9
- Human Path: Sets `game_state.pending_commander_zone_choice` with `player`, `card`, `permanent_id`, `intended_destination`, `from_zone`
- AI Path: Immediately calls `move_card_to_command_zone(game_state, card, player_name)`
- API Resolution: `choice_id="commander_zone_replace"` moves to command zone; `choice_id="commander_zone_stay"` moves to intended destination
- Legal Actions: `_compute_legal_actions` returns `commander_zone_replace` + `commander_zone_stay` + `pass` when `pending_commander_zone_choice` exists for priority player

### Monarch Coding Standards (MON-01)
- **Monarch tracking**: `GameState.monarch: str | None` tracks which player holds the monarch. Initialized to `active_player` on game creation for "commander" and "conspiracy" formats; `None` for other formats.
- **State transforms must be pure**: `set_monarch(gs, player)` returns new `GameState` via `model_copy(update={"monarch": player_name})`. Never mutate `game_state.monarch` directly.
- **CR 702.147 combat damage hook**: `check_combat_damage_monarch(gs, target_player, attacker_controller)` is called from `combat/core.py` during `assign_combat_damage`. If the target is the monarch, the attacker's controller becomes the new monarch.
- **CR 702.147 end step draw**: `handle_end_step_draw(gs)` is called from `turn_manager.py` at end step. Only draws if `active_player == monarch`.
- **Query helper**: Use `is_monarch(game_state, player_name) -> bool` to check if a player holds the monarch (for card effects that reference "if you're the monarch").
- **"become_monarch" trigger**: `set_monarch` fires a `PendingTrigger` with `trigger_type="become_monarch"` when monarch changes. Cards like "whenever you become the monarch" resolve from this trigger.

### Key Patterns for Monarch
- Game Initialization: `game_manager.py` sets `monarch=active_player` for commander/conspiracy formats at game creation
- Combat Hook: `combat/core.py` line 667 calls `check_combat_damage_monarch(gs, target_player, attacker_controller)` during damage assignment
- End Step Hook: `turn_manager.py` lines 389-391 call `handle_end_step_draw(gs)` at end step
- Query: `is_monarch(game_state, player_name) -> bool` for card effects referencing monarch status

### Venture/Dungeon Coding Standards (VEN-01)
- **Dungeon tracking**: `GameState.player_dungeons: dict[str, DungeonProgress]` tracks per-player dungeon progress. `GameState.player_completed_dungeons: dict[str, int]` counts completed dungeons per player. Both already exist in GameState.
- **State transforms must be pure**: All functions in `engine/dungeon.py` return new `GameState` via `model_copy(update={...})`. Never mutate `game_state.player_dungeons`, `game_state.pending_triggers`, or `game_state.player_completed_dungeons` directly.
- **CR 701.61 venture flow**: `venture(gs, player_name, dungeon_name=None)` handles the full venturing logic: starts new dungeon if none in progress/complete, advances to next room, fires room ability via stack resolution, increments completion counter when done.
- **Room effect resolution**: `_apply_room_effect(gs, player_name, ability_text)` routes room ability text through `_apply_single_effect_text()` so existing patterns (draw, scry, gain life, etc.) work without hard-coding each room's logic.
- **"venture into the dungeon" stack pattern**: Added to both `_apply_single_effect_text()` and `_apply_spell_effect()` in `stack.py`. Pattern: `r"\bventure\s+into\s+(?:the\s+)?dungeon\b"` with word boundaries to avoid false positives on "adventure".
- **Room choices**: Rooms may have `choices: list[DungeonRoomChoice]` — for human players, queues `pending_dungeon_room_choice`; for AI, auto-resolves using `is_default` flag.
- **Recursive venturing**: Undercity rooms contain "venture into the dungeon" in their ability text. This correctly chains through stack resolution → venture() again. Guard against infinite loops via `progress.is_complete` check.
- **Dungeon model**: Defined in `models/dungeon.py` with 4 dungeons (Mad Mage, Phandelver, Tomb of Annihilation, Undercity). Each dungeon has named rooms with ability text.

### Key Patterns for Venture/Dungeon
- Engine: `engine/dungeon.py` — `venture()`, `start_dungeon()`, `_apply_room_effect()`, `get_dungeon_progress()`
- Stack Integration: `engine/stack.py` — "venture into the dungeon" regex in effect resolution patterns
- Initiative Hook: `engine/initiative.py` line 57 calls `venture(gs, player_name, dungeon_name="Undercity")` during upkeep
- Trigger System: `engine/triggers.py` — `check_completed_dungeon_triggers()` fires "whenever you complete a dungeon" triggers

### Sample Backend Code (Dungeon Engine)
```python
from mtg_engine.engine.dungeon import venture, start_dungeon, get_dungeon_progress

# Start a specific dungeon for a player
gs, room_text = start_dungeon(gs, "Alice", "Lost Mine of Phandelver")
assert room_text == "Create a 1/1 green Goblin creature token"

# Venture into the dungeon (auto-starts if none in progress)
gs = venture(gs, "Bob")  # Defaults to first available dungeon
progress = get_dungeon_progress(gs, "Bob")
assert progress is not None
assert progress.current_room_index == 1  # Advanced past room 0

# Pure transform: new GameState object returned
old_id = id(gs)
gs = venture(gs, "Alice")
assert id(gs) != old_id
```

### Sample Testing Code (Dungeon Integration)
```python
import pytest
from mtg_engine.engine.dungeon import venture, start_dungeon, get_completed_dungeon_count
from mtg_engine.engine.stack import _apply_single_effect_text
from mtg_engine.models.game import GameState, PlayerState, Card
from mtg_engine.models.actions import StackObject

def test_venture_from_card_effect():
    """Card effect 'Venture into the dungeon.' resolves via stack."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
    )
    stack_obj = StackObject(
        source_card=Card(name="The Dungeon", oracle_text="Venture into the dungeon."),
        controller="Alice",
    )
    gs = _apply_single_effect_text(gs, stack_obj, "Venture into the dungeon.")
    progress = get_dungeon_progress(gs, "Alice")
    assert progress is not None

def test_dungeon_completion():
    """Completing all rooms increments completion counter."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
    )
    gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")  # 3 rooms
    for _ in range(3):
        gs = venture(gs, "Alice")
    assert get_completed_dungeon_count("Alice", gs) == 1

def test_pure_transform():
    """venture() returns new GameState object."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
    )
    old_id = id(gs)
    gs = venture(gs, "Alice")
    assert id(gs) != old_id
```

<!-- MANUAL ADDITIONS END -->

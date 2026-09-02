# mtg_ai_engine Coding Standards

## Testing Framework
- **pytest** for all tests
- Use `pytest.mark.comprehensive_rules` and `pytest.mark.cr("XXX.X")` for rules-engine tests
- Use `pytest.mark.skip` or `pytest.mark.xfail` for tests blocked by known TODOs
- Test fixtures go in `conftest.py` or as module-level helpers
- Prefer module-level helper functions (`_make_game`, `create_test_card`) over class fixtures for simple object creation

### Testing Patterns for Keyword Modules
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool, Permanent
from mtg_engine.engine.zones import get_player

def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-keyword", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2],
    )

# Detection test pattern
def test_keyword_detection():
    from mtg_engine.ability.keywords.example import ExampleKeyword
    assert ExampleKeyword.from_oracle_text("Example keyword text") is True
    assert ExampleKeyword.has_example(["example"]) is True

# Resolution test pattern (trigger-based keywords)
def test_trigger_resolution():
    from mtg_engine.engine.triggers import initialize_triggers, put_trigger_on_stack
    from mtg_engine.engine.stack import resolve_top
    gs = _make_game()
    initialize_triggers(gs)
    # ... set up permanent, kill it, verify trigger queued
    trigger = next(t for t in gs.pending_triggers if t.trigger_type == "example")
    gs = put_trigger_on_stack(gs, trigger.id, targets=[])
    gs = resolve_top(gs)
    # ... verify resolution effects

# Queue/resolve test pattern (evoke-style keywords)
def test_queue_and_resolve():
    from mtg_engine.ability.keywords.example import queue_effect, resolve_effect
    gs = _make_game()
    card = Card(name="Example", type_line="Creature — Beast", oracle_text="Example {1}")
    perm = Permanent(card=card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)
    
    # Queue the effect
    gs = queue_effect(gs, "perm-1", "p1", card.name)
    assert gs.pending_example is not None
    
    # Resolve it
    gs = resolve_effect(gs)
    assert gs.pending_example is None

# Pure transform assertion pattern
def test_pure_transform():
    from mtg_engine.ability.keywords.example import some_function
    gs = _make_game()
    old_id = id(gs)
    gs = some_function(gs, ...)
    assert id(gs) != old_id  # New object returned

# AI resolution test pattern
def test_ai_resolution():
    from mtg_engine.ability.keywords.example import resolve_with_ai
    gs = _make_game()
    # ... set up state
    gs = resolve_with_ai(gs, ...)
    # ... verify AI made correct decision
```

### Sample Backend Code (Engine Layer)
```python
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool
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

## Backend Code (Python 3.11 + FastAPI + Pydantic v2)
- All models use Pydantic v2 `BaseModel` with `Field(default_factory=...)` for mutable defaults
- GameState is the central immutable-ish state object; functions return modified `GameState`
- Zone changes are atomic: remove from source, then add to destination
- Use `model_copy(update={...})` for Pydantic v2 updates
- Engine functions in `mtg_engine/engine/` should be pure-ish (take GameState, return GameState)
- API routers in `mtg_engine/api/routers/` use `get_manager()` for game state persistence
- Import style: `from mtg_engine.models.game import GameState, Card, PlayerState`

## Keyword Module Coding Standards (Sprint 7 P0)
- **Keyword modules own their logic**: Each keyword's `apply()`, `resolve_trigger()`, or equivalent method contains the real implementation. Engine files delegate to keyword modules via module-level convenience functions.
- **Module-level convenience functions are primary API surface**: Engine code calls `afterlife.resolve_trigger(gs, stack_obj)` not `AfterlifeKeyword().resolve_trigger(gs, perm)`. This matches deathtouch/lifelink/infect patterns.
- **Dual export pattern**: Each keyword module exports both instance methods (on the class) AND module-level convenience functions that delegate to instances. This gives flexibility for different call sites.
- **Engine wrapper files as thin delegates**: Files like `engine/evoke.py`, `engine/morph.py`, `engine/suspend.py` become thin wrappers that import from and delegate to keyword modules. They maintain backward compatibility for existing imports (tests, API routers).
- **Lazy imports for cross-module dependencies**: When a keyword module needs engine helpers (like `_create_token_with_pt_and_keywords` from stack.py), use lazy imports inside the function body to avoid circular imports: `from mtg_engine.engine.stack import _create_token_with_pt_and_keywords`.
- **Player update pattern**: When modifying a player in GameState, use the inline pattern: `players = [new_player if p.name == name else p for p in gs.players]; gs.model_copy(update={"players": players})`. Don't extract this into a shared helper — it's 2 lines and duplication is clearer than indirection.

## Frontend Code (React + TypeScript)
- Types defined in `frontend/src/types/game.ts`
- Components use functional style with hooks
- Game state fetched via REST API, not WebSocket
- Action submission via `POST /game/{id}/choice` with `{ choice_id: string }`

## Trigger Wiring Coding Standards (TRG-B1)

### Core Principles
- **All trigger check functions are pure transforms**: Each function takes GameState, returns new GameState via `model_copy(update={"pending_triggers": ...})`. Never mutate directly.
- **Lazy imports for cross-module dependencies**: When wiring triggers into stack.py or other engine files, use lazy imports inside the function body to avoid circular imports:
  ```python
  def _gain_life(game_state, player_name, n):
      # ... existing logic ...
      from mtg_engine.engine.triggers import check_life_gain_lost_triggers
      game_state = check_life_gain_lost_triggers(game_state, player_name, n)
      return game_state
  ```
- **Wiring at engine layer only**: Triggers fire at the lowest level of the engine that has GameState context. API routers should NOT wire triggers — they call engine functions which handle trigger firing internally.
- **Mana spent/production triggers scoped carefully**: `pay_cost()` and `add_mana()` are pure ManaPool functions without GameState context. Wire triggers at their call sites in the engine layer (stack.py, morph.py, mana.py). API router's `can_pay_cost` calls for legal actions computation do NOT fire triggers.

### Trigger Check Function Signatures
All 13 trigger check functions follow this pattern:
```python
def check_<trigger_type>_triggers(game_state: GameState, **kwargs) -> GameState:
    """Check for <trigger type> triggers and queue them as PendingTrigger objects."""
    # Returns new GameState via model_copy(update={"pending_triggers": [...]})
```

### Trigger Wiring Points by Type

| Trigger Type | Check Function | Wire Location(s) | Event Moment |
|---|---|---|---|
| Sacrifice | `check_sacrifice_triggers(gs, perm_ids, controller)` | `_sacrifice_permanent()` helper (zones.py) | Permanent moves from battlefield to graveyard via sacrifice |
| Life Gain/Lost | `check_life_gain_lost_triggers(gs, player_name, amount)` | `_gain_life()`, `_lose_life()` (stack.py) | Player life total changes |
| Fight | `check_fight_triggers(gs, creature_ids)` | `_apply_fight()` new function (stack.py) | Two creatures fight each other |
| Transformed | `check_transformed_triggers(gs, perm_id)` | `_transform_daybound_permanents()` (daynight.py) | Permanent transforms to other face |
| Tutor/Search | `check_tutor_triggers(gs, player_name)` | `_tutor()`, `_tutor_to_top()` (stack.py) | Player searches library |
| Becomes Target | `check_becomes_target_triggers(gs, perm_ids, source_controller)` | `_cast_spell()` after target validation (stack.py) | Permanent becomes a target during casting |
| Attach | `check_attach_triggers(gs, aura_perm_id)` | `resolve_top()` after aura attaches (stack.py) | Aura permanently attaches to target |
| Mana Spent | `check_mana_spent_triggers(gs, player_name)` | `_cast_spell()`, morph face-up (morph.py) | Player pays mana from pool |
| Draw | `check_draw_triggers(gs, player_name)` | `_draw_cards()` (stack.py), `draw_card()` (zones.py) | Player draws cards |
| Discard | `check_discard_triggers(gs, player_name)` | `_discard_cards()` (stack.py) | Player discards cards |
| Token Created | `check_token_triggers(gs, controller)` | All token creation functions (stack.py) | Token enters battlefield |
| Counter Placed | `check_counter_triggers(gs, perm_id, counter_type)` | `_add_counters()` (stack.py) | Counters placed on permanent |
| Mana Production | `check_mana_production_triggers(gs, source_perm_id, mana_symbols)` | `resolve_land_mana_ability()`, `resolve_mana_ability()` (mana.py) | Land ability produces mana |

### Centralized Helper Pattern for Sacrifice
```python
# In zones.py — centralized sacrifice helper
def _sacrifice_permanent(game_state: GameState, perm_id: str) -> tuple[GameState, Permanent | None]:
    """Sacrifice a permanent. Fires sacrifice triggers."""
    player_obj = get_player(game_state, controller_name)
    perm = next((p for p in game_state.battlefield if p.id == perm_id), None)
    if perm is None:
        return game_state, None

    # Remove from battlefield
    new_battlefield = [p for p in game_state.battlefield if p.id != perm_id]
    
    # Add to graveyard
    player_obj.graveyard.append(perm.card)
    new_player = player_obj.model_copy(update={"graveyard": list(player_obj.graveyard)})
    players = [new_player if p.name == controller_name else p for p in game_state.players]

    gs = game_state.model_copy(update={
        "battlefield": new_battlefield,
        "players": players,
    })

    # Fire sacrifice triggers
    from mtg_engine.engine.triggers import check_sacrifice_triggers
    gs = check_sacrifice_triggers(gs, [perm_id], controller_name)

    return gs, perm
```

### Testing Pattern for Trigger Wiring
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool, Permanent

def _make_game() -> GameState:
    p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
    p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
    return GameState(
        game_id="test-trigger-wiring", seed=1, active_player="p1", priority_holder="p1",
        players=[p1, p2],
    )

# Trigger wiring test pattern — verify trigger queued after event
def test_trigger_fires_on_event():
    from mtg_engine.engine.stack import _gain_life
    gs = _make_game()
    
    # Set up a permanent with "whenever you gain life" ability on battlefield
    trigger_card = Card(
        name="Life Trigger", type_line="Creature — Beast", power="2", toughness="2",
        oracle_text="Whenever you gain life, draw a card.",
    )
    perm = Permanent(card=trigger_card, controller="p1", id="perm-1")
    gs.battlefield.append(perm)

    # Perform the triggering event
    gs = _gain_life(gs, "p1", 5)

    # Verify trigger was queued
    life_triggers = [t for t in gs.pending_triggers if t.trigger_type == "life_gain"]
    assert len(life_triggers) >= 1
    assert life_triggers[0].source_card_name == "Life Trigger"
```

## Database (MongoDB via motor)
- `motor` is the async MongoDB driver
- Game state serialized via `model_dump()` for storage
- Not actively used in current test suite (in-memory game manager)

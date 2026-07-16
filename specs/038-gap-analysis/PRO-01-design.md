# Design: PRO-01 Proliferate System

## Overview
Complete CR 701.27 "Proliferate" mechanic: choose any number of permanents and/or players that have a counter, then give each one additional counter of each kind that permanent or player already has. The system includes stack integration for card effects, pending choice handling for human players, AI auto-resolution, trigger firing ("whenever you proliferate"), and proper immutable state transforms.

## Architecture Decisions

### Decision 1: Fix mutability bugs in existing `engine/proliferate.py`
**Rationale**: The current implementation has three direct mutation anti-patterns that violate the project standard (AGENTS.md):
- `apply_proliferate()` line 60: `perm.counters[counter_type] = count + 1` — mutates permanent counters in place
- `apply_proliferate()` line 72: `target_player.poison_counters += 1` — mutates player poison counter in place
- `setup_pending_proliferate()` line 106: `game_state.pending_proliferate_choice = {...}` — mutates GameState directly

All three functions return the same GameState object reference instead of a new one via `model_copy(update={...})`. The monarch.py module provides the correct pattern to follow.

**Trade-offs considered**:
- **Alternative**: Keep mutable style for proliferate-only code. Rejected: inconsistent with rest of engine, makes testing harder, breaks serialization assumptions.
- **Chosen approach**: Rewrite all functions in `engine/proliferate.py` to return new GameState via model_copy, matching monarch.py pattern.

### Decision 2: Eliminate duplicate eligible-collection logic between `proliferate.py` and `stack.py`
**Rationale**: Currently `_trigger_proliferate()` in stack.py (line 1009-1036) duplicates the eligible-target collection from `get_proliferate_eligible()` in proliferate.py. Worse, the stack version does NOT filter internal counters (`__deathtouch_damage__`, etc.) — it uses bare `if perm.counters:` while proliferate.py correctly filters with `not k.startswith("__")`. This means internal engine counters could appear as eligible proliferate targets.

**Trade-offs considered**:
- **Alternative**: Keep both implementations, fix the stack version to filter internals. Rejected: violates DRY principle; two code paths for same logic will diverge over time.
- **Chosen approach**: Delete `_trigger_proliferate()` from stack.py entirely. Replace with call to `proliferate.setup_pending_proliferate()`.

### Decision 3: Eliminate duplicate counter-application logic between API handler and engine
**Rationale**: The API router at line 1082-1089 duplicates the exact same counter-incrementing logic as `apply_proliferate()` in proliferate.py. This means bugs fixed in one place won't propagate to the other.

**Trade-offs considered**:
- **Alternative**: Keep both implementations for performance (avoid import). Rejected: negligible performance difference; correctness and maintainability matter more.
- **Chosen approach**: API handler delegates to `proliferate.apply_proliferate()` — single source of truth.

### Decision 4: Wire up "whenever you proliferate" trigger firing after resolution
**Rationale**: `check_proliferated_triggers()` exists in triggers.py (line 679) but is NEVER called from the API handler or stack resolution flow. Cards like Flux Channeler ("Whenever you proliferate, draw a card") silently do nothing after proliferate resolves.

**Trade-offs considered**:
- **Alternative**: Fire triggers inside `apply_proliferate()`. Rejected: engine functions should be focused; trigger checking is an orchestration concern belonging in the API layer or stack resolution.
- **Chosen approach**: API handler calls `check_proliferated_triggers(gs, player_name)` after applying proliferate and before `_run_sbas()`.

### Decision 5: Add AI auto-resolution for proliferate choices
**Rationale**: Currently there is no path for AI players to resolve a pending proliferate choice. If an AI-controlled spell says "proliferate", the game hangs with `pending_proliferate_choice` set but no one making the choice.

**Trade-offs considered**:
- **Alternative**: Always auto-resolve (no pending choice) when player is AI. Rejected: inconsistent with other pending choice patterns (ETB, commander zone replacement) which use human vs AI branching.
- **Chosen approach**: Follow established pattern — for human players, queue `pending_proliferate_choice`; for AI, immediately resolve using a heuristic (proliferate to all eligible targets controlled by the proliferating player).

### Decision 6: Fix `check_proliferated_triggers` mutability
**Rationale**: The function directly appends to `game_state.pending_triggers.append(trigger)` at line 705. This violates immutability pattern.

**Trade-offs considered**:
- **Alternative**: Leave as-is since triggers are always appended. Rejected: inconsistent with project standards; breaks if GameState is frozen or serialized mid-operation.
- **Chosen approach**: Build new list and return via `model_copy(update={"pending_triggers": new_list})`.

## Files to Create/Modify

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/proliferate.py` | Fix all 3 mutability bugs: use `model_copy(update={...})` for state transforms; add AI resolution function `_resolve_proliferate_with_ai()` | Core engine correctness + new features |
| `mtg_engine/engine/stack.py` | Delete `_trigger_proliferate()`, replace with call to `proliferate.setup_pending_proliferate()` or `_resolve_proliferate_with_ai()` based on human/AI player | Eliminate duplicate code, fix internal counter leak |
| `mtg_engine/api/routers/game.py` | Replace inline counter logic with `proliferate.apply_proliferate()`; add `check_proliferated_triggers()` call after resolution | Single source of truth, trigger firing |
| `mtg_engine/engine/triggers.py` | Fix `check_proliferated_triggers()` mutability: use model_copy instead of append | Consistency with project patterns |

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `tests/engine/test_proliferate_integration.py` | Integration tests for full proliferate flow | Test card effect → pending choice → resolution → trigger firing cycle, test AI auto-resolution, test pure transforms |

## Task Breakdown (Ordered by Dependency)

### Task 1: Fix mutability bugs in `engine/proliferate.py`
- **Files**: `mtg_engine/engine/proliferate.py`
- **Description**: 
  1. Rewrite `apply_proliferate()` to build new battlefield list and players list with updated counters, return via `model_copy(update={"battlefield": ..., "players": ...})`. Never mutate perm.counters or player.poison_counters in place.
  2. Rewrite `setup_pending_proliferate()` to use `model_copy(update={"pending_proliferate_choice": {...}})` instead of direct mutation.
  3. Add `_resolve_proliferate_with_ai(game_state, controller) -> GameState` that auto-selects all eligible targets controlled by the proliferating player and calls `apply_proliferate()`.
- **Acceptance Criteria**: 
  - All existing tests in `tests/engine/test_proliferate.py` still pass
  - Calling `apply_proliferate()` returns a new GameState object (`id(new_gs) != id(old_gs)`)
  - Calling `setup_pending_proliferate()` returns a new GameState object
  - `_resolve_proliferate_with_ai()` correctly selects and proliferates to AI player's eligible targets

### Task 2: Fix mutability in `engine/triggers.py` — `check_proliferated_triggers`
- **Files**: `mtg_engine/engine/triggers.py`
- **Description**: 
  1. Replace `game_state.pending_triggers.append(trigger)` with building a new list and returning via `model_copy(update={"pending_triggers": new_list})`.
  2. Ensure the function signature remains `check_proliferated_triggers(game_state, player_name) -> GameState`.
- **Acceptance Criteria**: 
  - All existing tests in `tests/engine/test_b1_missing_triggers.py` still pass (specifically proliferate trigger tests)
  - Function returns new GameState object

### Task 3: Eliminate duplicate code in `engine/stack.py`
- **Files**: `mtg_engine/engine/stack.py`
- **Description**: 
  1. Delete `_trigger_proliferate()` function (lines 1009-1036).
  2. In the proliferate fallback check (lines 990-993), replace with: import from `proliferate` module, check if controller is human player → call `setup_pending_proliferate()`; else → call `_resolve_proliferate_with_ai()`.
  3. This also fixes the internal counter leak (stack version didn't filter `__*` counters).
- **Acceptance Criteria**: 
  - Card effects with "proliferate" still set pending choice for human players
  - AI player proliferate auto-resolves without pending choice
  - Internal counters (`__deathtouch_damage__`, etc.) are NOT eligible targets

### Task 4: Fix API handler to use engine functions and fire triggers
- **Files**: `mtg_engine/api/routers/game.py`
- **Description**: 
  1. In `POST /{game_id}/proliferate` endpoint (line 1060), replace the inline counter-incrementing logic (lines 1079-1089) with a single call to `proliferate.apply_proliferate(gs, req.targets)`.
  2. After applying proliferate and before `_run_sbas()`, add: `gs = check_proliferated_triggers(gs, player_name)` so "whenever you proliferate" abilities fire.
  3. Ensure the endpoint still validates targets against eligible list (lines 1075-1077).
- **Acceptance Criteria**: 
  - API proliferate endpoint works correctly with fewer lines of code
  - Flux Channeler-style "whenever you proliferate" triggers fire after API resolution
  - Target validation still rejects ineligible targets

### Task 5: Add integration tests
- **Files**: `tests/engine/test_proliferate_integration.py` (new)
- **Description**: Create comprehensive integration tests covering:
  1. Card effect "Proliferate" → sets pending choice for human player
  2. API resolution of proliferate choice adds counters correctly
  3. "Whenever you proliferate" trigger fires after resolution
  4. AI auto-resolution proliferates to own eligible targets
  5. Multiple counter types on one permanent all increment
  6. Poison counter proliferation on players
  7. Internal counters are NOT eligible for proliferation
  8. Pure transform: `apply_proliferate()` returns new GameState object
- **Acceptance Criteria**: 
  - All integration tests pass
  - No regressions in existing 2000+ test suite

### Task 6: Verify full test suite passes
- **Files**: N/A (run tests)
- **Description**: Run `PYTHONPATH=. pytest tests/ -v` to confirm no regressions. Specifically check `tests/engine/test_proliferate.py`, new integration tests, and `tests/engine/test_b1_missing_triggers.py`.
- **Acceptance Criteria**: All existing + new tests pass

## Data Models / Interfaces

### Existing GameState field (no change needed)
```python
class GameState(BaseModel):
    # ... existing fields ...
    pending_proliferate_choice: Optional[dict] = None
    # Format: {"player": str, "eligible": [{"id": str, "name": str, "counters": dict, "type": str}]}
```

### Existing Permanent counters (no change needed)
```python
class Permanent(BaseModel):
    # ... existing fields ...
    counters: dict[str, int] = Field(default_factory=dict)
    # Keys are counter type names like "+1/+1", "charge", "lore", etc.
    # Internal engine counters prefixed with "__" (e.g., "__deathtouch_damage__")
```

### Existing PlayerState poison tracking (no change needed)
```python
class PlayerState(BaseModel):
    # ... existing fields ...
    poison_counters: int = 0
```

### Fixed: Pure `apply_proliferate()` function signature
```python
def apply_proliferate(
    game_state: GameState,
    target_ids: list[str],
) -> GameState:
    """
    Apply proliferate to the given targets. CR 701.27.

    Each target must have at least one counter. For each counter type the
    target already has, one more is added.

    Pure transform: returns new GameState via model_copy. Never mutates
    perm.counters or player.poison_counters in place.
    """
```

### Fixed: Pure `setup_pending_proliferate()` function signature
```python
def setup_pending_proliferate(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """
    Set the pending_proliferate_choice on the game state so the player can
    select targets via the legal actions system.

    Pure transform: returns new GameState via model_copy.
    """
```

### New: AI resolution function
```python
def _resolve_proliferate_with_ai(
    game_state: GameState,
    controller: str,
) -> GameState:
    """
    Auto-resolve proliferate for an AI player.

    Heuristic: proliferate to all eligible targets controlled by the 
    proliferating player (never help opponents). Also includes the 
    proliferating player themselves if they have poison counters.
    
    Pure transform: returns new GameState via model_copy.
    """
```

### Fixed: Pure `check_proliferated_triggers()` signature
```python
def check_proliferated_triggers(
    game_state: GameState,
    player_name: str,
) -> GameState:
    """Check for 'whenever you proliferate' triggers. Pure transform."""
    # ... builds new pending_triggers list via model_copy instead of append ...
```

### Fixed: Stack.py proliferate integration (no more duplicate code)
```python
# In _apply_single_effect_text(), lines 990-993, replace with:
if re.search(r'\bproliferate\b', oracle, re.IGNORECASE):
    from mtg_engine.engine.proliferate import setup_pending_proliferate, _resolve_proliferate_with_ai
    
    # Determine if controller is human or AI
    is_human = any(
        p.name == stack_obj.controller and 
        getattr(game_state, 'human_player_name', None) == p.name
        for p in game_state.players
    )
    
    if is_human:
        game_state = setup_pending_proliferate(game_state, stack_obj.controller)
    else:
        game_state = _resolve_proliferate_with_ai(game_state, stack_obj.controller)
    return game_state
```

## Testing Strategy

### Unit Tests (existing, in `tests/engine/test_proliferate.py`)
- `TestGetProliferateEligible`: 7 tests for eligible target detection ✅ already exists
- `TestApplyProliferate`: 6 tests for counter application — need updating to verify pure transforms
- `TestSetupPendingProliferate`: 1 test for pending choice setup — need updating to verify pure transform

### New Integration Tests (`tests/engine/test_proliferate_integration.py`)
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent
from mtg_engine.engine.proliferate import (
    apply_proliferate, setup_pending_proliferate, 
    get_proliferate_eligible, _resolve_proliferate_with_ai,
)
from mtg_engine.engine.stack import _apply_single_effect_text
from mtg_engine.models.actions import StackObject

def _make_game() -> GameState:
    card = Card(name="Test Creature", type_line="Creature — Beast", power="2", toughness="2")
    perm = Permanent(
        id="perm-1", card=card, controller="Alice", counters={"charge": 3},
    )
    return GameState(
        game_id="test-pro-integ", seed=42, turn=1,
        active_player="Alice", priority_holder="Alice",
        players=[
            PlayerState(name="Alice", life=20, poison_counters=2,
                       library=[Card(name=f"C{i}") for i in range(20)]),
            PlayerState(name="Bob", life=20, poison_counters=1),
        ],
        battlefield=[perm],
    )

class TestPureTransforms:
    """Test that proliferate functions return new GameState objects."""
    
    def test_apply_proliferate_returns_new_state(self):
        gs = _make_game()
        old_id = id(gs)
        gs = apply_proliferate(gs, ["perm-1"])
        assert id(gs) != old_id
    
    def test_setup_pending_returns_new_state(self):
        gs = _make_game()
        old_id = id(gs)
        gs = setup_pending_proliferate(gs, "Alice")
        assert id(gs) != old_id

class TestStackIntegration:
    """Test that card effects trigger proliferate via stack resolution."""
    
    def test_human_player_gets_pending_choice(self):
        """Human player casting a proliferate spell gets pending choice."""
        gs = _make_game()
        gs.human_player_name = "Alice"
        
        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")
        
        assert gs.pending_proliferate_choice is not None
        assert gs.pending_proliferate_choice["player"] == "Alice"
    
    def test_ai_player_auto_resolves(self):
        """AI player casting a proliferate spell auto-resolves."""
        gs = _make_game()
        gs.human_player_name = None  # AI
        
        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Proliferate."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Proliferate.")
        
        assert gs.pending_proliferate_choice is None  # Auto-resolved
        # Alice's perm should have gained a counter
        perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert perm.counters["charge"] == 4

class TestTriggerFiring:
    """Test that 'whenever you proliferate' triggers fire after resolution."""
    
    def test_proliferated_trigger_fires(self):
        from mtg_engine.engine.triggers import check_proliferated_triggers
        
        flux = Permanent(
            id="flux-1",
            card=Card(name="Flux Channeler", type_line="Creature — Elemental", 
                     oracle_text="Whenever you proliferate, draw a card.",
                     power="2", toughness="2"),
            controller="Alice",
        )
        gs = _make_game()
        gs.battlefield.append(flux)
        
        hand_before = len(gs.players[0].hand)
        gs = apply_proliferate(gs, ["perm-1"])
        gs = check_proliferated_triggers(gs, "Alice")
        
        # Check for proliferated trigger in pending triggers
        prolif_triggers = [t for t in gs.pending_triggers if t.trigger_type == "proliferated"]
        assert len(prolif_triggers) >= 1

class TestInternalCounterExclusion:
    """Test that internal engine counters are not eligible."""
    
    def test_internal_counters_not_eligible(self):
        perm = Permanent(
            id="perm-int", 
            card=Card(name="Deathtouch Creature", type_line="Creature — Zombie",
                     power="2", toughness="2"),
            controller="Alice",
            counters={"__deathtouch_damage__": 5},
        )
        gs = _make_game()
        gs.battlefield.append(perm)
        
        eligible = get_proliferate_eligible(gs)
        eligible_ids = [e["id"] for e in eligible]
        assert "perm-int" not in eligible_ids

class TestMultipleCounterTypes:
    """Test that all counter types on a permanent increment."""
    
    def test_all_counter_types_increment(self):
        perm = Permanent(
            id="multi", 
            card=Card(name="Multi Counter", type_line="Creature — Beast",
                     power="2", toughness="2"),
            controller="Alice",
            counters={"charge": 3, "+1/+1": 1, "lore": 2},
        )
        gs = _make_game()
        gs.battlefield.append(perm)
        
        gs = apply_proliferate(gs, ["multi"])
        multi_perm = next(p for p in gs.battlefield if p.id == "multi")
        assert multi_perm.counters["charge"] == 4
        assert multi_perm.counters["+1/+1"] == 2
        assert multi_perm.counters["lore"] == 3

class TestPoisonCounterProliferation:
    """Test poison counter proliferation on players."""
    
    def test_poison_counter_increments(self):
        gs = _make_game()
        gs = apply_proliferate(gs, ["Alice"])
        
        alice = next(p for p in gs.players if p.name == "Alice")
        assert alice.poison_counters == 3  # Was 2, now 3
    
    def test_poison_counter_increments_via_api_pattern(self):
        """Simulate API handler calling apply_proliferate with player target."""
        gs = _make_game()
        gs = apply_proliferate(gs, ["Bob"])
        
        bob = next(p for p in gs.players if p.name == "Bob")
        assert bob.poison_counters == 2  # Was 1, now 2

class TestAIHeuristic:
    """Test AI auto-resolution heuristic."""
    
    def test_ai_proliferates_to_own_targets_only(self):
        gs = _make_game()
        old_id = id(gs)
        gs = _resolve_proliferate_with_ai(gs, "Alice")
        
        assert id(gs) != old_id  # Pure transform
        # Alice's perm should have gained counter
        alice_perm = next(p for p in gs.battlefield if p.id == "perm-1")
        assert alice_perm.counters["charge"] == 4
        # Alice herself (poison) should also be proliferated
        alice_player = next(p for p in gs.players if p.name == "Alice")
        assert alice_player.poison_counters == 3

class TestEmptyTargets:
    """Test edge cases with no eligible targets."""
    
    def test_no_eligible_targets_is_safe(self):
        gs = GameState(
            game_id="test-empty", seed=1, turn=1,
            active_player="Alice", priority_holder="Alice",
            players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
            battlefield=[],
        )
        eligible = get_proliferate_eligible(gs)
        assert eligible == []
        
        # Applying to empty list should be safe (no-op)
        gs2 = apply_proliferate(gs, [])
        assert gs2 is not None

## Potential Risks

1. **Risk**: Mutability fix in `apply_proliferate()` changes battlefield/player references → existing tests that hold references to old perm objects see stale data → **Mitigation**: All callers already reassign `gs = apply_proliferate(gs, ...)`. Update test assertions to read from the returned GameState's battlefield list.

2. **Risk**: Removing `_trigger_proliferate()` from stack.py breaks existing tests that import it directly → **Mitigation**: Check imports in `tests/test_019/test_rules_engine_gap_closure.py` (line 17). Update those tests to use `proliferate.setup_pending_proliferate()` instead.

3. **Risk**: AI heuristic of "proliferate to all own targets" may be suboptimal for some strategies → **Mitigation**: This is MVP behavior. Future enhancement could add smarter heuristics (e.g., prioritize permanents with +1/+1 counters over charge counters). The heuristic is correct per CR 701.27 — it's legal to choose any subset, and choosing all own targets is a reasonable default.

4. **Risk**: `check_proliferated_triggers()` fires triggers but they may not resolve in the same turn → **Mitigation**: Triggers are added to `pending_triggers` list; resolution happens when priority is passed and stack processes them. This matches how all other triggered abilities work in this engine.

5. **Risk**: API handler change (delegating to `apply_proliferate`) may affect dry_run behavior → **Mitigation**: The endpoint already creates a snapshot for dry_run (`gs = mgr.snapshot(game_id)`). Since `apply_proliferate()` returns a new GameState, the original is untouched. Dry run still works correctly.

6. **Risk**: Internal counter filtering in stack.py was previously missing — removing `_trigger_proliferate` and using `setup_pending_proliferate` fixes this but may change behavior for edge cases → **Mitigation**: This is a bug fix, not a breaking change. Internal counters should never have been eligible targets.

## Handoff to Developer

**Design Document**: Above
**Estimated Complexity**: Low — most infrastructure exists (stack integration, API endpoint, legal actions, trigger checking), just needs mutability fixes and code consolidation
**Key Files**: 
1. `mtg_engine/engine/proliferate.py` — Fix 3 mutability bugs + add AI resolution function (biggest change)
2. `mtg_engine/engine/stack.py` — Delete `_trigger_proliferate()`, wire to proliferate module
3. `mtg_engine/api/routers/game.py` — Delegate to engine functions, fire triggers after resolution
4. `tests/engine/test_proliferate_integration.py` — New integration test file

**Start With**: Task 1 (fix mutability in `engine/proliferate.py`) — this unblocks all other tasks since the pure transform pattern is foundational. Then run existing tests to confirm no regressions before proceeding.

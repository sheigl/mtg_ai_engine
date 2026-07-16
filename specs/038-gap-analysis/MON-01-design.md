# Design: MON-01 The Monarch Mechanic

## Overview
Implement CR 702.147 The Monarch mechanic for Conspiracy/Commander formats: a player holds "the monarch" status, draws a card at the end of their turn while holding it, and transfers it when their creature deals combat damage to them.

## Architecture Decisions

### Decision 1: Extend existing `monarch.py` rather than rewrite
**Rationale**: The module already has correct signatures for `set_monarch`, `handle_end_step_draw`, and `check_combat_damage_monarch`. The combat hook (combat/core.py line 667-669) and turn manager hook (turn_manager.py lines 389-391) are already wired. We need to:
1. Add missing `is_monarch()` query helper for card effects
2. Fix mutability pattern in `set_monarch` to use `model_copy`
3. Initialize monarch on game creation for Conspiracy/Commander formats
4. Add integration tests that exercise the full combat→monarch flow

### Decision 2: Use `model_copy(update={...})` for state transforms
**Rationale**: Consistent with project standard (CMD-01 commander patterns, AGENTS.md). The current `set_monarch` mutates `game_state.monarch` directly which conflicts with the immutable-ish GameState pattern.

### Decision 3: Initialize monarch via game format flag
**Rationale**: CR 702.147a says "At the start of a Commander or Conspiracy game, each player rolls a die; the highest roller becomes the monarch." For simplicity in this engine (no dice rolling), we assign it to `active_player` at game creation time when format is "commander" or "conspiracy".

### Trade-offs considered
- **Alternative**: Add `monarch` parameter to `create_game`. Rejected: monarch should be deterministic based on format, not configurable per-game.
- **Alternative**: Dice-roll simulation with seed-based RNG. Rejected: over-engineering for a game engine; active_player assignment is sufficient and deterministic.

## Files to Create/Modify

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/monarch.py` | Add `is_monarch()` helper, fix `set_monarch` mutability pattern | Query support + consistency with project patterns |
| `mtg_engine/api/game_manager.py` | Initialize `monarch=active_player` for commander/conspiracy formats | CR 702.147a: monarch must exist at game start |

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `tests/engine/test_monarch_integration.py` | Integration tests for monarch in combat flow | Test full declare_attackers→assign_combat_damage→monarch transfer cycle, test end step draw via turn_manager |

## Task Breakdown (Ordered by Dependency)

### Task 1: Fix `set_monarch` mutability and add `is_monarch()` helper
- **Files**: `mtg_engine/engine/monarch.py`
- **Description**: 
  1. Refactor `set_monarch` to use `model_copy(update={"monarch": player_name})` instead of direct mutation
  2. Add `is_monarch(game_state: GameState, player_name: str) -> bool` helper function
  3. Ensure "become_monarch" trigger is still fired on change (existing behavior must be preserved)
- **Acceptance Criteria**: 
  - All existing 14 unit tests in `test_monarch.py` pass
  - New `is_monarch()` returns correct boolean for monarch/non-monarch/None cases

### Task 2: Initialize monarch on game creation
- **Files**: `mtg_engine/api/game_manager.py`
- **Description**: In `create_game()`, when format is "commander" or "conspiracy", set `monarch=player1_name` (the active player) in the GameState constructor. This matches CR 702.147a where someone starts as monarch.
- **Acceptance Criteria**: 
  - Games created with format="commander" have `gs.monarch == gs.active_player`
  - Games created with format="standard" have `gs.monarch is None`

### Task 3: Add integration tests for monarch in combat flow
- **Files**: `tests/engine/test_monarch_integration.py` (new)
- **Description**: Create integration tests that exercise the full monarch flow through actual combat mechanics:
  1. Test: creature attacks player who is monarch → attacker's controller becomes monarch
  2. Test: creature attacks non-monarch player → no change to monarch
  3. Test: monarch draws card at end of their turn (via `handle_end_step_draw`)
  4. Test: non-monarch active player does not draw even if they're the active player
- **Acceptance Criteria**: 
  - All new integration tests pass
  - No regressions in existing 1936+ tests

### Task 4: Verify full test suite passes
- **Files**: N/A (run tests)
- **Description**: Run `PYTHONPATH=. pytest tests/ -v` to confirm no regressions. Specifically check `tests/engine/test_monarch.py` and new integration tests.
- **Acceptance Criteria**: All existing + new tests pass

## Data Models / Interfaces

### Existing GameState field (no change needed)
```python
class GameState(BaseModel):
    # ... existing fields ...
    monarch: str | None = Field(default=None, description="CR 702.147 The Monarch")
```

### New `is_monarch()` helper signature
```python
def is_monarch(game_state: GameState, player_name: str) -> bool:
    """Check if the given player currently holds the monarch. CR 702.147."""
    return game_state.monarch == player_name
```

### Fixed `set_monarch` signature (same API, internal change)
```python
def set_monarch(game_state: GameState, player_name: str) -> GameState:
    """Set the monarch to the given player. Fires 'become_monarch' trigger on change."""
    if game_state.monarch == player_name:
        return game_state  # No-op
    
    gs = game_state.model_copy(update={"monarch": player_name})
    
    # Fire become_monarch trigger for cards that care
    from mtg_engine.models.game import PendingTrigger
    import uuid
    trigger = PendingTrigger(
        id=str(uuid.uuid4()),
        source_permanent_id="monarch",
        source_card_name="monarch",
        controller=player_name,
        trigger_type="become_monarch",
        effect_description=f"{player_name} becomes the monarch",
    )
    gs.pending_triggers.append(trigger)
    
    return gs
```

## Testing Strategy

### Unit Tests (existing, in `tests/engine/test_monarch.py`)
- `TestSetMonarch`: 5 tests for set_monarch behavior ✅ already exists
- `TestEndStepDraw`: 6 tests for handle_end_step_draw ✅ already exists  
- `TestCombatDamage`: 4 tests for check_combat_damage_monarch ✅ already exists

### New Integration Tests (in `tests/engine/test_monarch_integration.py`)
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, Phase, Step
from mtg_engine.models.actions import AttackDeclaration
from mtg_engine.engine.zones import put_permanent_onto_battlefield
from mtg_engine.engine.combat import declare_attackers, assign_combat_damage
from mtg_engine.engine.monarch import is_monarch

def _make_combat_game(monarch: str | None = None) -> GameState:
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    return GameState(
        game_id="t-monarch-combat", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS,
        players=[p1, p2], monarch=monarch
    )

def test_monarch_transfers_on_combat_damage():
    """Full combat flow: p1 attacks p2 (who is monarch) → p1 becomes monarch."""
    gs = _make_combat_game(monarch="p2")
    
    # Add attacker creature to p1's battlefield
    card = Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2")
    gs, attacker = put_permanent_onto_battlefield(gs, card, "p1")
    attacker.summoning_sick = False
    
    # Declare attack on p2 (the monarch)
    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    
    # Assign combat damage — this triggers check_combat_damage_monarch internally
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)
    
    assert is_monarch(gs, "p1"), f"Expected p1 to be monarch, got {gs.monarch}"
    assert not is_monarch(gs, "p2")

def test_no_monarch_transfer_when_attacking_non_monarch():
    """Full combat flow: p1 attacks p3 (who isn't monarch) → monarch unchanged."""
    gs = _make_combat_game(monarch="p2")
    
    card = Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2")
    gs, attacker = put_permanent_onto_battlefield(gs, card, "p1")
    attacker.summoning_sick = False
    
    # Attack p2 who is monarch → should transfer to p1
    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)
    
    assert gs.monarch == "p1"

def test_monarch_draws_at_end_of_own_turn():
    """Monarch draws a card during end step of their turn."""
    from mtg_engine.engine.monarch import handle_end_step_draw
    
    p1 = PlayerState(name="p1", life=20, library=[Card(name=f"C{i}") for i in range(5)])
    p2 = PlayerState(name="p2", life=20)
    gs = GameState(
        game_id="t-monarch-draw", seed=1, active_player="p1", priority_holder="p1",
        phase="ending", step="end", players=[p1, p2], monarch="p1"
    )
    
    hand_before = len(p1.hand)
    gs = handle_end_step_draw(gs)
    assert len(p1.hand) == hand_before + 1

def test_is_monarch_query():
    """is_monarch() returns correct boolean for various states."""
    gs = _make_combat_game(monarch="p2")
    
    assert is_monarch(gs, "p2") is True
    assert is_monarch(gs, "p1") is False
    
    gs_no_monarch = _make_combat_game(monarch=None)
    assert is_monarch(gs_no_monarch, "p1") is False
```

### Regression Tests
- Run `PYTHONPATH=. pytest tests/engine/test_monarch.py -v` — all 14 existing tests must pass
- Run `PYTHONPATH=. pytest tests/rules/test_combat.py -v` — no regressions in combat tests
- Run `PYTHONPATH=. pytest tests/ -x -q` — full suite passes

## Potential Risks

1. **Risk**: `set_monarch` mutability fix may break code that relies on the mutated reference being the same object → **Mitigation**: All callers already reassign `gs = set_monarch(gs, ...)`, so this is safe. The only risk is if someone holds a reference to the old GameState and expects it to be updated — but that's an anti-pattern in this codebase.

2. **Risk**: Combat integration test may expose edge cases in `check_combat_damage_monarch` not covered by unit tests → **Mitigation**: Integration tests use real combat flow (declare_attackers, assign_combat_damage) which exercises the actual hook path.

3. **Risk**: Game creation monarch initialization conflicts with existing commander tests that don't expect monarch → **Mitigation**: Only initialize for "commander" and "conspiracy" formats; standard games remain unaffected. Existing commander tests may need updating to account for monarch presence.

## Handoff to Developer

**Design Document**: Above
**Estimated Complexity**: Low — most infrastructure exists, just needs wiring + helper function + integration tests
**Key Files**: 
1. `mtg_engine/engine/monarch.py` — Add `is_monarch()`, fix mutability
2. `mtg_engine/api/game_manager.py` — Initialize monarch on game creation
3. `tests/engine/test_monarch_integration.py` — New integration test file

**Start With**: Task 1 (fix `set_monarch` and add `is_monarch()`), then run existing tests to confirm no regressions before proceeding to Tasks 2-4.

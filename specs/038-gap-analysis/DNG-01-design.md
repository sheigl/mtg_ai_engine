# Design: DNG-01 Day/Night Cycle Mutability Fix

## Overview
Fix critical mutability violations in `mtg_engine/engine/daynight.py` and related turn_manager code. All functions currently mutate `GameState` (and its nested objects) directly instead of returning new state via `model_copy`. This violates the project's immutable-ish GameState pattern established by CMD-01, MON-01, VEN-01, and PRO-01.

## Architecture Decisions

### Decision 1: Fix all mutability in `daynight.py` to use `model_copy(update={...})`
**Rationale**: Consistent with project standard (see AGENTS.md, MON-01 pattern). The current code has 5 functions that directly mutate GameState fields (`is_day`, `pending_triggers`) and nested objects (`Permanent.face_index`). All must be converted to pure transforms.

### Decision 2: `_transform_daybound_permanents()` returns new battlefield list with transformed Permanents
**Rationale**: The function currently mutates `perm.face_index` in-place on permanents living in the shared `game_state.battlefield` list. Following MON-01/CMD-01 patterns, we build a new list where matching permanents are replaced via `model_copy(update={"face_index": new_face})`.

### Decision 3: `_add_daynight_trigger()` returns new pending_triggers list
**Rationale**: Currently appends directly to `game_state.pending_triggers` (shared mutable list). Following MON-01 pattern, we build a new list with the trigger appended.

### Decision 4: Fix turn_manager.py snapshot mutations in `_advance_turn()` and `begin_step()`
**Rationale**: Lines 515-526 of `_advance_turn()` directly mutate spell counters and phase flags on GameState. The untap step (lines 130-137) mutates permanent fields and player state. These must use the same model_copy pattern.

### Trade-offs considered
- **Alternative**: Deep-copy entire GameState at start of each function. Rejected: `model_copy(update={...})` is more explicit about what changed, matches project patterns, and avoids unnecessary deep copies of unchanged data.
- **Alternative**: Change return type to `(GameState, bool)` indicating whether transition occurred. Rejected: Inconsistent with MON-01/CMD-01 pattern where functions always return GameState (possibly unchanged).

## Files to Create/Modify

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/daynight.py` | Fix all 5 functions for pure transforms via model_copy | Core mutability violations |
| `mtg_engine/engine/turn_manager.py` (lines 513-526) | Replace direct mutations in `_advance_turn()` with model_copy | Snapshot mutations on spell counters and phase flags |
| `mtg_engine/engine/turn_manager.py` (lines 129-143) | Fix untap step permanent/player mutations to use model_copy | Permanent field mutations during begin_step(UNTAP) |

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `tests/engine/test_daynight_integration.py` | Integration tests for day/night cycle through full turn flow | Test transition via begin_step, test spell tracking across turns, test permanent transform immutability |

## Task Breakdown (Ordered by Dependency)

### Task 1: Fix `_transform_daybound_permanents()` to return new battlefield list
- **Files**: `mtg_engine/engine/daynight.py`
- **Description**: 
  1. Change signature from `(game_state: GameState) -> None` to `(game_state: GameState) -> list[Permanent]`
  2. Build a new list; for permanents with daybound/nightbound, create `perm.model_copy(update={"face_index": new_face})`; for others, keep reference (shallow copy is fine since we're not mutating them)
- **Acceptance Criteria**: 
  - Function returns a new list object (`id(new_list) != id(old_list)`)
  - Transformed permanents are new objects with correct `face_index`
  - Non-matching permanents remain unchanged

**Pattern:**
```python
def _transform_daybound_permanents(game_state: GameState) -> list[Permanent]:
    """Transform all daybound/nightbound permanents. Returns NEW battlefield list."""
    from mtg_engine.models.game import Permanent
    
    new_battlefield = []
    for perm in game_state.battlefield:
        card = perm.card
        oracle = (card.oracle_text or "").lower()
        type_line = (card.type_line or "").lower()

        has_daybound = "daybound" in oracle or "daybound" in type_line
        has_nightbound = "nightbound" in oracle or "nightbound" in type_line
        
        if not has_daybound and not has_nightbound:
            new_battlefield.append(perm)
            continue

        # DFC with back face — flip it
        if card.faces and len(card.faces) > 1:
            current_face = getattr(perm, "face_index", 0)
            new_face = 1 if current_face == 0 else 0
            new_perm = perm.model_copy(update={"face_index": new_face})
            logger.info("Day/Night transform: %s face %d → %d", card.name, current_face, new_face)
            new_battlefield.append(new_perm)
        else:
            # Has keyword but no faces — keep as-is (shouldn't happen in practice)
            new_battlefield.append(perm)

    return new_battlefield
```

### Task 2: Fix `_add_daynight_trigger()` to return new pending_triggers list
- **Files**: `mtg_engine/engine/daynight.py`
- **Description**: 
  1. Change signature from `(game_state, transition_type) -> None` to `(transition_type: str) -> PendingTrigger`
  2. Return a single trigger object instead of appending to the shared list
  3. Callers will handle adding it to new pending_triggers via model_copy
- **Acceptance Criteria**: 
  - Function returns a `PendingTrigger` instance (not None, not mutating anything)

**Pattern:**
```python
def _create_daynight_trigger(transition_type: str) -> PendingTrigger:
    """Create a pending trigger for day/night transition events. Pure function."""
    from mtg_engine.models.game import PendingTrigger
    
    return PendingTrigger(
        source_permanent_id="@@daynight_system@@",
        source_card_name="@@daynight_system@@",
        controller="@@system@@",
        trigger_type=f"day_time_changes_{transition_type}",
        effect_description=f"Day/night transition: {transition_type}",
    )
```

### Task 3: Fix `check_daynight_transition()` to use model_copy
- **Files**: `mtg_engine/engine/daynight.py`
- **Description**: 
  1. Build update dict with only changed fields (`is_day`, `battlefield`, `pending_triggers`)
  2. Use `_transform_daybound_permanents()` result for new battlefield list
  3. Append trigger to new pending_triggers list via `[...gs.pending_triggers, _create_daynight_trigger(...)]`
- **Acceptance Criteria**: 
  - Returns a new GameState object when transition occurs (`id(new_gs) != id(old_gs)`)
  - Original GameState is unchanged after call
  - All existing unit tests in `test_daynight.py` still pass

**Pattern:**
```python
def check_daynight_transition(game_state: GameState) -> GameState:
    """Check and apply day/night transition (CR 730.2). Returns new GameState."""
    prev_casts = game_state.spells_cast_last_turn
    
    if game_state.is_day is None:
        return game_state  # No transition possible when neither day nor night

    if game_state.is_day:
        # Day → Night: active player of previous turn cast no spells
        if prev_casts == 0:
            logger.info("Day → Night transition (0 spells cast last turn)")
            new_battlefield = _transform_daybound_permanents(game_state)
            trigger = _create_daynight_trigger("day_to_night")
            return game_state.model_copy(update={
                "is_day": False,
                "battlefield": new_battlefield,
                "pending_triggers": [*game_state.pending_triggers, trigger],
            })
    else:
        # Night → Day: active player of previous turn cast 2+ spells
        if prev_casts >= 2:
            logger.info("Night → Day transition (2+ spells cast last turn)")
            new_battlefield = _transform_daybound_permanents(game_state)
            trigger = _create_daynight_trigger("night_to_day")
            return game_state.model_copy(update={
                "is_day": True,
                "battlefield": new_battlefield,
                "pending_triggers": [*game_state.pending_triggers, trigger],
            })

    return game_state  # No transition — return original (same object is fine)
```

### Task 4: Fix `set_day()` and `set_night()` to use model_copy
- **Files**: `mtg_engine/engine/daynight.py`
- **Description**: 
  1. Replace direct `game_state.is_day = True/False` with model_copy
  2. Use `_create_daynight_trigger()` and append to new pending_triggers list
- **Acceptance Criteria**: 
  - Returns new GameState when change occurs
  - Original GameState is unchanged

**Pattern:**
```python
def set_day(game_state: GameState) -> GameState:
    """Explicitly set the game to day. Returns new GameState if changed."""
    if game_state.is_day is not True:
        logger.info("Day explicitly set")
        trigger = _create_daynight_trigger("set_to_day")
        return game_state.model_copy(update={
            "is_day": True,
            "pending_triggers": [*game_state.pending_triggers, trigger],
        })
    return game_state


def set_night(game_state: GameState) -> GameState:
    """Explicitly set the game to night. Returns new GameState if changed."""
    if game_state.is_day is not False:
        logger.info("Night explicitly set")
        trigger = _create_daynight_trigger("set_to_night")
        return game_state.model_copy(update={
            "is_day": False,
            "pending_triggers": [*game_state.pending_triggers, trigger],
        })
    return game_state
```

### Task 5: Fix `_advance_turn()` snapshot mutations in turn_manager.py
- **Files**: `mtg_engine/engine/turn_manager.py` (lines 513-526)
- **Description**: Replace direct field mutations with model_copy. The spell counter snapshot, active player change, and phase flag clear must all be done via a single model_copy call.

**Current code (mutating):**
```python
# Lines 513-526 — ALL MUTATE DIRECTLY
prev_active = game_state.active_player
game_state.spells_cast_last_turn = \
    game_state.spells_cast_this_turn_by_player.get(prev_active, 0)
game_state.spells_cast_this_turn = 0
game_state.spells_cast_this_turn_by_player.clear()

game_state.active_player = next_player
game_state.priority_holder = next_player
game_state.turn += 1
game_state.phase = Phase.BEGINNING
game_state.step = Step.UNTAP
game_state.phase_skip_flags.clear()
```

**Fixed code (pure):**
```python
# Lines 513-526 — PURE TRANSFORM via model_copy
prev_active = game_state.active_player
gs = game_state.model_copy(update={
    "spells_cast_last_turn": game_state.spells_cast_this_turn_by_player.get(prev_active, 0),
    "spells_cast_this_turn": 0,
    "spells_cast_this_turn_by_player": {},
    "active_player": next_player,
    "priority_holder": next_player,
    "turn": game_state.turn + 1,
    "phase": Phase.BEGINNING,
    "step": Step.UNTAP,
    "phase_skip_flags": set(),
})
```

### Task 6: Fix `begin_step()` untap section mutations in turn_manager.py
- **Files**: `mtg_engine/engine/turn_manager.py` (lines 129-143)
- **Description**: The untap step currently mutates permanent fields (`tapped`, `summoning_sick`, `loyalty_activated_this_turn`) and player state (`lands_played_this_turn`). These must use model_copy pattern.

**Current code (mutating):**
```python
# Lines 129-143 — ALL MUTATE DIRECTLY
for perm in game_state.battlefield:
    if perm.controller == game_state.active_player:
        perm.tapped = False
        perm.summoning_sick = False
        perm.loyalty_activated_this_turn = False
active = get_player(game_state, game_state.active_player)
active.lands_played_this_turn = 0
if game_state.is_day is not None:
    from mtg_engine.engine.daynight import check_daynight_transition
    game_state = check_daynight_transition(game_state)
```

**Fixed code (pure):**
```python
# Lines 129-143 — PURE TRANSFORM via model_copy
new_battlefield = []
for perm in game_state.battlefield:
    if perm.controller == game_state.active_player:
        new_perm = perm.model_copy(update={
            "tapped": False,
            "summoning_sick": False,
            "loyalty_activated_this_turn": False,
        })
        new_battlefield.append(new_perm)
    else:
        new_battlefield.append(perm)

# Reset lands played for active player (new PlayerState via model_copy)
active = get_player(game_state, game_state.active_player)
new_active = active.model_copy(update={"lands_played_this_turn": 0})
new_players = [
    new_active if p.name == game_state.active_player else p
    for p in game_state.players
]

gs = game_state.model_copy(update={
    "battlefield": new_battlefield,
    "players": new_players,
})

# DNG-01: Day/Night transition check (CR 730.2 — second part of untap step)
if gs.is_day is not None:
    from mtg_engine.engine.daynight import check_daynight_transition
    gs = check_daynight_transition(gs)

return gs
```

### Task 7: Update existing unit tests to verify immutability
- **Files**: `tests/engine/test_daynight.py`
- **Description**: Add assertions that original GameState is unchanged after calls. This catches future regressions.
- **Acceptance Criteria**: 
  - All 18 existing tests still pass
  - New immutability assertions added to key test cases

**Pattern:**
```python
def test_day_to_night_does_not_mutate_original(self):
    gs = _gs(is_day=True, prev_casts=0)
    original_id = id(gs)
    original_is_day = gs.is_day
    
    new_gs = check_daynight_transition(gs)
    
    # Original state unchanged
    assert id(new_gs) != original_id
    assert gs.is_day is original_is_day  # Still True on original

def test_transform_does_not_mutate_permanent(self):
    """Transformed permanent should be a different object."""
    from mtg_engine.models.game import CardFace, Permanent
    card = _make_card(
        "Daybound Creature",
        type_line="Creature — Werewolf",
        oracle_text="Daybound (If a player casts no spells during their turn, it becomes night.)",
    )
    card.faces = [
        CardFace(name="Day Face", type_line="Creature", oracle_text="Day side"),
        CardFace(name="Night Face", type_line="Creature", oracle_text="Night side"),
    ]
    perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)
    
    gs = _gs(is_day=True, prev_casts=0)
    gs.battlefield = [perm]
    original_perm_id = id(perm)
    
    new_gs = check_daynight_transition(gs)
    
    # Original permanent unchanged
    assert perm.face_index == 0
    # New battlefield has a different permanent object for the transformed one
    new_perm = new_gs.battlefield[0]
    assert id(new_perm) != original_perm_id
    assert new_perm.face_index == 1
```

### Task 8: Create integration test suite
- **Files**: `tests/engine/test_daynight_integration.py` (new)
- **Description**: Integration tests exercising the full day/night cycle through turn_manager flows. See Testing Strategy section below for complete test list.
- **Acceptance Criteria**: All new integration tests pass, no regressions in existing 2089+ tests

## Data Models / Interfaces

### Existing GameState fields (no changes needed)
```python
class GameState(BaseModel):
    # ... existing fields ...
    spells_cast_this_turn: int = 0
    spells_cast_this_turn_by_player: dict[str, int] = Field(default_factory=dict)
    spells_cast_last_turn: int = 0
    is_day: Optional[bool] = None  # None=neither, True=day, False=night
```

### Fixed function signatures (same API, internal change to pure transforms)
```python
def check_daynight_transition(game_state: GameState) -> GameState: ...
def set_day(game_state: GameState) -> GameState: ...
def set_night(game_state: GameState) -> GameState: ...
def is_daytime(game_state: GameState) -> Optional[bool]: ...  # Already pure (read-only)

# Internal helpers — changed signatures:
def _transform_daybound_permanents(game_state: GameState) -> list[Permanent]: ...
def _create_daynight_trigger(transition_type: str) -> PendingTrigger: ...
```

## Testing Strategy

### Unit Tests (existing, in `tests/engine/test_daynight.py`)
- `TestDayNightTransitions`: 10 tests for transition logic ✅ already exists — add immutability assertions
- `TestSetExplicit`: 4 tests for set_day/set_night ✅ already exists — add immutability assertions
- `TestDayboundTransform`: 2 tests for DFC transform ✅ already exists — add object identity checks
- `TestSpellTracking`: 2 tests for spell counter tracking ✅ already exists

### New Integration Tests (in `tests/engine/test_daynight_integration.py`)

```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, Phase, Step, CardFace, Permanent
from mtg_engine.engine.turn_manager import begin_step, _advance_turn
from mtg_engine.engine.daynight import check_daynight_transition, set_day, is_daytime


def _make_game(is_day=None, spells_last=0) -> GameState:
    p1 = PlayerState(name="p1", library=[Card(name=f"C{i}") for i in range(20)])
    p2 = PlayerState(name="p2", library=[Card(name=f"C{i}") for i in range(20)])
    return GameState(
        game_id="test-dng-integration", seed=1,
        active_player="p1", priority_holder="p1",
        phase=Phase.BEGINNING, step=Step.UNTAP,
        players=[p1, p2],
        is_day=is_day,
        spells_cast_last_turn=spells_last,
    )


class TestDayNightViaTurnManager:
    """Test day/night transitions through the full turn_manager flow."""

    def test_untap_triggers_day_to_night(self):
        """When it's day and prev player cast 0 spells, untap triggers night transition."""
        gs = _make_game(is_day=True, spells_last=0)
        new_gs = begin_step(gs)
        assert is_daytime(new_gs) is False

    def test_untap_triggers_night_to_day(self):
        """When it's night and prev player cast 2+ spells, untap triggers day transition."""
        gs = _make_game(is_day=False, spells_last=3)
        new_gs = begin_step(gs)
        assert is_daytime(new_gs) is True

    def test_untap_no_transition_when_neither(self):
        """When is_day=None, no transition occurs during untap."""
        gs = _make_game(is_day=None, spells_last=0)
        new_gs = begin_step(gs)
        assert is_daytime(new_gs) is None

    def test_advance_turn_snapshots_spell_count(self):
        """_advance_turn captures previous player's spell count for day/night."""
        gs = _make_game(is_day=True, spells_last=0)
        gs.spells_cast_this_turn_by_player["p1"] = 3
        
        new_gs = _advance_turn(gs)
        
        # Snapshot should capture p1's count (prev active player)
        assert new_gs.spells_cast_last_turn == 3
        # Counters reset for new turn
        assert new_gs.spells_cast_this_turn == 0
        assert new_gs.spells_cast_this_turn_by_player == {}

    def test_advance_turn_does_not_mutate_original(self):
        """_advance_turn returns new GameState, original unchanged."""
        gs = _make_game(is_day=True)
        gs.spells_cast_this_turn = 5
        
        old_id = id(gs)
        new_gs = _advance_turn(gs)
        
        assert id(new_gs) != old_id
        assert gs.spells_cast_this_turn == 5  # Original unchanged


class TestPermanentTransformImmutability:
    """Test that daybound transforms don't mutate original permanents."""

    def test_transform_creates_new_permanent(self):
        """Daybound permanent gets a new object with flipped face_index."""
        card = Card(
            name="Daybound Wolf", type_line="Creature — Werewolf",
            oracle_text="Daybound (If a player casts no spells during their turn, it becomes night.)",
        )
        card.faces = [
            CardFace(name="Wolf", type_line="Creature", oracle_text=""),
            CardFace(name="Werewolf", type_line="Creature", oracle_text=""),
        ]
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)

        gs = _make_game(is_day=True, spells_last=0)
        gs.battlefield = [perm]
        
        new_gs = begin_step(gs)  # Goes through untap → check_daynight_transition
        
        assert perm.face_index == 0  # Original unchanged
        assert new_gs.battlefield[0].face_index == 1  # New object flipped

    def test_non_daybound_permanent_unchanged(self):
        """Regular permanents are not affected by day/night transition."""
        card = Card(name="Grizzly Bears", type_line="Creature — Bear")
        perm = Permanent(id="perm_1", card=card, controller="p1", face_index=0)

        gs = _make_game(is_day=True, spells_last=0)
        gs.battlefield = [perm]
        
        new_gs = begin_step(gs)
        
        # Same object reference (no transform needed)
        assert new_gs.battlefield[0] is perm


class TestFullDayNightCycle:
    """Test complete day→night→day cycle across turns."""

    def test_day_to_night_cycle(self):
        """Day → Night when 0 spells cast, then stays night until 2+ spells."""
        gs = _make_game(is_day=True, spells_last=0)
        
        # Turn 1: Day → Night (prev player cast 0)
        gs = begin_step(gs)
        assert is_daytime(gs) is False
        
        # Simulate p2 casting 0 spells on their turn
        gs.spells_cast_this_turn_by_player["p2"] = 0
        gs = _advance_turn(gs)
        
        # Turn 2: Night stays night (prev player cast 0, need 2+)
        gs = begin_step(gs)
        assert is_daytime(gs) is False

    def test_night_to_day_cycle(self):
        """Night → Day when 2+ spells cast."""
        gs = _make_game(is_day=False, spells_last=3)
        
        # Turn 1: Night → Day (prev player cast 3)
        gs = begin_step(gs)
        assert is_daytime(gs) is True
        
        # Simulate p1 casting 0 spells on their turn
        gs.spells_cast_this_turn_by_player["p1"] = 0
        gs = _advance_turn(gs)
        
        # Turn 2: Day → Night (prev player cast 0)
        gs = begin_step(gs)
        assert is_daytime(gs) is False

    def test_full_round_trip(self):
        """Day → Night → Day → Night across multiple turns."""
        gs = _make_game(is_day=True, spells_last=0)
        
        # Day → Night (0 spells)
        gs = begin_step(gs)
        assert is_daytime(gs) is False
        
        # Cast 3 spells this turn
        gs.spells_cast_this_turn_by_player["p2"] = 3
        gs = _advance_turn(gs)
        
        # Night → Day (3 spells)
        gs = begin_step(gs)
        assert is_daytime(gs) is True
        
        # Cast 0 spells this turn
        gs.spells_cast_this_turn_by_player["p1"] = 0
        gs = _advance_turn(gs)
        
        # Day → Night again (0 spells)
        gs = begin_step(gs)
        assert is_daytime(gs) is False


class TestSetExplicitImmutability:
    """Test that set_day/set_night don't mutate original state."""

    def test_set_day_returns_new_state(self):
        gs = _make_game(is_day=None)
        new_gs = set_day(gs)
        
        assert id(new_gs) != id(gs)
        assert is_daytime(gs) is None  # Original unchanged
        assert is_daytime(new_gs) is True

    def test_set_night_returns_new_state(self):
        gs = _make_game(is_day=None)
        new_gs = set_night(gs)
        
        assert id(new_gs) != id(gs)
        assert is_daytime(gs) is None  # Original unchanged
        assert is_daytime(new_gs) is False


class TestTriggerFiring:
    """Test that day/night triggers are properly added to pending_triggers."""

    def test_transition_adds_trigger_to_new_list(self):
        gs = _make_game(is_day=True, spells_last=0)
        original_triggers = list(gs.pending_triggers)  # Copy
        
        new_gs = check_daynight_transition(gs)
        
        # Original triggers list unchanged
        assert len(gs.pending_triggers) == len(original_triggers)
        # New state has the trigger appended
        assert any("day_to_night" in t.trigger_type for t in new_gs.pending_triggers)
```

### Regression Tests
- Run `PYTHONPATH=. pytest tests/engine/test_daynight.py -v` — all 18 existing tests must pass (with added immutability assertions)
- Run `PYTHONPATH=. pytest tests/rules/test_turn_manager.py -v` — no regressions in turn manager tests
- Run `PYTHONPATH=. pytest tests/ -x -q` — full suite passes

## Potential Risks

1. **Risk**: `_transform_daybound_permanents()` returning a new battlefield list may break code that holds references to individual Permanent objects and expects them to be updated → **Mitigation**: This is the correct immutable pattern; any code relying on mutation is itself buggy. All callers must use the returned GameState's battlefield, not hold old permanent references.

2. **Risk**: The untap step fix in `begin_step()` creates new PlayerState objects via model_copy — existing tests may compare player identity by reference → **Mitigation**: Tests should compare by name or field values, not object identity. Review test assertions that use `is` comparisons on players.

3. **Risk**: `_advance_turn()` now returns a fully new GameState — callers in the API layer must reassign `gs = _advance_turn(gs)` → **Mitigation**: Check all call sites of `_advance_turn()`. The current code at line 528 already does `return game_state`, so callers should be fine. But verify no caller ignores the return value.

4. **Risk**: Pydantic v2 `model_copy` with nested mutable defaults (`pending_triggers`, `battlefield`) — need to ensure we're passing new lists, not references → **Mitigation**: Using `[...gs.pending_triggers, trigger]` creates a new list; same for battlefield. This is correct.

5. **Risk**: The `extra_turns.pop()` on line 507 of `_advance_turn()` still mutates the shared list → **Mitigation**: This should also be fixed to use model_copy with `"extra_turns": game_state.extra_turns[:-1]` (or equivalent). Include this in Task 5.

## Handoff to Developer

**Design Document**: Above
**Estimated Complexity**: Medium — 8 tasks, but each is straightforward model_copy refactoring following established patterns
**Key Files**: 
1. `mtg_engine/engine/daynight.py` — All 5 functions need mutability fixes
2. `mtg_engine/engine/turn_manager.py` (lines 129-143 and 503-528) — Snapshot mutations in `_advance_turn()` and untap step
3. `tests/engine/test_daynight_integration.py` — New integration test file

**Start With**: Task 1 (`_transform_daybound_permanents`) since it's the deepest dependency (called by Tasks 3 and 4), then work up through Tasks 2-6, followed by Tasks 7-8 for tests.

# Design: Sprint 7 P0 — Wire Trigger-Based Keyword Modules

## Overview
Refactor 6 keyword ability modules so their `apply()` methods contain real logic instead of being NOOP stubs, and have engine files call into these modules instead of containing inline logic. This is a **pure code ownership transfer** — no behavior changes.

### User Story Reference
Sprint 7 P0: Wire trigger-based keyword modules (afterlife, undying, persist, evoke, morph, suspend)

## Architecture Decisions

### Decision 1: Keep zone-change listener system intact in triggers.py
- **Why**: The zone-change listener infrastructure (`_register_zone_change_listener`, `_notify_listeners`) is shared by landfall triggers, deathwatch sentinel, and other triggered abilities. Only the afterlife/undying/persist *resolution* logic moves out of stack.py; the *queuing* stays in triggers.py because it's tightly coupled to zone-change event dispatching.
- **Trade-offs considered**: Moving queuing into keyword modules would require each module to register its own listener, fragmenting the zone-change system and making it harder to add new death-triggered keywords.

### Decision 2: Module-level convenience functions as primary API surface
- **Why**: Engine files (stack.py, turn_manager.py) should call `afterlife.resolve_trigger(gs, stack_obj)` not `AfterlifeKeyword().resolve_trigger(gs, perm)`. This matches the existing pattern used by deathtouch/lifelink/infect modules (`apply_deathtouch_damage()`, `apply_lifelink_gain()`).
- **Trade-offs considered**: Instance methods on keyword classes would be more OOP-pure but require engine code to instantiate and configure objects. Module-level functions are simpler for the engine layer and match established patterns.

### Decision 3: Each module exports both instance methods AND module-level wrappers
- **Why**: The `apply()` method on each keyword class contains the core logic (satisfying the user story requirement). Module-level convenience functions delegate to these methods, providing a clean API for callers that don't need to construct keyword instances.
- **Trade-offs considered**: Pure instance-only approach would force every caller to parse oracle text and construct objects. Dual approach gives flexibility.

### Decision 4: Evoke uses `apply()` with mode parameter instead of separate queue/resolve functions
- **Why**: The existing `engine/evoke.py` has two functions (`queue_evoke_sacrifice`, `resolve_evoke_sacrifice`). Consolidating into a single `EvokeKeyword.apply(gs, perm, mode="queue")` unifies the interface. Module-level wrappers maintain backward compatibility for callers.
- **Trade-offs considered**: Keeping separate functions would be simpler but wouldn't satisfy the requirement that `apply()` contains real logic.

### Decision 5: Morph face-down play stays in zones.py; only face-up turns into keyword module
- **Why**: The morph *casting* flow (face-down placement) is tightly coupled to zone management and spell resolution in stack.py/zones.py. Only the *turn face up* action has a clear boundary that maps to `MorphKeyword.apply()`.
- **Trade-offs considered**: Moving all morph logic would require refactoring zones.py's permanent creation, which is high-risk for no behavioral benefit.

### Decision 6: Suspend time counter removal moves into keyword module; auto-cast stays in turn_manager.py
- **Why**: Time counter decrement and "ready to cast" detection are suspend-specific logic that belongs in the keyword module. The actual `cast_spell()` call is a general engine operation that should stay in turn_manager.py's upkeep flow.
- **Trade-offs considered**: Moving auto-cast into SuspendKeyword would couple it to stack.py's cast_spell, creating circular dependencies and making it harder to test independently.

## Files to Create/Modify

### Modified Keyword Module Files (6 files — core changes)

| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/ability/keywords/afterlife.py` | Add `resolve_trigger()` instance method + module-level wrapper; move token creation logic from stack.py | Core afterlife resolution now lives in keyword module |
| `mtg_engine/ability/keywords/undying.py` | Add `resolve_trigger()` instance method + module-level wrapper; move graveyard→battlefield return logic from stack.py | Core undying resolution now lives in keyword module |
| `mtg_engine/ability/keywords/persist.py` | Add `resolve_trigger()` instance method + module-level wrapper; move graveyard→battlefield return logic from stack.py | Core persist resolution now lives in keyword module |
| `mtg_engine/ability/keywords/evoke.py` | Rewrite `apply()` to handle both queue and resolve modes; add module-level wrappers for backward compat | Consolidates engine/evoke.py logic into keyword module |
| `mtg_engine/ability/keywords/morph.py` | Add `turn_face_up()` instance method + module-level wrapper; move face-up logic from engine/morph.py | Core morph turn-face-up now lives in keyword module |
| `mtg_engine/ability/keywords/suspend.py` | Add `remove_time_counter()` instance method + module-level wrapper; add `get_ready_cards()` helper; move time counter logic from engine/suspend.py | Core suspend time counter management now lives in keyword module |

### Modified Engine Files (4 files — call site changes)

| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/stack.py` (lines 738-886) | Replace `_resolve_afterlife_trigger`, `_resolve_undying_trigger`, `_resolve_persist_trigger` with calls to keyword module functions; keep dispatcher structure | Delegates resolution to keyword modules |
| `mtg_engine/engine/stack.py` (lines 626-631) | Replace inline evoke queue call with `evoke.queue_sacrifice()` wrapper from keyword module | Uses keyword module API |
| `mtg_engine/engine/turn_manager.py` (lines 168-212) | Replace inline suspend time counter logic with `suspend.remove_time_counter_upkeep()` wrapper; keep auto-cast flow | Delegates time counter management to keyword module |
| `mtg_engine/engine/turn_manager.py` (lines 410-413) | Replace inline evoke resolve call with `evoke.resolve_sacrifice()` wrapper from keyword module | Uses keyword module API |

### Modified Engine Module Files (2 files — deprecated/replaced)

| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/evoke.py` | Replace all functions with thin wrappers that delegate to `EvokeKeyword`; add deprecation comments | Logic ownership transferred to keyword module |
| `mtg_engine/engine/morph.py` | Replace all functions with thin wrappers that delegate to `MorphKeyword`; add deprecation comments | Logic ownership transferred to keyword module |

### Modified Engine Module Files (1 file — deprecated/replaced)

| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/suspend.py` | Replace all functions with thin wrappers that delegate to `SuspendKeyword`; add deprecation comments | Logic ownership transferred to keyword module |

### Test Files (no new files — existing tests pass without modification)

All 6 existing integration test suites continue to work because:
1. Module-level wrapper functions maintain the same signatures as before
2. Behavior is identical — only code location changes
3. Tests import from `engine/evoke.py`, `engine/morph.py`, `engine/suspend.py` which now delegate to keyword modules

## Detailed Per-Module Refactoring Plan

### 1. Afterlife (`ability/keywords/afterlife.py`)

**Current state**: NOOP `apply()`, `create_trigger()` used by triggers.py, resolution in stack.py

**New methods on `AfterlifeKeyword` class**:
```python
def resolve_trigger(
    self,
    game_state: "GameState",
    controller: str,
    count: int = 1,
) -> "GameState":
    """Resolve afterlife trigger: create N 0/0 white Spirit tokens with afterlife 1.
    
    CR 702.108b: Create N 0/0 white Spirit creature tokens with afterlife 1.
    Pure transform: returns new GameState via model_copy (delegates to _create_token_with_pt_and_keywords).
    """
```

**Module-level convenience function**:
```python
def resolve_trigger(game_state: "GameState", stack_obj: "StackObject") -> "GameState":
    """Resolve afterlife trigger from a StackObject.
    
    Extracts count from stack_obj.trigger_data and delegates to AfterlifeKeyword.resolve_trigger().
    This is the primary entry point called by stack.py's dispatcher.
    """
```

**Changes in `stack.py`**: Replace `_resolve_afterlife_trigger()` (lines 780-796) with:
```python
if trigger_type == "afterlife":
    from mtg_engine.ability.keywords.afterlife import resolve_trigger as _resolve_afterlife
    return _resolve_afterlife(game_state, stack_obj)
```

**What stays in triggers.py**: `_queue_death_triggers()` — unchanged. It already calls `AfterlifeKeyword.create_trigger()`.

---

### 2. Undying (`ability/keywords/undying.py`)

**Current state**: NOOP `apply()`, `create_trigger()` used by triggers.py, resolution in stack.py

**New methods on `UndyingKeyword` class**:
```python
def resolve_trigger(
    self,
    game_state: "GameState",
    controller: str,
    card_name: str,
    power: int = 0,
    toughness: int = 0,
) -> "GameState":
    """Resolve undying trigger: return creature from graveyard with +1/+1 counters.
    
    CR 702.51b: Return it to the battlefield under its owner's control with a number
    of +1/+1 counters on it equal to its power and toughness.
    Pure transform: returns new GameState via model_copy.
    """
```

**Module-level convenience function**:
```python
def resolve_trigger(game_state: "GameState", stack_obj: "StackObject") -> "GameState":
    """Resolve undying trigger from a StackObject."""
```

**Changes in `stack.py`**: Replace `_resolve_undying_trigger()` (lines 799-846) with keyword module call.

---

### 3. Persist (`ability/keywords/persist.py`)

**Current state**: NOOP `apply()`, `create_trigger()` used by triggers.py, resolution in stack.py

**New methods on `PersistKeyword` class**:
```python
def resolve_trigger(
    self,
    game_state: "GameState",
    controller: str,
    card_name: str,
) -> "GameState":
    """Resolve persist trigger: return creature from graveyard with a -1/-1 counter.
    
    CR 702.61b: Return it to the battlefield under its owner's control with a -1/-1 counter on it.
    Pure transform: returns new GameState via model_copy.
    """
```

**Module-level convenience function**:
```python
def resolve_trigger(game_state: "GameState", stack_obj: "StackObject") -> "GameState":
    """Resolve persist trigger from a StackObject."""
```

**Changes in `stack.py`**: Replace `_resolve_persist_trigger()` (lines 849-886) with keyword module call.

---

### 4. Evoke (`ability/keywords/evoke.py`)

**Current state**: NOOP `apply()`, real logic in `engine/evoke.py` as standalone functions

**New methods on `EvokeKeyword` class**:
```python
def apply(
    self,
    game_state: "GameState",
    permanent: "Permanent | None" = None,
    mode: str = "queue",  # "queue" or "resolve"
    **kwargs,
) -> "GameState":
    """Apply evoke keyword ability.
    
    When mode="queue": Sets pending_evoke_sacrifice on GameState for mandatory end-step sacrifice.
    Called from stack.py after ETB placement when spell was cast via evoke cost.
    
    When mode="resolve": Executes the mandatory sacrifice — moves permanent to graveyard, clears pending state.
    Called from turn_manager.py at beginning of end step.
    
    Pure transform: returns new GameState via model_copy(update={...}).
    """
```

**Module-level convenience functions**:
```python
def queue_sacrifice(
    game_state: "GameState",
    permanent_id: str,
    player_name: str,
    card_name: str,
) -> "GameState":
    """Queue mandatory evoke sacrifice. Delegates to EvokeKeyword.apply(mode='queue')."""

def resolve_sacrifice(game_state: "GameState") -> "GameState":
    """Execute mandatory evoke sacrifice. Delegates to EvokeKeyword.apply(mode='resolve')."""

def resolve_with_ai(game_state: "GameState") -> "GameState":
    """AI auto-resolves evoke sacrifice (always sacrifices as mandatory)."""
```

**Changes in `stack.py`**: Replace inline call at lines 627-631 with `evoke.queue_sacrifice()`.

**Changes in `turn_manager.py`**: Replace inline call at lines 411-413 with `evoke.resolve_sacrifice()`.

**Changes in `engine/evoke.py`**: All functions become thin wrappers:
```python
def queue_evoke_sacrifice(...) -> GameState:
    from mtg_engine.ability.keywords.evoke import queue_sacrifice as _qs
    return _qs(game_state, permanent_id, player_name, card_name)

def resolve_evoke_sacrifice(...) -> GameState:
    from mtg_engine.ability.keywords.evoke import resolve_sacrifice as _rs
    return _rs(game_state)
```

---

### 5. Morph (`ability/keywords/morph.py`)

**Current state**: NOOP `apply()`, real logic in `engine/morph.py` as standalone functions

**New methods on `MorphKeyword` class**:
```python
def apply(
    self,
    game_state: "GameState",
    permanent: "Permanent | None" = None,
    target: "Permanent | None" = None,
) -> "GameState":
    """Apply morph turn face up.
    
    CR 702.35b: You may turn a face-down creature you control face up any time 
    you have priority by paying its mana cost (not morph cost — the real mana cost).
    
    Note: The existing engine/morph.py uses "morph cost" for turning face up, which is
    actually incorrect per CR 702.34b (you pay the creature's *mana cost*, not morph cost).
    However, this refactoring preserves existing behavior — no rule changes.
    
    Pure transform: returns new GameState via model_copy(update={...}).
    """
```

**New method on `MorphKeyword` class**:
```python
def turn_face_up(
    self,
    game_state: "GameState",
    permanent_id: str,
    mana_payment: dict[str, int] | None = None,
) -> "GameState":
    """Turn a face-down creature face up by paying its morph cost.
    
    CR 702.35b: doesn't use the stack, instant speed, can't be countered.
    Pure transform: returns new GameState via model_copy.
    """
```

**Module-level convenience functions**:
```python
def turn_face_up(
    game_state: "GameState",
    permanent_id: str,
    mana_payment: dict[str, int] | None = None,
) -> "GameState":
    """Turn a face-down creature face up. Delegates to MorphKeyword.turn_face_up()."""

def resolve_with_ai(game_state: "GameState", permanent_id: str) -> "GameState":
    """AI auto-resolves morph face-up: always pays if affordable."""
```

**Changes in `engine/morph.py`**: All functions become thin wrappers delegating to keyword module.

---

### 6. Suspend (`ability/keywords/suspend.py`)

**Current state**: NOOP `apply()`, real logic in `engine/suspend.py` as standalone functions, inline upkeep logic in turn_manager.py

**New methods on `SuspendKeyword` class**:
```python
def apply(
    self,
    game_state: "GameState",
    permanent: "Permanent | None" = None,
    target: "Permanent | None" = None,
) -> "GameState":
    """Apply suspend keyword ability.
    
    When called from turn_manager.py upkeep: removes one time counter from each 
    suspended card and marks cards with 0 counters as ready to cast.
    
    Pure transform: returns new GameState via model_copy(update={...}).
    """

def remove_time_counter(
    self,
    game_state: "GameState",
    player_name: str,
) -> "GameState":
    """Remove one time counter from all suspended cards of a player.
    
    Called at the beginning of upkeep for each player. When a card's last
    time counter is removed, it becomes available to cast (via from_suspended=True).
    Pure transform: returns new GameState via model_copy.
    """

def get_ready_cards(
    self,
    game_state: "GameState",
    player_name: str,
) -> list[dict]:
    """Get cards that are ready to be cast via suspend (no time counters left)."""
```

**Module-level convenience functions**:
```python
def remove_time_counter(game_state: "GameState", player_name: str) -> "GameState":
    """Remove one time counter from all suspended cards of a player."""

def get_ready_cards(game_state: "GameState", player_name: str) -> list[dict]:
    """Get cards ready to cast via suspend."""
```

**Changes in `turn_manager.py`**: Replace inline upkeep logic (lines 168-212) with call to `suspend.remove_time_counter()` + keep auto-cast flow. The auto-cast portion (calling `cast_spell`) stays in turn_manager.py because it's a general engine operation.

**Changes in `engine/suspend.py`**: All functions become thin wrappers delegating to keyword module.

## Data Models / Interfaces

No new data models needed. Existing models used:
- `GameState.pending_evoke_sacrifice: Optional[dict]` — unchanged
- `GameState.pending_morph_payment: Optional[dict]` — unchanged  
- `PlayerState.suspended_cards: list[Card]` — unchanged
- `StackObject.trigger_type: Optional[str]` — unchanged ("afterlife", "undying", "persist")
- `StackObject.trigger_data: dict` — unchanged (stores count, power, toughness)

### Key Interface Signatures

```python
# Afterlife resolution (called from stack.py dispatcher)
def resolve_trigger(game_state: GameState, stack_obj: StackObject) -> GameState: ...

# Undying resolution (called from stack.py dispatcher)
def resolve_trigger(game_state: GameState, stack_obj: StackObject) -> GameState: ...

# Persist resolution (called from stack.py dispatcher)
def resolve_trigger(game_state: GameState, stack_obj: StackObject) -> GameState: ...

# Evoke queue/resolve (called from stack.py and turn_manager.py)
def queue_sacrifice(gs: GameState, perm_id: str, player: str, card_name: str) -> GameState: ...
def resolve_sacrifice(gs: GameState) -> GameState: ...

# Morph face-up (called from API router / game.py choice handler)
def turn_face_up(gs: GameState, perm_id: str, mana_payment: dict | None = None) -> GameState: ...

# Suspend time counter management (called from turn_manager.py upkeep)
def remove_time_counter(gs: GameState, player_name: str) -> GameState: ...
```

## Task Breakdown (Ordered by Dependency)

### Task 1: Afterlife resolution into keyword module
- **Files**: `mtg_engine/ability/keywords/afterlife.py`, `mtg_engine/engine/stack.py`
- **Description**: Move `_resolve_afterlife_trigger()` from stack.py into `AfterlifeKeyword.resolve_trigger()`. Add module-level wrapper. Replace stack.py dispatcher call with import + function call. Delete old helper from stack.py.
- **Acceptance Criteria**: 
  - All existing afterlife integration tests pass (9 tests)
  - `_resolve_afterlife_trigger` no longer exists in stack.py
  - `AfterlifeKeyword.resolve_trigger()` contains the token creation logic

### Task 2: Undying resolution into keyword module
- **Files**: `mtg_engine/ability/keywords/undying.py`, `mtg_engine/engine/stack.py`
- **Description**: Move `_resolve_undying_trigger()` from stack.py into `UndyingKeyword.resolve_trigger()`. Add module-level wrapper. Replace stack.py dispatcher call. Delete old helper from stack.py.
- **Acceptance Criteria**:
  - All existing undying integration tests pass (16 tests)
  - `_resolve_undying_trigger` no longer exists in stack.py
  - `UndyingKeyword.resolve_trigger()` contains graveyard→battlefield return logic

### Task 3: Persist resolution into keyword module
- **Files**: `mtg_engine/ability/keywords/persist.py`, `mtg_engine/engine/stack.py`
- **Description**: Move `_resolve_persist_trigger()` from stack.py into `PersistKeyword.resolve_trigger()`. Add module-level wrapper. Replace stack.py dispatcher call. Delete old helper from stack.py.
- **Acceptance Criteria**:
  - All existing persist integration tests pass (11 tests)
  - `_resolve_persist_trigger` no longer exists in stack.py
  - `PersistKeyword.resolve_trigger()` contains graveyard→battlefield return logic

### Task 4: Evoke queue/resolve into keyword module
- **Files**: `mtg_engine/ability/keywords/evoke.py`, `mtg_engine/engine/evoke.py`, `mtg_engine/engine/stack.py`, `mtg_engine/engine/turn_manager.py`
- **Description**: Move `queue_evoke_sacrifice()` and `resolve_evoke_sacrifice()` logic from engine/evoke.py into `EvokeKeyword.apply()`. Add module-level wrappers. Convert engine/evoke.py functions to thin delegates. Update call sites in stack.py (line 628) and turn_manager.py (line 413).
- **Acceptance Criteria**:
  - All existing evoke integration tests pass (13+ tests)
  - `EvokeKeyword.apply()` contains real queue/resolve logic
  - engine/evoke.py functions delegate to keyword module

### Task 5: Morph face-up into keyword module
- **Files**: `mtg_engine/ability/keywords/morph.py`, `mtg_engine/engine/morph.py`
- **Description**: Move `apply_morph_turn_face_up()` logic from engine/morph.py into `MorphKeyword.turn_face_up()`. Add module-level wrappers. Convert engine/morph.py functions to thin delegates.
- **Acceptance Criteria**:
  - All existing morph integration tests pass (13+ tests)
  - `MorphKeyword.turn_face_up()` contains face-up logic with mana payment
  - engine/morph.py functions delegate to keyword module

### Task 6: Suspend time counter management into keyword module
- **Files**: `mtg_engine/ability/keywords/suspend.py`, `mtg_engine/engine/suspend.py`, `mtg_engine/engine/turn_manager.py`
- **Description**: Move `remove_time_counter()` logic from engine/suspend.py into `SuspendKeyword.remove_time_counter()`. Add module-level wrappers. Convert engine/suspend.py functions to thin delegates. Update turn_manager.py upkeep (lines 168-212) to call keyword module wrapper + keep auto-cast flow inline.
- **Acceptance Criteria**:
  - All existing suspend integration tests pass (13+ tests)
  - `SuspendKeyword.remove_time_counter()` contains time counter decrement logic
  - engine/suspend.py functions delegate to keyword module

### Task 7: Full regression test run
- **Files**: All test files
- **Description**: Run complete test suite to verify zero regressions across all 6 modules and the rest of the codebase.
- **Acceptance Criteria**: 
  - All existing tests pass (2700+ total)
  - No new failures introduced
  - Test count unchanged

## Testing Strategy

### Unit Tests (no changes needed — existing tests cover behavior)
All 6 existing integration test suites verify the same behavior regardless of code location:
- `tests/engine/test_afterlife_integration.py` (9 tests) — trigger queuing + resolution
- `tests/engine/test_undying_integration.py` (16 tests) — detection, counter guard, resolution
- `tests/engine/test_persist_integration.py` (11 tests) — detection, counter guard, resolution
- `tests/engine/test_evoke_integration.py` (13+ tests) — queue/resolve flow, edge cases
- `tests/engine/test_morph_integration.py` (13+ tests) — face-up, mana payment, AI
- `tests/engine/test_suspend_integration.py` (13+ tests) — time counter decrement, multi-turn

### Integration Tests (no changes needed)
The existing integration tests import from engine-level modules (`engine/evoke.py`, `engine/morph.py`, `engine/suspend.py`). These will continue to work because those files become thin wrappers that delegate to keyword modules. The afterlife/undying/persist tests exercise the full trigger→stack→resolve flow, which is preserved.

### Regression Testing (critical)
- Run full pytest suite after each task
- Verify test count matches baseline (~2700+ passing)
- Pay special attention to combat damage tests (afterlife/undying/persist interact with death)
- Pay special attention to turn advancement tests (evoke/suspend interact with end step/upkeep)

## Potential Risks

### Risk 1: Import cycles between keyword modules and engine modules
- **Scenario**: `ability/keywords/afterlife.py` needs `_create_token_with_pt_and_keywords` from stack.py, but stack.py imports from afterlife.py → circular import
- **Mitigation**: Use lazy imports (`from mtg_engine.engine.stack import _create_token...`) inside the function body. This is already done in undying/persist resolution functions and works correctly.

### Risk 2: `_update_player_in_game` helper in stack.py used by death trigger resolution
- **Scenario**: Moving undying/persist resolution out of stack.py means they can't access `_update_player_in_game()` (a private helper)
- **Mitigation**: Inline the player update pattern (`players = [new_player if p.name == ... else p for p in gs.players]; gs.model_copy(update={"players": players})`) directly in keyword module functions. This is a simple 2-line pattern that's easy to duplicate.

### Risk 3: Existing tests import from engine modules
- **Scenario**: Tests like `from mtg_engine.engine.evoke import queue_evoke_sacrifice` break if we delete those functions
- **Mitigation**: Keep engine/evoke.py, engine/morph.py, engine/suspend.py as thin wrapper files. They delegate to keyword module functions with identical signatures. This is zero-risk for test compatibility.

### Risk 4: Turn manager inline suspend logic has auto-cast flow that can't be extracted
- **Scenario**: The upkeep code (lines 168-212) interleaves time counter removal with `cast_spell()` calls and haste granting
- **Mitigation**: Only extract the time counter decrement portion into SuspendKeyword. Keep the auto-cast + haste grant flow in turn_manager.py, calling `suspend.remove_time_counter(gs, player)` first, then iterating ready cards for casting. This is a clean separation of concerns.

### Risk 5: Morph face-up uses mana payment logic from engine/mana.py
- **Scenario**: Moving morph face-up into keyword module requires importing from engine/mana.py
- **Mitigation**: This import already exists in the current engine/morph.py and works fine. The keyword module will use the same lazy import pattern.

## Architecture Diagram (Before → After)

```
BEFORE:
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│ triggers.py  │────▶│ stack.py     │────▶│ _resolve_afterlife│
│ _queue_death │     │ resolve_top()│     │ _resolve_undying  │
│   triggers() │     │              │     │ _resolve_persist  │
└─────────────┘     └──────────────┘     └──────────────────┘
                          │
                    ┌─────▼──────┐
                    │ engine/    │
                    │ evoke.py   │◀── stack.py (queue)
                    │ morph.py   │◀── API router
                    │ suspend.py │◀── turn_manager.py
                    └────────────┘

AFTER:
┌─────────────┐     ┌──────────────┐     ┌──────────────────────────┐
│ triggers.py  │────▶│ stack.py     │────▶│ ability/keywords/        │
│ _queue_death │     │ resolve_top()│     │ afterlife.resolve_trigger│
│   triggers() │     │ (thin dispatch)│   │ undying.resolve_trigger  │
└─────────────┘     └──────────────┘     │ persist.resolve_trigger  │
                                          └──────────────────────────┘
                          │                        ▲
                    ┌─────▼──────┐                 │
                    │ engine/    │◀── thin wrappers│
                    │ evoke.py   │    delegate to  │
                    │ morph.py   │    keyword mods │
                    │ suspend.py │                 │
                    └────────────┘                 │
                          │                        │
                    ┌─────▼──────┐     ┌───────────┴──────────┐
                    │turn_manager│────▶│ ability/keywords/     │
                    │  .py       │     │ evoke.apply()         │
                    └────────────┘     │ morph.turn_face_up()  │
                                       │ suspend.remove_tc()   │
                                       └───────────────────────┘
```

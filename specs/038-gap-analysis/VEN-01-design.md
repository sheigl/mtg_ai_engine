# Design: VEN-01 Venture into the Dungeon Mechanic

## Overview
Complete CR 701.61 "Venture into the dungeon" mechanic for Amonkhet/AFR dungeons. The system tracks per-player exploration through structured adventure paths with rooms, choices, and rewards. Cards like "The Dungeon" prompt players to venture; each room's ability resolves when entered; completing a dungeon triggers completion-based effects (e.g., Hama Pashar).

## Architecture Decisions

### Decision 1: Fix mutability bugs in existing `engine/dungeon.py`
**Rationale**: The current implementation directly mutates `game_state.player_dungeons[player_name]`, `game_state.pending_triggers.append()`, and `game_state.player_completed_dungeons[...]` in place. This violates the project standard (AGENTS.md) that all state transforms must be pure via `model_copy(update={...})`. The monarch.py module provides a correct pattern to follow.

**Trade-offs considered**:
- **Alternative**: Keep mutable style for dungeon-only code. Rejected: inconsistent with rest of engine, makes testing harder, breaks serialization assumptions.
- **Chosen approach**: Rewrite all functions in `engine/dungeon.py` to return new GameState via model_copy, matching monarch.py pattern.

### Decision 2: Add "venture into the dungeon" regex to stack effect resolution
**Rationale**: Currently `_apply_single_effect_text()` and `_apply_spell_effect()` have no pattern for "venture into the dungeon". When a card's oracle text says this (e.g., The Dungeon, Undercity rooms), it silently no-ops. Need to wire up `stack.py` → `dungeon.venture()`.

**Trade-offs considered**:
- **Alternative**: Handle venturing only in dedicated trigger code. Rejected: inconsistent with how other effects (draw, scry, etc.) are handled via pattern matching in stack resolution.
- **Chosen approach**: Add regex patterns to both `_apply_single_effect_text()` and `_apply_spell_effect()` that call `dungeon.venture()`.

### Decision 3: Use pending choice system for room choices
**Rationale**: Some dungeon rooms present binary or multi-way choices (e.g., Undercity's "Do you dare to proceed?"). The existing pending choice pattern (`pending_etb_choice`, `pending_commander_zone_choice`) is well-established. We follow the same pattern with `pending_dungeon_room_choice`.

**Trade-offs considered**:
- **Alternative**: Resolve room choices synchronously in the venture() call. Rejected: human players need to make choices via API; synchronous resolution only works for AI.
- **Chosen approach**: For rooms with choices, queue `pending_dungeon_room_choice` and let the choice handler resolve it (matching ETB/commander patterns).

### Decision 4: Room ability text drives effect resolution via stack
**Rationale**: When a player enters a room, the room's ability text should be processed through the existing stack/effect system. This means "Draw a card" in a room works because `_apply_spell_effect` already handles it. Rooms with "venture into the dungeon" recursively call venture().

**Trade-offs considered**:
- **Alternative**: Hard-code each room's effect as special-case logic. Rejected: fragile, doesn't scale to new dungeons, duplicates existing effect resolution code.
- **Chosen approach**: Room ability text flows through `_apply_single_effect_text()` via a synthetic stack object, reusing all existing pattern matching.

### Decision 5: Dungeon choice for "which dungeon to start" is AI-only at MVP
**Rationale**: CR 701.61 says when you venture and have no dungeon in progress, you choose which dungeon to enter. For human players, this adds a pending choice layer on top of room choices. At MVP, we default to the first available dungeon for humans (or accept `dungeon_name` parameter from card effects). Full "choose your dungeon" UI can be added later.

**Trade-offs considered**:
- **Alternative**: Always prompt human players to choose a dungeon. Rejected: adds complexity; most cards specify which dungeon (Undercity for initiative, The Dungeon lets you pick but that's one card). MVP defaults are sufficient.
- **Chosen approach**: `venture(gs, player, dungeon_name=None)` — if name is provided by the effect, use it; otherwise default to first available. Human "choose dungeon" pending choice deferred to VEN-02.

## Files to Create/Modify

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/engine/dungeon.py` | Fix all mutability bugs: use `model_copy(update={...})` for state transforms; add room choice handling; add `_apply_room_effect()` helper | Core engine correctness + new features |
| `mtg_engine/models/dungeon.py` | Add `choices` field to `Room`; add `DungeonRoomChoice` model | Support rooms with player choices |
| `mtg_engine/engine/stack.py` | Add "venture into the dungeon" regex patterns in `_apply_single_effect_text()` and `_apply_spell_effect()` | Card effects can trigger venturing |
| `mtg_engine/models/game.py` | Add `pending_dungeon_room_choice: Optional[dict] = None` to GameState | Pending choice for room decisions |
| `mtg_engine/api/routers/game.py` | Add dungeon room choice handler in `_process_choice()`; add legal actions in `_compute_legal_actions()` | Human player can make room choices via API |

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `tests/engine/test_venture_integration.py` | Integration tests for full venture flow | Test card effect → venture → room ability → choice resolution cycle |

## Task Breakdown (Ordered by Dependency)

### Task 1: Fix mutability bugs in `engine/dungeon.py`
- **Files**: `mtg_engine/engine/dungeon.py`
- **Description**: 
  1. Rewrite `set_dungeon_progress()` to use `model_copy(update={"player_dungeons": updated_dict})` instead of direct mutation
  2. Rewrite `venture()` to build new dicts/lists and return via model_copy instead of in-place mutations
  3. Ensure all callers already reassign: `gs = venture(gs, player)` (they do — initiative.py does this)
- **Acceptance Criteria**: 
  - All existing tests in `tests/engine/test_dungeon.py` still pass
  - Calling `venture()` returns a new GameState object (`id(new_gs) != id(old_gs)`)

### Task 2: Add room choice model to `models/dungeon.py`
- **Files**: `mtg_engine/models/dungeon.py`
- **Description**: 
  1. Add `DungeonRoomChoice` Pydantic model with fields: `choice_id`, `description`, `outcome_ability` (text of effect if chosen), `is_default` (bool — auto-picked by AI)
  2. Add `choices: list[DungeonRoomChoice] = Field(default_factory=list)` to `Room` model
  3. Update Undercity rooms that have choices with actual choice data
- **Acceptance Criteria**: 
  - Room model supports zero or more choices
  - Backward compatible: existing rooms without choices still work

### Task 3: Add "venture into the dungeon" pattern to stack effect resolution
- **Files**: `mtg_engine/engine/stack.py`
- **Description**: 
  1. In `_apply_single_effect_text()`, add pattern for "venture into the dungeon" that calls `dungeon.venture(game_state, controller)`
  2. In `_apply_spell_effect()`, add same pattern (for top-level spell effects)
  3. Handle "target player ventures into the dungeon" variant
- **Acceptance Criteria**: 
  - Card with oracle text "Venture into the dungeon." resolves correctly via stack
  - Card with oracle text "Target player ventures into the dungeon." targets correct player

### Task 4: Add room choice handling to `engine/dungeon.py`
- **Files**: `mtg_engine/engine/dungeon.py`, `mtg_engine/models/game.py`
- **Description**: 
  1. In `venture()`: after advancing to a new room, check if the room has choices
  2. If room has choices AND player is human: set `pending_dungeon_room_choice` and return (don't resolve ability yet)
  3. If room has choices AND player is AI: auto-resolve using `is_default` flag or first choice
  4. Add `_resolve_room_effect()` helper that applies the room's ability text through stack resolution
- **Acceptance Criteria**: 
  - Human players see pending choice for rooms with options
  - AI players auto-resolve room choices deterministically

### Task 5: Wire up API choice handler and legal actions
- **Files**: `mtg_engine/api/routers/game.py`
- **Description**: 
  1. In `_process_choice()`: handle `choice_id="dungeon_room_<N>"` — resolve the chosen room outcome, apply its ability text, clear pending choice
  2. In `_compute_legal_actions()`: when `pending_dungeon_room_choice` exists for priority player, return choice actions matching available room choices + pass
- **Acceptance Criteria**: 
  - Human player can see and submit dungeon room choices via API
  - Legal actions include room choice options

### Task 6: Add integration tests
- **Files**: `tests/engine/test_venture_integration.py` (new)
- **Description**: Create comprehensive integration tests covering:
  1. Card effect "Venture into the dungeon" → player enters first room
  2. Room ability resolves correctly through stack system
  3. Room with choice queues pending choice for human, auto-resolves for AI
  4. Dungeon completion increments counter and fires completed_dungeon trigger
  5. Per-player independent progress tracking
  6. Re-venturing after dungeon completion starts new dungeon
- **Acceptance Criteria**: 
  - All integration tests pass
  - No regressions in existing 2000+ test suite

### Task 7: Verify full test suite passes
- **Files**: N/A (run tests)
- **Description**: Run `PYTHONPATH=. pytest tests/ -v` to confirm no regressions. Specifically check `tests/engine/test_dungeon.py` and new integration tests.
- **Acceptance Criteria**: All existing + new tests pass

## Data Models / Interfaces

### Modified: Room model (add choices)
```python
class DungeonRoomChoice(BaseModel):
    """A choice presented by a dungeon room."""
    choice_id: str           # e.g., "dare", "retreat"
    description: str         # Display text for UI
    outcome_ability: str     # Effect text if this choice is made (goes through stack resolution)
    is_default: bool = False  # AI auto-picks this one

class Room(BaseModel):
    name: str
    index: int
    ability: str
    choices: list[DungeonRoomChoice] = Field(default_factory=list)
```

### Modified: GameState (add pending choice field)
```python
class GameState(BaseModel):
    # ... existing fields ...
    # VEN-01: Dungeon room choice pending for human players
    pending_dungeon_room_choice: Optional[dict] = None
    # Format: {
    #     "player": str,
    #     "dungeon_name": str,
    #     "room_index": int,
    #     "room_name": str,
    #     "choices": [{"choice_id": str, "description": str}],
    # }
```

### Fixed: Pure `venture()` function signature
```python
def venture(
    game_state: GameState,
    player_name: str,
    dungeon_name: Optional[str] = None,
) -> tuple[GameState, Room | None]:
    """
    The player ventures into the dungeon. CR 701.61.

    - If no dungeon in progress (or completed), start a new one.
    - Advance to the next room.
    - Return the room entered (None if dungeon is now complete).
    - Pure transform: returns new GameState via model_copy.
    """
```

### New: Room effect resolver
```python
def _apply_room_effect(
    game_state: GameState,
    player_name: str,
    ability_text: str,
) -> GameState:
    """
    Apply a room's ability text through the stack effect system.
    
    Creates a synthetic StackObject and routes through 
    _apply_single_effect_text() so existing patterns (draw, scry, etc.) work.
    """
```

### Fixed: Pure `set_dungeon_progress()`
```python
def set_dungeon_progress(
    game_state: GameState,
    player_name: str,
    progress: DungeonProgress,
) -> GameState:
    """Set the dungeon progress for a player. Pure transform."""
    new_dungeons = {**game_state.player_dungeons}
    new_dungeons[player_name] = progress
    return game_state.model_copy(update={"player_dungeons": new_dungeons})
```

## Testing Strategy

### Unit Tests (existing, in `tests/engine/test_dungeon.py`)
- `TestDungeonModels`: 7 tests for Room/Dungeon/DungeonProgress models ✅ already exists
- `TestVenture`: 8 tests for venture/start_dungeon functions — need updating for pure transforms

### New Integration Tests (`tests/engine/test_venture_integration.py`)
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card
from mtg_engine.engine.dungeon import (
    venture, start_dungeon, get_dungeon_progress, 
    get_completed_dungeon_count, _apply_room_effect,
)

def _make_game() -> GameState:
    return GameState(
        game_id="test-ven", seed=42, turn=1,
        active_player="Alice", priority_holder="Alice",
        players=[
            PlayerState(name="Alice", library=[Card(name=f"C{i}") for i in range(20)]),
            PlayerState(name="Bob", library=[Card(name=f"C{i}") for i in range(20)]),
        ],
    )

class TestVentureFromEffect:
    """Test that card effects can trigger venturing via stack resolution."""
    
    def test_venture_pattern_in_single_effect(self):
        """'Venture into the dungeon.' resolves correctly."""
        from mtg_engine.engine.stack import _apply_single_effect_text
        gs = _make_game()
        # Simulate a spell with "Venture into the dungeon." effect
        stack_obj = StackObject(
            source_card=Card(name="The Dungeon", oracle_text="Venture into the dungeon."),
            controller="Alice",
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Venture into the dungeon.")
        progress = get_dungeon_progress(gs, "Alice")
        assert progress is not None

    def test_target_player_ventures(self):
        """'Target player ventures into the dungeon.' targets correctly."""
        from mtg_engine.engine.stack import _apply_single_effect_text
        gs = _make_game()
        stack_obj = StackObject(
            source_card=Card(name="Test Card", oracle_text="Target player ventures into the dungeon."),
            controller="Alice",
            targets=["Bob"],
        )
        gs = _apply_single_effect_text(gs, stack_obj, "Target player ventures into the dungeon.")
        progress = get_dungeon_progress(gs, "Bob")
        assert progress is not None

class TestRoomEffectResolution:
    """Test that room abilities resolve through the stack system."""
    
    def test_draw_card_room(self):
        """Room ability 'Draw a card' draws from library."""
        gs = _make_game()
        gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")
        # Room 1: "Draw a card, then lose 1 life" — test draw part
        room_1_ability = "Draw a card, then lose 1 life"
        hand_before = len(get_player(gs, "Alice").hand)
        gs = _apply_room_effect(gs, "Alice", room_1_ability)
        assert len(get_player(gs, "Alice").hand) == hand_before + 1

    def test_scry_room(self):
        """Room ability 'Scry N' puts cards on bottom."""
        gs = _make_game()
        gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")
        # Room 0: "Scry 1"
        room_0_ability = "Scry 1"
        lib_before = len(get_player(gs, "Alice").library)
        gs = _apply_room_effect(gs, "Alice", room_0_ability)
        assert len(get_player(gs, "Alice").library) == lib_before

class TestDungeonCompletion:
    """Test dungeon completion tracking and triggers."""
    
    def test_completion_increments_counter(self):
        gs = _make_game()
        gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")  # 3 rooms
        gs = venture(gs, "Alice")  # room 1
        gs = venture(gs, "Alice")  # room 2  
        gs = venture(gs, "Alice")  # room 3 = complete
        assert get_completed_dungeon_count("Alice", gs) == 1

    def test_completion_fires_trigger(self):
        """Completing a dungeon adds a completed_dungeon pending trigger."""
        gs = _make_game()
        gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")
        for _ in range(3):
            gs = venture(gs, "Alice")
        # Check for completed_dungeon trigger in pending_triggers
        dungeon_triggers = [t for t in gs.pending_triggers if t.trigger_type == "completed_dungeon"]
        assert len(dungeon_triggers) >= 1

class TestPerPlayerIndependence:
    """Test that each player's dungeon progress is independent."""
    
    def test_independent_progress(self):
        gs = _make_game()
        gs = venture(gs, "Alice")
        gs = venture(gs, "Alice")
        gs = venture(gs, "Bob")
        assert get_room_count("Alice", gs) == 2
        assert get_room_count("Bob", gs) == 1

class TestPureTransforms:
    """Test that dungeon functions return new GameState objects."""
    
    def test_venture_returns_new_state(self):
        gs = _make_game()
        old_id = id(gs)
        gs = venture(gs, "Alice")
        assert id(gs) != old_id

    def test_start_dungeon_returns_new_state(self):
        gs = _make_game()
        old_id = id(gs)
        gs, _ = start_dungeon(gs, "Alice", "Lost Mine of Phandelver")
        assert id(gs) != old_id

class TestRoomChoices:
    """Test room choice handling for human vs AI players."""
    
    def test_human_room_queues_pending_choice(self):
        """Human player entering a room with choices gets pending_dungeon_room_choice."""
        gs = _make_game()
        gs.human_player_name = "Alice"
        # Use Undercity which has rooms with venture/choice patterns
        gs, _ = start_dungeon(gs, "Alice", "Undercity")
        gs = venture(gs, "Alice")  # Room 1: "Draw a card, then venture into the dungeon."
        # If room has choices, pending_dungeon_room_choice should be set

    def test_ai_auto_resolves_room_choice(self):
        """AI player auto-resolves room choice using is_default flag."""
        gs = _make_game()
        gs.human_player_name = None  # AI player
        gs, _ = start_dungeon(gs, "Alice", "Undercity")
        gs = venture(gs, "Alice")
        # Should auto-resolve without pending choice
        assert gs.pending_dungeon_room_choice is None

## Potential Risks

1. **Risk**: Room ability text patterns don't match existing stack resolution regexes → **Mitigation**: `_apply_room_effect()` routes through `_apply_single_effect_text()`, which already handles draw, scry, gain life, etc. For room abilities that need new patterns (e.g., "Return target creature card from your graveyard to the battlefield"), add them to the pattern list with a VEN-01 comment.

2. **Risk**: Recursive venturing — Undercity rooms say "venture into the dungeon" as part of their ability → **Mitigation**: The room effect goes through stack resolution, which calls `venture()` again. This is correct per CR 701.61 (venturing can chain). Guard against infinite loops by checking `progress.is_complete` before recursing.

3. **Risk**: Pending trigger from room ability conflicts with existing pending choice system → **Mitigation**: Room abilities that are simple effects (draw, scry) resolve synchronously in `_apply_room_effect()`. Only rooms with explicit player choices queue `pending_dungeon_room_choice`. Simple room abilities do NOT add to `pending_triggers` — they resolve immediately.

4. **Risk**: Dungeon state serialization/deserialization issues → **Mitigation**: `DungeonProgress` is a Pydantic BaseModel, serializes cleanly via `model_dump()`. The `player_dungeons: dict[str, DungeonProgress]` field uses standard dict serialization. No special handling needed.

5. **Risk**: Existing tests break due to mutability fix → **Mitigation**: All existing callers of `venture()` and `set_dungeon_progress()` already reassign the return value (`gs = venture(gs, ...)`). The only risk is if someone holds a reference to the old GameState dict — but that's an anti-pattern. Update test assertions if needed.

6. **Risk**: "Venture into the dungeon" regex in stack.py matches unintended text → **Mitigation**: Use specific pattern `r"\bventure\s+into\s+(?:the\s+)?dungeon\b"` with word boundaries to avoid false positives on words like "adventure".

## Handoff to Developer

**Design Document**: Above
**Estimated Complexity**: Medium — mutability fixes are straightforward, stack integration is a few regex additions, room choice system requires new API wiring but follows established patterns
**Key Files**: 
1. `mtg_engine/engine/dungeon.py` — Fix mutability + add room effect resolver (biggest change)
2. `mtg_engine/engine/stack.py` — Add venture regex patterns
3. `mtg_engine/api/routers/game.py` — Wire up dungeon room choice handler and legal actions
4. `tests/engine/test_venture_integration.py` — New integration test file

**Start With**: Task 1 (fix mutability in `engine/dungeon.py`) — this unblocks all other tasks since the pure transform pattern is foundational. Then run existing tests to confirm no regressions before proceeding.

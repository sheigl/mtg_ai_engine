# Design: ETB Choice System Test Plan (034-etb-choices)

## Overview

Create a comprehensive test suite for the ETB (enters-the-battlefield) choice system that covers detection, AI resolution, engine integration, API endpoints, and end-to-end gameplay flows. The system handles 4 land types: shockland, checkland, fetchland, and snow dual.

## Architecture Decisions

1. **Test Organization by Layer**: Tests are split into 5 files mirroring the architecture layers:
   - Detection (`test_etb_detection.py`) — unit tests for `_detect_etb_choice`
   - AI Resolution (`test_etb_ai.py`) — unit tests for `_resolve_etb_choice_with_ai`
   - Engine Integration (`test_etb_integration.py`) — tests for `put_permanent_onto_battlefield` with ETB choices
   - API Integration (`test_etb_choices.py`) — tests for choice endpoints and legal actions
   - Gameplay (`test_etb_gameplay.py`) — end-to-end tests simulating full turns

2. **Use Existing Test Helpers**: Reuse `create_test_card`, `create_test_game`, `_make_game`, `_make_card`, `_make_permanent`, `TestClient(app)` patterns from existing test files.

3. **Test Both Human and AI Paths**: The engine branches in `put_permanent_onto_battlefield` based on `human_player_name`. Both paths must be tested.

4. **Test What's Implemented + TODO for Gaps**: `_compute_legal_actions` only fully implements shockland ETB choices (lines 2236-2252). Checkland/fetchland/snow_dual have TODO comments. Tests cover the implemented shockland path and document gaps.

## Files to Create/Modify

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `tests/engine/test_etb_detection.py` | Unit tests for `_detect_etb_choice` | Verify all 4 patterns match correctly, no false positives, edge cases |
| `tests/engine/test_etb_ai.py` | Unit tests for `_resolve_etb_choice_with_ai` | Verify AI heuristics for all 4 land types under various board conditions |
| `tests/engine/test_etb_integration.py` | Integration tests for `put_permanent_onto_battlefield` | Verify human path queues pending choice, AI path resolves immediately, permanent state correct |
| `tests/api/test_etb_choices.py` | API integration tests for ETB choice endpoints | Test `etb_pay`/`etb_tapped` choice submission, legal actions return, state updates |
| `tests/rules/test_etb_gameplay.py` | End-to-end gameplay tests | Simulate playing a shockland through full API flow, verify battlefield state |

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `AGENTS.md` | Add test plan summary, sample ETB test code, coding standards | Handoff context for developer and QA |

## Task Breakdown (Ordered by Dependency)

### Task 1: Detection Tests
- **Files**: `tests/engine/test_etb_detection.py`
- **Description**: Test `_detect_etb_choice(oracle_text)` from `mtg_engine/engine/zones.py`
- **Acceptance Criteria**:
  - Shockland pattern matches "As this land enters, you may pay 2 life. If you don't, it enters tapped."
  - Checkland pattern matches "enters tapped unless you control a Forest or a Plains"
  - Fetchland pattern matches "As this land enters, you may pay 1 life and exile a land card..."
  - Snow dual pattern matches "As this land enters, you may pay 1 snow mana."
  - Returns correct `ETBChoice` object with `choice_type`, `cost_amount`, `cost_type`, `required_type`, `alternatives`
  - Returns `None` for cards without ETB choices (normal Forest, Grizzly Bears)
  - Returns `None` for unconditional "enters tapped" (already handled by `_parse_enters_tapped`)
  - Handles empty/None oracle_text gracefully

### Task 2: AI Resolution Tests
- **Files**: `tests/engine/test_etb_ai.py`
- **Description**: Test `_resolve_etb_choice_with_ai(game_state, player_name, choice, permanent_id, permanent_name)`
- **Acceptance Criteria**:
  - **Shockland**: AI pays life when `life > cost + 3` and either opponent has removal OR `life > cost + 6`; enters untapped. Otherwise enters tapped.
  - **Shockland**: AI does NOT pay when life is too low (≤ cost + 3)
  - **Checkland**: AI enters untapped when required land type is on battlefield under player's control; enters tapped otherwise
  - **Fetchland**: AI pays when `life > cost + 3` AND land exists in graveyard; enters untapped. Otherwise enters tapped.
  - **Fetchland**: AI does NOT pay when no land in graveyard
  - **Snow dual**: AI pays when can afford snow mana (current implementation uses `life > cost + 3 or True` — test this heuristic)
  - **Default**: Unknown choice type returns `should_be_tapped = True`
  - **Missing player**: Returns `should_be_tapped = True` when player not found

### Task 3: Engine Integration Tests
- **Files**: `tests/engine/test_etb_integration.py`
- **Description**: Test `put_permanent_onto_battlefield` with ETB choice cards
- **Acceptance Criteria**:
  - **Human player path**: When `human_player_name == controller`, playing a shockland sets `pending_etb_choice` on `GameState`, permanent enters tapped (`tapped=True`), and `pending_etb_choice.permanent_id` matches the created permanent's id
  - **AI player path**: When no human player (or AI controller), AI heuristic resolves immediately, permanent enters tapped or untapped based on heuristic, `pending_etb_choice` remains `None`
  - **Checkland human path**: `pending_etb_choice` is created with `choice_type="checkland"` and `required_type` populated
  - **Fetchland human path**: `pending_etb_choice` is created with `choice_type="fetchland"` and `required_zone="graveyard"`
  - **Snow dual human path**: `pending_etb_choice` is created with `choice_type="snow_dual"` and `cost_type="snow"`
  - **No ETB choice**: Normal Forest enters untapped, `pending_etb_choice` remains `None`
  - **Already tapped**: If `tapped=True` passed to `put_permanent_onto_battlefield`, ETB choice detection is skipped (line 634: `if etb_choice and not tapped`)

### Task 4: API Integration Tests
- **Files**: `tests/api/test_etb_choices.py`
- **Description**: Test API endpoints for ETB choice resolution
- **Acceptance Criteria**:
  - **Legal actions with pending ETB**: When `pending_etb_choice` exists for the priority player, `GET /game/{id}/legal-actions` returns exactly 2 choice actions: `card_name="etb_pay"` and `card_name="etb_tapped"`, plus a `pass` action
  - **Legal actions without pending ETB**: Normal legal actions are returned when no `pending_etb_choice`
  - **Choice submission etb_pay**: `POST /game/{id}/choice` with `choice_id="etb_pay"` reduces player life by `cost_amount`, sets permanent `tapped=False`, clears `pending_etb_choice`
  - **Choice submission etb_tapped**: `POST /game/{id}/choice` with `choice_id="etb_tapped"` clears `pending_etb_choice`, permanent remains tapped
  - **Choice submission without pending**: Submitting `etb_pay` or `etb_tapped` when no `pending_etb_choice` exists does not crash (no-op or graceful handling)
  - **State hash updates**: After choice submission, `state_hash` changes
  - **Game state persistence**: `GET /game/{id}` after choice shows updated life total and permanent tapped state

### Task 5: End-to-End Gameplay Tests
- **Files**: `tests/rules/test_etb_gameplay.py`
- **Description**: Full turn simulation playing ETB choice lands via API
- **Acceptance Criteria**:
  - **Play shockland as human**: Create game with human player, advance to main phase, play Steam Vents from hand, verify `pending_etb_choice` appears, submit `etb_pay`, verify life reduced by 2, permanent untapped on battlefield
  - **Play shockland as human (tapped)**: Same flow but submit `etb_tapped`, verify life unchanged, permanent tapped on battlefield
  - **AI plays shockland**: Create game with AI player, AI plays shockland, verify AI makes decision (either life paid or tapped) within game state update
  - **Checkland with prerequisite**: Game with Canopy Vista and a Forest on battlefield — checkland enters untapped (AI path)
  - **Checkland without prerequisite**: Game with Canopy Vista and no Forest/Plains — checkland enters tapped (AI path)

## Data Models / Interfaces

```python
# Key dataclass from zones.py
@dataclass
class ETBChoice:
    choice_type: str       # "shockland" | "checkland" | "fetchland" | "snow_dual"
    cost_amount: int = 0
    cost_type: str = ""    # "life" | "snow" | "mana"
    required_type: str = ""  # e.g., "forest or a plains"
    required_zone: str = ""  # e.g., "graveyard"
    alternatives: list[str] = field(default_factory=list)

# GameState field (already exists)
class GameState(BaseModel):
    pending_etb_choice: Optional[dict] = None
    # Format: {
    #   "player": str,
    #   "permanent_id": str,
    #   "permanent_name": str,
    #   "choice_type": str,
    #   "cost_amount": int,
    #   "cost_type": str,
    #   "required_type": str,
    #   "alternatives": [str]
    # }

# LegalAction model (from api/routers/game.py)
class LegalAction(BaseModel):
    action_type: str
    card_name: str = ""
    description: str = ""
    valid_targets: list[str] = Field(default_factory=list)
```

## Testing Strategy

### Unit Tests
- **Detection**: 15+ tests covering exact match, partial match, false positives, None input, empty string
- **AI Resolution**: 20+ tests covering all 4 land types with various life totals, board states, graveyard contents

### Integration Tests
- **Engine**: 10+ tests covering human/AI paths, all 4 land types, tapped flag interaction, permanent_id linkage
- **API**: 10+ tests covering legal actions, choice submission, state consistency, error handling

### End-to-End Tests
- **Gameplay**: 5+ tests covering full turns from game creation through land play to choice resolution

### Regression Tests
- Ensure existing `test_020_etb_replacements.py` still passes (unconditional "enters tapped" should not trigger ETB choice system)
- Ensure `test_zones.py` still passes (normal `put_permanent_onto_battlefield` behavior unchanged)

### Test Fixtures and Helpers

```python
# From existing patterns — use these helpers

# Helper for detection tests
def _make_shockland_oracle(cost: int = 2) -> str:
    return f"As this land enters, you may pay {cost} life. If you don't, it enters tapped."

def _make_checkland_oracle(required: str = "a Forest or a Plains") -> str:
    return f"Canopy Vista enters tapped unless you control {required}."

def _make_fetchland_oracle(cost: int = 1) -> str:
    return f"As this land enters, you may pay {cost} life and exile a land card from your graveyard. If you don't, it enters tapped."

def _make_snow_dual_oracle(cost: int = 1) -> str:
    return f"As this land enters, you may pay {cost} snow mana. If you don't, it enters tapped."

# Helper for AI tests
def _make_game_with_battlefield(life: int = 20, graveyard_lands: int = 0, battlefield_lands: list[str] | None = None) -> GameState:
    """Create game with specified player state for AI heuristic testing."""
    ...

# Helper for API tests
def _create_game_with_human(deck_size: int = 60, seed: int = 42, human_name: str = "p1") -> dict:
    """Create game with human_player_name set."""
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": ["Steam Vents"] * deck_size,  # or appropriate test deck
        "deck2": ["Forest"] * deck_size,
        "seed": seed,
        "human_player_name": human_name,
    })
    return resp
```

## Potential Risks

1. **Risk**: `_compute_legal_actions` only implements shockland in legal actions (checkland/fetchland/snow_dual have TODO). Tests for those types will fail if they try to get legal actions.
   - **Mitigation**: Test only shockland legal actions. Add `pytest.mark.skip` or `pytest.mark.xfail` for checkland/fetchland/snow dual legal action tests with a comment referencing the TODO.

2. **Risk**: Snow dual AI heuristic is oversimplified (`life > cost + 3 or True` always evaluates to True, and it subtracts life instead of snow mana). Tests will expose this.
   - **Mitigation**: Write tests that document the current behavior. Add TODO comments in tests for when snow mana tracking is implemented.

3. **Risk**: Fetchland AI heuristic exiles land from graveyard but the actual exile logic is not fully implemented (comment says "would need additional logic").
   - **Mitigation**: Test that fetchland AI pays life when conditions met, but do not assert graveyard state change until exile logic is implemented.

4. **Risk**: Existing tests (`test_020_etb_replacements.py`) use a "Shockland" card with unconditional "enters battlefield tapped" text. This should NOT trigger the new ETB choice system.
   - **Mitigation**: Verify that `_parse_enters_tapped` handles unconditional text and `_detect_etb_choice` does not false-positive on it. Add a regression test.

5. **Risk**: `put_permanent_onto_battlefield` creates the permanent with `tapped=True` for human path BEFORE the choice is made. If the choice is "pay", the API endpoint must set `tapped=False`.
   - **Mitigation**: Test that after `etb_pay`, the permanent's `tapped` field is `False`. Test that after `etb_tapped`, it remains `True`.

## Handoff to Developer

**Design Document**: Inline above
**Estimated Complexity**: Medium
**Key Files**:
1. `tests/engine/test_etb_detection.py` — 15 unit tests for pattern detection
2. `tests/engine/test_etb_ai.py` — 20 unit tests for AI heuristics
3. `tests/engine/test_etb_integration.py` — 10 integration tests for engine behavior
4. `tests/api/test_etb_choices.py` — 10 API tests for endpoints
5. `tests/rules/test_etb_gameplay.py` — 5 end-to-end gameplay tests

**Start With**: Task 1 (Detection Tests) — these are pure unit tests with no dependencies, fastest to implement, and verify the foundation for all other tests.

**Total Estimated Tests**: ~60 tests across 5 files.

**Important Notes**:
- Only shockland legal actions are fully implemented in `_compute_legal_actions`. Test other land types in engine/AI layers but skip/xfail their legal action tests.
- Snow dual AI uses life subtraction as a placeholder for actual snow mana payment. Document this in tests.
- Fetchland AI does not actually exile from graveyard yet. Document this gap.
- Reuse existing test helpers (`create_test_card`, `create_test_game`, `_make_game`, `_make_card`, `TestClient(app)`).
- All tests should use `pytest` and follow the existing code style (no emojis, standard Python naming).

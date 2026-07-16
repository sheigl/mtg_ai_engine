# INT-01 Initiative Mutability Fix Design

## Problem
`initiative.py` has direct mutations in `set_initiative()`:
- Line 25: `game_state.initiative = player_name` — mutates GameState directly
- Line 41: `game_state.pending_triggers.append(trigger)` — mutates pending_triggers list

## Fix Plan

### 1. Fix `mtg_engine/engine/initiative.py`

#### `set_initiative()` — Replace mutations with model_copy
```python
def set_initiative(game_state: GameState, player_name: str) -> GameState:
    """Set the initiative to the given player. Returns new GameState."""
    if game_state.initiative == player_name:
        return game_state

    old = game_state.initiative
    logger.info("Initiative: %s gains the initiative (was %s)", player_name, old or "none")

    trigger = PendingTrigger(
        id=str(uuid.uuid4()),
        source_permanent_id="initiative",
        source_card_name="initiative",
        controller=player_name,
        trigger_type="gain_initiative",
        effect_description=f"{player_name} gains the initiative",
    )

    return game_state.model_copy(update={
        "initiative": player_name,
        "pending_triggers": [*game_state.pending_triggers, trigger],
    })
```

#### `handle_upkeep_venture()` — Already pure (calls venture() which is pure) ✅ No changes needed

#### `check_combat_damage_initiative()` — Already pure (calls set_initiative()) ✅ No changes needed after fix above

### 2. Update existing tests in `tests/engine/test_initiative.py`
Add immutability assertions: verify original GameState unchanged after `set_initiative()`.

### 3. Create integration test suite at `tests/engine/test_initiative_integration.py`
14+ integration tests covering:
- Full combat damage → initiative transfer flow via combat/core.py hook
- Upkeep venture flow through turn_manager begin_step(UPKEEP)
- Multiple initiative transfers in sequence (immutability chain)
- Initiative + dungeon progress tracking across turns
- set_initiative immutability assertions

## Acceptance Criteria
- `set_initiative()` returns new GameState via model_copy — no direct mutations
- All 14 existing unit tests pass with added immutability assertions
- New integration test file passes all tests
- Full test suite: no regressions

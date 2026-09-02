# KW-04 Death Triggers Design Document

## Overview
Implement Afterlife (CR 702.108), Undying (CR 702.51), Persist (CR 702.61), and Sunburst (CR 702.103) as proper triggered abilities using the existing trigger/stack infrastructure. Remove incorrect inline replacement-effect code from `zones.py`.

## Architecture Decisions

### A1: Trigger Wiring — Shared Function in triggers.py
Add a new function `check_death_keyword_triggers()` and call it from `_on_zone_change()`:

```python
def check_death_keyword_triggers(event, game_state):
    """Check dying permanent for afterlife/undying/persist keyword triggers."""
    if event.get("to_zone") != "graveyard" or event.get("from_zone") != "battlefield":
        return
    
    card_id = event.get("card_id", "")
    # Find the dying permanent in the zone change event data (it was on battlefield)
    # The permanent is already being moved — we need its state BEFORE it left
    # Use event.get("permanent") or reconstruct from card name + controller
```

**Why shared function**: All three death triggers share the same condition check (battlefield → graveyard). A single function reduces code duplication and makes future keyword additions easier.

### A2: Shared Helper for Graveyard Return — In stack.py
Add `_return_from_graveyard_with_counters()` in `stack.py`:

```python
def _return_from_graveyard_with_counters(
    game_state: GameState,
    card_name: str,
    controller: str,
    counter_type: str,  # "+1/+1" or "-1/-1"
    counter_count: int,
) -> GameState:
    """Return a card from graveyard to battlefield with counters. Pure transform."""
```

**Why in stack.py**: This is an effect resolution helper (like `_create_token_with_keywords`). It's called during trigger resolution on the stack.

### A3: Sunburst — Inline ETB Counter Application
Sunburst fires as part of `put_permanent_onto_battlefield()` when a permanent enters via casting. Add a new function in `sunburst.py`:

```python
def apply_sunburst_counters(game_state, permanent, mana_cost) -> GameState:
    """Apply sunburst counters to the entering permanent. Pure transform."""
```

**Why inline**: Sunburst is simpler than death triggers — it just adds counters to an existing permanent. No need for stack-based trigger resolution. The "if cast" condition is already tracked by `put_permanent_onto_battlefield` callers.

### A4: zones.py Refactoring Plan
**Remove lines 292-317 entirely**. This code incorrectly implements persist/undying as inline replacement effects (bypassing the stack). After removal, the normal zone change flow continues to line 319 (`if to_zone == "battlefield"` / `if to_zone in ("hand", ...)`).

## Task Breakdown

### TASK 1: Remove zones.py Inline Code
- **File**: `mtg_engine/engine/zones.py` lines 292-317
- **Action**: Delete the entire block. The function should fall through to the normal zone change logic at line 319.
- **Verification**: Existing persist/undying tests will initially fail (expected — they relied on inline behavior). New trigger-based tests replace them.

### TASK 2: Wire Death Triggers into triggers.py
- **File**: `mtg_engine/engine/triggers.py` — add to `_on_zone_change()` after line 329
- **Action**: After the existing Landfall handling, add a call to check for keyword death triggers on the dying permanent. The key challenge: by the time `_on_zone_change` fires, the permanent has already been removed from battlefield. We need to capture its state (keywords, counters) at the moment of death.

**Implementation approach**: Pass the dying permanent's data through the `ZoneChangeEvent` dict. The zone change event is emitted in `zones.py` — we can attach `permanent_data` to the event before calling listeners. Then `_on_zone_change()` reads this data to check keywords/counters.

### TASK 3: Implement Afterlife Resolution
- **File**: `mtg_engine/ability/keywords/afterlife.py` — implement real `apply()` method
- **Stack wiring**: Add explicit handler in `_apply_triggered_effect()` for `trigger_type="afterlife"` that calls the keyword module's apply function with token creation via `_create_token_with_pt_and_keywords()`
- **Token spec**: 0/0 white Spirit creature tokens, keywords=["afterlife"], each gets afterlife count of 1

### TASK 4: Implement Undying Resolution
- **File**: `mtg_engine/ability/keywords/undying.py` — implement real `apply()` method
- **Stack wiring**: Add handler in `_apply_triggered_effect()` for `trigger_type="undying"` that calls `_return_from_graveyard_with_counters(gs, card_name, controller, "+1/+1", power+toughness)`

### TASK 5: Implement Persist Resolution
- **File**: `mtg_engine/ability/keywords/persist.py` — implement real `apply()` method
- **Stack wiring**: Add handler in `_apply_triggered_effect()` for `trigger_type="persist"` that calls `_return_from_graveyard_with_counters(gs, card_name, controller, "-1/-1", 1)`

### TASK 6: Implement Sunburst ETB Counters
- **File**: `mtg_engine/ability/keywords/sunburst.py` — implement real `apply()` and `apply_sunburst_counters()` functions
- **Wiring point**: Call from `put_permanent_onto_battlefield()` in `zones.py` when permanent enters battlefield AND was cast (check for a "cast" flag or stack context)

### TASK 7: Test Suite
Create/update integration tests:
- `tests/engine/test_afterlife_integration.py` — NEW, ~12 tests
- `tests/engine/test_undying_integration.py` — UPDATE existing, add resolution tests
- `tests/engine/test_persist_integration.py` — UPDATE existing, add resolution tests
- `tests/engine/test_sunburst_integration.py` — NEW, ~10 tests

## Key Implementation Details

### ZoneChangeEvent Enhancement
The zone change event dict needs to carry the dying permanent's state. In `zones.py`, before calling `_notify_zone_change_listeners()`:
```python
event = {
    "from_zone": from_zone,
    "to_zone": to_zone,
    "card_id": card.id,
    "permanent_id": perm_id if perm_id else "",
    "controller": controller,
    "card_name": card.name,
    # NEW: carry permanent state for trigger evaluation
    "permanent_keywords": card.keywords or [],
    "permanent_counters": dict(permanent.counters) if permanent.counters else {},
    "permanent_power": permanent.card.power,
    "permanent_toughness": permanent.card.toughness,
}
```

### Trigger Resolution in stack.py `_apply_triggered_effect()`
Add explicit handlers before the generic pattern matching:
```python
# Handle keyword-specific trigger types directly
trigger_type = getattr(stack_obj, 'trigger_type', None)
if trigger_type == "afterlife":
    return _resolve_afterlife_trigger(game_state, stack_obj)
elif trigger_type == "undying":
    return _resolve_undying_trigger(game_state, stack_obj)
elif trigger_type == "persist":
    return _resolve_persist_trigger(game_state, stack_obj)
```

### StackObject Enhancement for Trigger Type
`StackObject` needs to carry `trigger_type` so `_apply_triggered_effect()` can dispatch. When creating the StackObject from a PendingTrigger in `stack.py`, pass `trigger_type=trigger.trigger_type`.

## Constraints
- **DO NOT modify sba.py** — SBA runs after triggers resolve
- All transforms use `model_copy(update={...})` — no direct mutations
- Trigger counter guard: Undying checks for +1/+1 counters at death time; Persist checks for -1/-1 counters. These checks happen when QUEUING the trigger (in `_on_zone_change`), not during resolution.

# TRG-20 Design: Fix Trigger Bugs + Add Missing Triggers

## Part A: Bug Fixes (9 failing tests)

### Root Cause 1: Missing "you" controller filtering
Functions that accept a `player_name` parameter fire triggers for ALL permanents regardless of whether the oracle text says "whenever YOU X" vs "whenever a player X". Fix: add `_is_you_pattern()` helper and filter.

### Root Cause 2: Missing regex patterns
Some oracle text variants aren't matched by existing pattern lists (e.g., "dies", "this creature transforms").

### Root Cause 3: Direct mutation instead of model_copy
Most B1 check functions mutate `game_state.pending_triggers.append()` directly. Only `check_proliferated_triggers` uses pure transform. Fix all to use `new_triggers = list(gs.pending_triggers)` + `model_copy`.

---

### Helper function (add at top of B1 section):
```python
def _is_you_pattern(pattern_idx: int, patterns: list[_re.Pattern]) -> bool:
    """Return True if the matched pattern is a 'you' (self-referential) pattern.
    Pattern index 0 in each list is always the 'you' variant."""
    return pattern_idx == 0
```

### Fix per test:

#### Test 1: `test_triggers_on_any_sacrifice` — sacrifice trigger not firing
**File**: `triggers.py`, line 574, SACRIFICE_TRIGGER_PATTERNS (line ~150)
**Fix A**: Add pattern for "dies" to SACRIFICE_TRIGGER_PATTERNS:
```python
SACRIFICE_TRIGGER_PATTERNS = [
    _re.compile(r"whenever a creature you control is sacrificed", _re.IGNORECASE),
    _re.compile(r"whenever (?:a|an) .*? dies", _re.IGNORECASE),  # NEW
]
```
**Fix B**: Convert to pure transform — use `new_triggers` + `model_copy`

#### Test 2: `test_no_trigger_opponent_life_change_does_not_affect_p1` — fires for opponent life loss
**File**: `triggers.py`, line 608, `check_life_gain_lost_triggers`
**Fix**: Add controller filter. For "you" patterns (index 0), only fire if `perm.controller == player_name`. For "a player" patterns (index 1+), also filter — the test expects NO trigger for opponent events on your permanents:
```python
# After pattern match, before creating trigger:
if perm.controller != player_name:
    continue
```
Convert to pure transform.

#### Test 3: `test_no_proliferate_trigger_for_opponent` — fires when opponent proliferates
**File**: `triggers.py`, line 679, `check_proliferated_triggers`
**Fix**: Add controller filter for "you" patterns (index 0):
```python
# Inside the pattern loop:
pattern_idx = list(PROLIFERATED_TRIGGER_PATTERNS).index(pattern)
if _is_you_pattern(pattern_idx, PROLIFERATED_TRIGGER_PATTERNS) and perm.controller != player_name:
    continue
```

#### Test 4: `test_trigger_on_self_transform` — regex doesn't match "this creature transforms"
**File**: `triggers.py`, line 178, TRANSFORMED_TRIGGER_PATTERNS
**Fix**: Change pattern from `"whenever (?:this|~) transforms"` to `"whenever (?:this(?:\s+creature)?|~) transforms"`:
```python
TRANSFORMED_TRIGGER_PATTERNS = [
    _re.compile(r"whenever (?:this(?:\s+creature)?|~) transforms", _re.IGNORECASE),  # FIXED
    _re.compile(r"whenever a double-faced card you control transforms", _re.IGNORECASE),
]
```
Also convert `check_transformed_triggers` to pure transform.

#### Test 5: `test_no_tutor_trigger_for_opponent` — fires when opponent searches
**File**: `triggers.py`, line 751, `check_tutor_triggers`
**Fix**: Add controller filter for "you" patterns (index 0). Convert to pure transform.

#### Test 6: `test_trigger_becomes_attached` — fires for ALL permanents, not just the aura
**File**: `triggers.py`, line 817, `check_attach_triggers`
**Fix**: Add self-referential guard (like fight/transform already have):
```python
is_this_trigger = bool(_re.compile(r"whenever this becomes attached", _re.IGNORECASE).search(cond))
if is_this_trigger and perm.id != aura_perm_id:
    continue
```
Convert to pure transform.

#### Test 7: `test_no_trigger_for_opponent_dungeon` — fires when opponent completes dungeon
**File**: `triggers.py`, line ~890, `check_completed_dungeon_triggers`
**Fix**: Add controller filter for "you" patterns (index 0). Convert to pure transform.

#### Test 8: `test_no_mana_spent_trigger_for_opponent` — fires when opponent spends mana
**File**: `triggers.py`, line ~920, `check_mana_spent_triggers`
**Fix**: Add controller filter for "you" patterns (index 0). Convert to pure transform.

#### Test 9: `test_trigger_for_opponent_mana` — mana production trigger not firing
**File**: `triggers.py`, MANA_PRODUCTION_TRIGGER_PATTERNS + `check_mana_production_triggers`
**Fix A**: Add pattern for "whenever a player spends mana" to MANA_PRODUCTION_TRIGGER_PATTERNS:
```python
MANA_PRODUCTION_TRIGGER_PATTERNS = [
    _re.compile(r"whenever you tap a land for mana", _re.IGNORECASE),
    _re.compile(r"whenever a land produces mana", _re.IGNORECASE),
    _re.compile(r"whenever a player spends mana", _re.IGNORECASE),  # NEW
]
```
**Fix B**: Convert to pure transform.

---

## Part B: New Trigger Types (Top 5)

### 1. Draw Triggers — `check_draw_triggers(gs, player_name)`
- **Patterns**: `"whenever you draw a card"`, `"whenever a player draws a card"`
- **Hook**: Called from `stack.py` `_draw_cards()` after drawing
- **Filter**: "you" patterns require controller match

### 2. Discard Triggers — `check_discard_triggers(gs, discarded_perm_ids, player_name)`
- **Patterns**: `"whenever you discard a card"`, `"whenever a player discards"`
- **Hook**: Called from wherever cards are moved to graveyard via discard

### 3. Token Creation Triggers — `check_token_triggers(gs, token_type, controller)`
- **Patterns**: `"whenever a creature token enters"`, `"whenever you create a token"`
- **Hook**: Called from stack.py when creating tokens

### 4. Counter Triggers — `check_counter_triggers(gs, perm_id, counter_type, player_name)`
- **Patterns**: `"whenever a +1/+1 counter is put on"`, `"whenever a charge counter is removed"`
- **Hook**: Called from wherever counters are added/removed

### 5. Planeswalk Triggers — `check_planeswalk_triggers(gs, perm_id, player_name)`
- **Patterns**: `"whenever this planeswalker planeswalks"`, `"whenever a planeswalker you control planeswalks"`
- **Hook**: Called from stack.py when loyalty abilities resolve

---

## Part C: Test Plan
- All 9 failing tests should pass after fixes
- Add controller filter assertions to verify "you" vs "a player" semantics
- Add pure transform assertions (id(new_gs) != id(old_gs)) for all check functions
- Add tests for each of the 5 new trigger types

# Tasks: Heuristic Player Mulligan Bug Fix

**Source**: Bug — heuristic players never commit to keeping or mulliganing their hand; the game loops indefinitely in the mulligan phase, and no cards ever appear on the battlefield.

**Affected file**: `ai_client/heuristic_player.py`

---

## Bug Description

`_score_mulligan(action, ...)` is called for every `declare_mulligan` action. Both legal actions during a mulligan decision share `action_type="declare_mulligan"`:

| description | action_type |
|---|---|
| `"Mulligan (draw N)"` | `declare_mulligan` |
| `"Keep hand"` | `declare_mulligan` |

`_score_mulligan` calls `evaluate_mulligan()` and returns:
- `50.0` if the player should mulligan  
- `-50.0` if the player should keep

Because **both** actions receive the same score, the relative ordering is wrong when the hand is keepable: both `declare_mulligan` actions score `-50.0` while "Pass priority" scores `0.0`. The heuristic picks "pass" every time.

Consequence:
- The mulligan endpoint is never called with `keep=True`
- `mulligan_phase_active` stays `True` forever
- The game advances turns (pass-priority fires the normal phase-advance logic)
- Players draw a card each turn while remaining in the mulligan phase
- No lands or creatures are ever played → battlefield stays empty → **no cards visible**

### Verified via live game state

```
Turn: 6, mulligan_phase_active: True, players_kept: [], Battlefield: 0 permanents
H1 hand: 10 cards  H2 hand: 9 cards
```

---

## Bug Fixes

- [X] T001 Fix `_score_mulligan` in `ai_client/heuristic_player.py` — check the action description to distinguish "Keep hand" from "Mulligan" before returning a score: `is_keep = "keep" in (action.get("description") or "").lower(); should_mulligan = self.evaluate_mulligan(hand, len(hand)); return (50.0 if not should_mulligan else -50.0) if is_keep else (50.0 if should_mulligan else -50.0)` — this ensures "Keep hand" scores 50.0 when the hand is worth keeping (outscoring pass at 0.0) and "Mulligan" scores 50.0 only when the player should mulligan

- [X] T002 Add a fast integration test in `tests/` — create `tests/test_heuristic_mulligan.py` that builds a mock game state with a keepable 7-card mixed hand, instantiates `HeuristicPlayer`, calls `decide()` with the three mulligan-phase legal actions (`[pass, mulligan, keep_hand]`), and asserts the returned index points to "Keep hand" and NOT to "pass" or "Mulligan"

---

## Root Cause

`_score_mulligan` was written to answer "should I mulligan?" but was not designed to answer "which specific action represents that decision?" The two `declare_mulligan` actions are semantically opposite, yet both route to the same scoring method and receive identical scores. The correct fix treats `_score_mulligan` as a per-action scorer that inspects the description, not a binary keep/mulligan oracle.

## Fix Strategy

Change only the return logic in `_score_mulligan` (4 lines). No other code changes needed. The mulligan endpoint and game loop are working correctly — only the action selection was broken.

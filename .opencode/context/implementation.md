# Implementation Context

## Sprint 7 P1 Bloodthirst Keyword (CR 702.22) — Story 7-6e — 2026-09-02

Implemented the Bloodthirst keyword (previously a NOOP stub) as part of the alternative-casting-cost umbrella Story 7-6 (sub-story 7-6e).

### Production changes
- `mtg_engine/ability/keywords/bloodthirst.py` — `BloodthirstKeyword.apply()` now has a real implementation:
  - No-op guards (permanent lacks bloodthirst / no opponent dealt damage this turn) return the SAME GameState per Q4
  - Bloodthirst amount from `self.amount` or parsed from oracle text
  - Checks `game_state.damage_dealt_this_turn` (dict[str, int] mapping player → damage received this turn)
  - If any opponent has damage > 0, adds N +1/+1 counters to the entering permanent
  - Pure transform via `model_copy`; emits `counter_placed` event
- `mtg_engine/models/game.py` (line 376) — NEW `damage_dealt_this_turn: dict[str, int]` field
- `mtg_engine/engine/zones.py` (lines 767-775) — ETB wiring in `put_permanent_onto_battlefield()`: detects Bloodthirst via `from_oracle()`, applies counters
- `mtg_engine/engine/combat/core.py` (lines 731-733) — combat damage tracking (CR 702.22b)
- `mtg_engine/engine/stack.py` (lines 2090-2092) — spell/ability damage tracking (CR 702.22b)
- `mtg_engine/engine/turn_manager.py` (line 543) — resets `damage_dealt_this_turn` at turn start

### Tests
- `tests/engine/test_bloodthirst_integration.py` — 19 tests across 4 classes:
  - `TestBloodthirstUnit` (6): module helpers (has/parse/from_oracle)
  - `TestBloodthirstApply` (5): direct apply (counters, no-op same-object guard, oracle-parsed amount, pure transform)
  - `TestBloodthirstETB` (6): `put_permanent_onto_battlefield` wiring incl. AI controller and multi-opponent
  - `TestBloodthirstDamageTracking` (2): combat and spell damage both trigger per CR 702.22b

### Status
- Full suite: **3167 passed / 0 failed / 3 skipped / 13 xfailed**
- Skip/xfail set unchanged from baseline
- ruff 0 NEW errors (4 E402 in bloodthirst.py are pre-existing at git HEAD)

### Known limitation
- Damage tracking counts only player life loss/poison, not damage to permanents (sufficient for the Bloodthirst condition which checks whether an opponent was dealt damage).

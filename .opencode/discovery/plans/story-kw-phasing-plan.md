# Technical Plan: Phasing (CR 702.26) — Story `story-kw-phasing`

## Overview
Wire the Phasing keyword end-to-end. Currently only model stubs exist (`Permanent.phased_out`, `Permanent.has_phasing`) and no engine logic drives phasing. This plan adds a pure-transform keyword module, an end-of-untap/start-of-untap hook in turn_manager.py, targeting/combat/SBA exclusion for phased-out permanents, API choice-handler wiring, and integration tests.

## 1. State Model Changes (`models/game.py`)
Reuse existing stubs on `Permanent`:
- `phased_out: bool = False` — set True when the permanent phases out.
- `has_phasing: bool = False` — set from keyword detection at ETB/creation time.

Add ONE new field to `GameState`:
```python
# US15 (Phasing): perm_id -> controller_name for all currently-phased-out permanents.
phased_out_permanents: dict[str, str] = Field(default_factory=dict)
```
Also add a per-turn phase counter so "return at next untap" is unambiguous even if the same player's turn processes twice:
```python
# perm_id -> turn number on which it last phased out (for return timing).
phased_out_turns: dict[str, int] = Field(default_factory=dict)
```

## 2. Keyword Module (`mtg_engine/ability/keywords/phasing.py`)
Base class: `PassiveKeyword` (passive end-of-step mechanic).

- Regex detection: `_PHASING_RE = re.compile(r"\bphasing\b")`.
- Static helpers exported for tests:
  - `has_phasing(card_or_perm) -> bool` — checks keyword list or oracle text.
  - `from_oracle_text(oracle_text) -> bool`.
- Module-level functions (mirroring crew.py pattern):
  - `phase_out(game_state, controller_name) -> GameState`: returns a NEW GameState via `model_copy(update={...})` in which every of `controller_name`'s untapped-or-tapped permanents with phasing that is not already phased out gets `phased_out=True`; records `phased_out_turns[perm_id] = current_turn`. No-op (same object) if none qualify.
  - `phase_in(game_state, controller_name) -> GameState`: returns a NEW GameState in which every permanent currently in `phased_out_permanents` for that controller is set back to `phased_out=False`, removed from the dict; does NOT fire an untap event and does NOT reset summoning-sick via this call.
  - `_detect_phasing(game_state, perm_id) -> bool`.

Pure-transform discipline: every branch returns a new object except the no-op guard which returns the SAME `game_state` (Q4).

## 3. turn_manager.py Hook (THE hard dependency)
In `begin_step()`, within the `Step.UNTAP` branch, add an end-of-untap-step block AFTER the existing day/night transition "second part of untap step". Phasing has two sub-events in one untap step:

**Phase-in at START of untap:** Before untapping, for each controller whose `phased_out_permanents` is non-empty, call `phase_in(game_state, controller)` — return permanents to the battlefield. (Only active_player's are relevant; others' remain phased out.)

**Phase-out at END of untap:** After the untap/daynight work, for the `active_player`, call `phase_out(game_state, active_player)`. Because both happen in the same untap step and phase-in must precede phase-out (a permanent returning this turn should not immediately phase out again), process phase_in first, then phase_out.

The hook location is a small additive block gated on `phased_out_permanents` being non-empty so existing games with no phasing are byte-identical.

## 4. Targeting / Combat / SBA Exclusion
Filter phased-out permanents out of:
- **Targeting validation** (`stack.py` target loops, `_compute_legal_actions`): skip any `perm.phased_out`.
- **Attack declaration** (`combat/core.py declare_attackers`): a phased-out attacker can't be declared; a creature defended against that is phased out can't be attacked.
- **Block assignment** (`assign_combat_damage`): phased-out creatures don't block and can't be blocked.
- **SBA** (`sba.py`): treat phased-out as non-existent — exclude from "you lose if life <= 0" style checks that iterate battlefield, and from death/destruction (a phased-out permanent shouldn't die).
Use a shared helper `is_phased_out(game_state, perm_id) -> bool` so all call sites share one check.

## 5. Attachment Preservation
Reuse existing `attached_to`/`attachments`. When a host phases out, its attached Auras/Equipment also phase out (they carry the flag via their controller's phased-out set). On return they remain attached — no detach/re-attach. Confirm SBA does not treat a now-orphaned attachment as invalid while host is phased out; add `and not perm.phased_out` guards to any SBA detach check that iterates attachments.

## 6. API Router Wiring (`mtg_engine/api/routers/game.py`)
Phasing has no human decision point — it's automatic at untap. No pending-choice handler needed. Ensure:
- Legal-actions endpoint does not offer phasing as an action (it's a passive step).
- The `/legal-actions` snapshot correctly excludes phased-out permanents from valid targets/attacks (handled via section 4 helper).

## 7. Test Plan (`tests/engine/test_phasing_integration.py`, 8–15 tests)
1. `test_detection` — `has_phasing` true for oracle containing "phasing", false otherwise.
2. `test_phase_out_at_end_of_untap` — after untap-step hook, phasing permanent is phased out; non-phasing stays in.
3. `test_phased_out_not_targetable` — a spell targeting a phased-out creature has zero legal targets (helper returns False).
4. `test_phased_out_cannot_attack` — declare_attackers rejects a phased-out attacker.
5. `test_phased_out_cannot_block` — block assignment ignores phased-out blocker.
6. `test_counters_persist_through_phasing` — permanent with +1/+1 counters returns with them.
7. `test_aura_stays_attached_on_return` — attached aura remains attached after phase-in.
8. `test_returns_at_next_untap` — next untap step phases the permanent back in and removes it from `phased_out_permanents`.
9. `test_does_not_untap_on_return` — returning does not fire an untap event / does not clear summoning-sick via phase-in (verify no untap-state change beyond phased_out flag).
10. `test_pure_transform_noop_returns_same_object` — phasing a game with no phasing permanents returns the SAME object.
11. `test_phased_out_excluded_from_sba_death` — a damaged phased-out permanent is not destroyed by SBA.
12. `test_multiple_players_independent` — player A's phase-in does not affect player B's phased-out permanents.

## 8. Edge Cases & CR Gaps
- **Phase-in vs phase-out ordering in the same untap step**: phase-in first (return permanents), then phase-out (phase out fresh ones). Documented in section 3.
- **Permanent removed from game while phased out**: while phased out it "doesn't exist", so nothing can target/remove it; if a global effect removes everything, SBA/exclusion helpers must skip phased-out — no special action needed.
- **Losing the game with a phased-out permanent**: leave `phased_out_permanents` as-is; game-over short-circuits turn progression.
- Phasing rules are well-defined (CR 702.26) — no ambiguity. The one genuine subtlety is the two-phase untap-step ordering, nailed in section 3.

## 9. Files to Modify / Create & Task Order
1. `mtg_engine/ability/keywords/phasing.py` — NEW module (regex, helpers, phase_in/phase_out).
2. `mtg_engine/models/game.py` — add `phased_out_permanents` and `phased_out_turns` to `GameState`.
3. `mtg_engine/engine/turn_manager.py` — add phase-in + phase-out blocks in the UNTAP branch (section 3).
4. `mtg_engine/engine/stack.py` — guard target loops with `is_phased_out`; use shared helper.
5. `mtg_engine/engine/combat/core.py` — exclude phased-out from declare_attackers / assign_combat_damage.
6. `mtg_engine/engine/sba.py` — skip phased-out in battlefield iteration + attachment detach checks.
7. `mtg_engine/api/routers/game.py` — confirm no phasing action offered (verify only).
8. `tests/engine/test_phasing_integration.py` — NEW test file (section 7).

**Task order:** (1) model field → (2) keyword module + shared helper → (3) turn_manager hook → (4) targeting/combat/SBA guards → (5) API verify → (6) tests → (7) run full suite, confirm byte-identical skip/xfail set (3 skip / 13 xfail).

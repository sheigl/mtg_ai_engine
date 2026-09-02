# Out-of-Scope / Deferred-Items Registry

Comprehensive, durable list of every item that was explicitly declared **out of scope** or **deferred**
during Sprint 7 (and the OOS items the user directed to be closed this session). Built from a full
sweep of: code `TODO/FIXME/no-op` comments, `.opencode/context/` files, Sprint 7 discovery/plan
"Out of Scope" / "Deferred" / "Known Gaps" sections, and AGENTS.md "Known Gaps".

Last updated: 2026-09-01 (post OOS-1 + OOS-2). Suite baseline at this date: **3079 / 0 / 3 / 13**.

Status legend:
- ✅ **RESOLVED** — closed (references the story/commit that closed it).
- 🔴 **OPEN** — still deferred; candidate for a future story.
- 🟡 **VERIFY** — appears resolved by a later story, needs a confirming run before closing.

---

## A. OOS items the user directed to be closed this session

| # | Item | Status | Closed by |
|---|------|--------|-----------|
| A1 | **Ward fired on ABILITIES** (CR 702.145a "spell OR ability") — Ward previously fired only from `cast_spell` (spells), not from activated abilities. | ✅ RESOLVED | OOS-1 (2026-09-01). `apply_ward_to_ability()` in `ward.py`; wired into REAL `/activate` after cost, before effect. Suite 3067/0/3/13. |
| A2 | **Toxic spurious no-op `combat_damage` PendingTrigger** — the `check_damage_triggers` fallback regex matched Toxic's parenthetical KEYWORD REMINDER text and queued a cosmetic no-op trigger. | ✅ RESOLVED | OOS-2 (2026-09-01). `_is_inside_parenthetical()` helper + `finditer` parenthetical-skip in `triggers.py`. Suite 3079/0/3/13. |
| A3 | Ward backlog note ("Ward should also cover abilities") — the original backlog entry behind A1. | ✅ RESOLVED | Superseded by A1. |

---

## B. Previously-resolved gaps (audited — do NOT re-open)

These were listed as "Known Gaps"/"Deferred" in earlier Sprint 7 stories but have since been closed.
Recorded here so a future sweep doesn't re-report them as open.

| # | Item | Status | Closed by |
|---|------|--------|-----------|
| B1 | **CR 903.9 commander-on-sacrifice redirect bypass** in `_sacrifice_permanent` (sacrificed commanders could no longer go to command zone). | ✅ RESOLVED | 7-17 (P1 Trigger Fidelity Minors, item 1). Human path defers via `pending_commander_zone_choice`; AI auto-redirects. |
| B2 | **Unattach path latent** — `check_attach_triggers(attach_event="unattach")` had no call site. | ✅ RESOLVED | 7-17 (item 2). Call site added in `zones.move_permanent_to_zone`, controller captured pre-removal. |
| B3 | **Multi-token creation under-fires** — `check_token_triggers` fired once after the token loop instead of per-token (CR 110.6). | ✅ RESOLVED | 7-17 (item 3). Now fires inside the token loop. |
| B4 | **Missing negative unit test** for "a creature **you** control is sacrificed" not firing on an opponent's sacrifice. | ✅ RESOLVED | 7-17 (item 4). |
| B5 | **Integration coverage gaps** for the cycling API route and Fading upkeep counter-removed route. | ✅ RESOLVED | 7-17 (item 5). `tests/api/test_cycle_endpoint.py` + `tests/engine/test_fading_upkeep_triggers.py`. |
| B6 | **Investigate token-creation double-queue** for token-fallback-phrased watchers. | ✅ RESOLVED | 7-3 test round 1 (pattern-ownership split: token-ETB phrasings owned by `check_token_triggers`). |
| B7 | **Cycling endpoint did not deduct the cycle cost** (documented at `game.py` ~1001 in the 7-17 note, 2026-08-27). | ✅ RESOLVED | 7-5d (Cycling, 2026-08-31). `/cycle` now calls `_pay_mana(gs, player_name, cycling_cost)` (game.py:990). The 7-17 note predates this fix. |

---

## C. OPEN — engine / trigger fidelity

| # | Item | Where | Source |
|---|------|-------|--------|
| C1 | **Saga final chapter — DEAD scheduled trigger**: `sacrifice_saga:{perm.id}` is scheduled at `turn_manager.py:279` but **no resolver/consumer** performs the sacrifice. The trigger is queued and never resolves. | `turn_manager.py:272-282` | context/architecture.md:246; SPRINT7-P1-minors:95; SPRINT7-P0-wiring:135 |
| C2 | **`mana_spent` does NOT fire for non-cast payments**: kicker / buyback / replicate / activated-ability mana payments do not emit the `mana_spent` trigger (only spell-cast payments do). | `morph.py turn_face_up`, kicker/buyback/replicate/activate paths | context/architecture.md:260; SPRINT7-P1-minors:97; SPRINT7-P0-wiring:136 |
| C3 | **SBA legend rule NOT routed**: the legend-rule removal path (`sba.py:237-249`) does its own event + removal and fires **no sacrifice trigger**. | `sba.py:237-249` | context/architecture.md:245 |
| C4 | **`pending_triggers` is a shallow copy under `model_copy`**: the list is shallow-copied when a `GameState` is copied; a deep-copy pass is a future task. | `models/game.py` | SPRINT7-P1-minors:102; SPRINT7-P0-wiring:138 |
| C5 | **`check_damage_triggers` still mutates `pending_triggers` in place** (pre-existing shape, deliberately preserved in OOS-2). Candidate for a future pure-transform (Q4) refactor. | `triggers.py` | OOS-2 Code Review recommendation |
| C6 | **Token-creation coverage**: only 3 of ~24 token functions actually create tokens (`_create_tokens`, `_create_token_with_keywords`, `_create_token_with_pt_and_keywords`); the rest are stubs that log "TODO" and return early. | `stack.py` | context/architecture.md:251 |
| C7 | **`_COMBAT_DAMAGE_TRIGGER_RE` recompiled inside the per-permanent loop** (trivial perf; pre-existing placement). | `triggers.py` (~704) | OOS-2 Code Review recommendation |

---

## D. OPEN — keyword / mechanic

| # | Item | Where | Source |
|---|------|-------|--------|
| D1 | **Multi-ward targeting**: an activated ability targeting MULTIPLE different ward permanents queues only the **first** ward trigger. | `ward.py` / `/activate` | OOS-1 Code Review (known limitation) |
| D2 | **Equip bonus does NOT auto-revert on Equipment detach**: `clear_equip_bonus` is not wired into the SBA/zone-detach flow (the aura revert at `zones.py:276-281` is gated on `"aura" in type_line`; Equipment is not an aura). Bonus persists after the Equipment leaves the battlefield until someone clears it. | `equip.py`, `zones.py:276-281` | context/implementation.md:163 / :239 |
| D3 | **Player-level keyword tracking NOT implemented on `PlayerState`**: `hexproof`/`shroud` query helpers return `False` for player-name targets (only permanent targets are checked). | `hexproof.py`, `shroud.py` | AGENTS.md:672 |
| D4 | **Companion mechanic** delegated to COM-01 (out of scope for CMD-01). | commander | AGENTS.md:552 |
| D5 | **"Fortified land" reference resolution**: the static/triggered abilities on the two real Fortify cards that reference the "fortified land" (Darksteel Garrison "Fortified land has indestructible"; C.A.M.P. "Whenever fortified land is tapped for mana...") are a follow-up. The Fortify *attach* works; the attached Fortification's own abilities that reference the fortified land do not. | Fortify | SPRINT7-P0-fortify:82 |
| D6 | **Legacy Clue-token activated ability** is out of scope (documented known simplification). Modern investigate creates a Goblin Scout token instead. | investigate | SPRINT7-P0-missing-triggers-plan:378 |
| D7 | **`"whenever a land is investigated"` phrasing** intentionally out of scope (approved 7-3 scope delta; only 2 action patterns shipped). | `triggers.py INVESTIGATED_TRIGGER_PATTERNS` | SPRINT7-P0-missing-triggers:23; SPRINT7-P2:107 |

---

## E. OPEN — API / endpoint

| # | Item | Where | Source |
|---|------|-------|--------|
| E1 | **Cycling legal-actions offer branch** (~`game.py:3279`) still uses the local `_CYCLING_RE` regex instead of the `cycle.py` module detector (drift; the live `/cycle` route was unified but the legal-actions offer branch was left). | `game.py` | context/implementation.md:135 / :211 |
| E2 | **`recent_games` always empty** in player stats — will be populated when the game-history store is implemented (APP-06 gap). TODO in code. | `player_stats.py:65` | code TODO |
| E3 | **Alternative costs not implemented** — the special-action path for `alternative_cost` (split/phyrexian/etc.) returns "not yet implemented" (400). | `game.py:2231` | code comment |
| E4 | **Unimplemented loyalty effects no-op** — `loyalty.py` logs "Loyalty effect not yet implemented" and no-ops for effect types it doesn't handle. | `loyalty.py:241` | code comment |

---

## F. OPEN — ETB choices (encoded as the 3 SKIPPED + 13 XFAIL'd tests)

These are the only intentional skip/xfail entries in the suite. Do NOT add/remove without closing the
underlying gap (Q6: skip/xfail set must stay byte-identical).

| # | Item | Where | Source |
|---|------|-------|--------|
| F1 | **`_compute_legal_actions` only fully implements SHOCKLAND ETB**; checkland / fetchland / snow_dual have TODO comments. | `game.py` ~2397-2398 / :2670 | AGENTS.md:544; code TODO |
| F2 | **Snow dual AI subtracts LIFE instead of snow mana** — placeholder until snow-mana tracking is implemented. | `zones.py` `_resolve_etb_choice_with_ai` | AGENTS.md:545 |
| F3 | **Fetchland AI does not actually exile the land from the graveyard** (comment: "would need additional logic"). | `zones.py` `_resolve_etb_choice_with_ai` | AGENTS.md:546 |

Test encoding: 3 skipped = `tests/api/test_etb_choices.py` lines 185/190/195 (checkland/fetchland/snow_dual
legal-actions not fully implemented). 13 xfailed = `test_etb_detection.py` ×5 + `test_etb_integration.py` ×4 +
`test_etb_ai.py` ×4 (Checkland "or" types, Fetchland regex, Snow-dual regex/placeholder).

---

## G. Minor / trivial

| # | Item | Where | Source |
|---|------|-------|--------|
| G1 | **Docstring typo** "ACTIVITY" → "ABILITY" in the `apply_ward_to_ability` docstring. | `ward.py:349` | OOS-1 Code Review |

---

## Suggested next candidates (if a future story is needed)
Ordered roughly by impact/effort:
1. **C1 Saga final-chapter dead trigger** — a whole card type (Sagas with a final "sacrifice" chapter) is half-wired; a resolver completes it.
2. **D2 Equip-bonus auto-revert on detach** — small, localized, closes a correctness gap.
3. **D1 Multi-ward targeting** — closes the last Ward fidelity gap.
4. **F1-F3 ETB checkland/fetchland/snow_dual** — closes the 3 skips + 13 xfails (largest test-set payoff).
5. **C2 mana_spent non-cast payments** — fidelity for cost-based triggers.
6. **E3 alternative costs** — needed for split/phyrexian cards.

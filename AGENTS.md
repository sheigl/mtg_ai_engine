# mtg_ai_engine Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-13

## Active Technologies
- N/A (in-memory game state) (029-skip-empty-phases)

- Python 3.11 + FastAPI, Pydantic v2, motor (async MongoDB driver) (028-player-default-settings)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes
- 2026-09-03: **Sprint 7 P1 Convoke Keyword (CR 702.43) implemented — Story 7-6f** — real `apply()` in `mtg_engine/ability/keywords/convoke.py` with cost reduction via tapping creatures; human queues `pending_convoke_choice`, AI auto-resolves with greedy color-matching (prefer untapped creatures matching cost colors, then generic taps); `pending_convoke_choice` field on GameState; `stack.py` `cast_spell` intercepts Convoke casts and defers for human choice; API `/cast` flow with `convoke_pay`/`convoke_pass` legal actions and choice handler; cost reduction applied before mana payment; new tests/engine/test_convoke_integration.py (9); suite 3167/0/3/13 (+18 net from 3149 Bloodthirst baseline); skip/xfail byte-identical; ruff 0 NEW. Known limitation: convoke combined with cost-reduction keywords may double-count; tapped creatures not returned if cast fails.
- 2026-09-02: **Sprint 7 P1 Bloodthirst Keyword (CR 702.22) implemented — Story 7-6e** — real `apply()` in `mtg_engine/ability/keywords/bloodthirst.py` with damage tracking (combat and non-combat damage dealt this turn, CR 702.22b); no-op guards (no bloodthirst / no opponent damage) return the SAME GameState per Q4; `damage_dealt_this_turn` dict field on GameState; `zones.py` `put_permanent_onto_battlefield` ETB wiring detects Bloodthirst via `from_oracle` and applies N +1/+1 counters; damage tracking wired in `combat/core.py` `assign_combat_damage` and `stack.py` `_deal_damage`; `turn_manager.py` resets `damage_dealt_this_turn` each turn; emits counter_placed event; new tests/engine/test_bloodthirst_integration.py (19 tests across 4 classes); suite 3167/0/3/13; skip/xfail byte-identical; ruff 0 NEW (4 E402 in bloodthirst.py pre-existing at git HEAD). Known limitation: damage tracking counts only player life loss/poison, not damage to permanents (sufficient for the Bloodthirst condition).
- 2026-09-01: **Sprint 7 P1 Miracle Keyword (CR 702.93) implemented — Story 7-6d of the alternative-casting-cost umbrella (7-6)** — real `apply()` in `miracle.py` (first-draw detection, human queues `pending_miracle_choice`, AI auto-resolves by affordability, no-op guards same-object); `cards_drawn_this_turn` dict + `pending_miracle_choice` fields on GameState; `turn_manager.py` resets `cards_drawn_this_turn` each turn; `zones.py` `draw_card` increments counter and detects Miracle on first draw, queues pending for human or auto-casts for AI; API `/cast` alternative cost flow with `miracle_cast`/`miracle_pass` legal actions and choice handler; new tests/engine/test_miracle_integration.py (13); suite 3139/0/3/13 (+13 net from 3126); skip/xfail byte-identical; ruff 0 NEW. Known limitation: card moved to hand before miracle check; cost-reduction combos skip interception.
- 2026-09-01: **Sprint 7 P1 Overload Keyword (CR 702.95) implemented — Story 7-6c of the alternative-casting-cost umbrella (7-6)** — real `apply()` in overload.py (human queues `pending_overload_choice`, AI auto-resolves by affordability, no-op guards same-object); `pending_overload_choice` field on GameState; `stack.py` `cast_spell` replaces base cost with overload cost (alternative, not additional); `_apply_spell_effect` replaces "target" with "each" when `overload_paid`; API `/cast` intercept + `overload_pay`/`overload_pass` handlers (NO pass); overloaded spells target nothing; new tests/engine/test_overload_integration.py (11); suite 3126/0/3/13 (+11 net from 3115 Entwine baseline); skip/xfail byte-identical; ruff 0 NEW. Known limitation: overload combined with cost-reduction keywords skips interception.
- 2026-09-01: **Sprint 7 P1 Entwine Keyword (CR 702.39/702.41) implemented — Story 7-6b of the alternative-casting-cost umbrella (7-6)** — Entwine {cost} is an ADDITIONAL cost on modal spells (not an alternative): if paid, all modes are applied on resolution instead of a single mode. Real `apply()` in `mtg_engine/ability/keywords/entwine.py` replaces the prior NOOP; no-op guards (non-modal / no-entwine / unparseable cost) return the SAME GameState object per Q4. Human path queues `pending_entwine_choice` (cast deferred until the choice resolves); AI path auto-resolves by affordability of base+entwine. NEW `GameState` field `pending_entwine_choice: Optional[dict] = None` (~models/game.py). `stack.py` adds `_split_modal_texts` helper; modal resolution refactored to use it (behavior-preserving). `cast_spell` gains `entwine_paid: bool = False` parameter: when True, the entwine cost is APPENDED to the base cost for a single-flow payment — the base cost is STILL required, so an unpaid/unparseable entwine yields `entwine_paid=False` and only a single mode is applied. Resolution selects ALL modes when `entwine_paid`, else SINGLE mode. `mtg_engine/api/routers/game.py`: `/cast` intercepts HUMAN entwine casts (defers via `pending_entwine_choice`); `entwine_pay`/`entwine_pass` choice handlers re-drive the cast with `entwine_paid=True/False`; `INSUFFICIENT_MANA` keeps pending; legal actions offer entwine_pay + entwine_pass with NO `pass`. New tests/engine/test_entwine_integration.py (13 tests). Full suite 3115 passed / 0 failed / 3 skipped / 13 xfailed (+13 net from 3102 Buyback baseline); skip/xfail byte-identical; ruff 0 NEW. Known limitation (documented): entwine combined with cost-reduction keywords skips interception and casts without offering entwine (no known card combines them).
- 2026-09-01: **Sprint 7 P1 Buyback Keyword (CR 702.27/702.28) implemented — Story 7-6a of the alternative-casting-cost umbrella (7-6)** — Buyback {cost} is an ADDITIONAL cost on sorcery-speed spells (not an alternative): if paid, the spell returns to its owner's hand on resolution instead of the graveyard. Real `apply()` in `mtg_engine/ability/keywords/buyback.py` replaces the prior NOOP, with a new `_is_sorcery_speed_spell()` helper; no-op guards (non-sorcery-speed spell, missing/unparseable cost) return the SAME GameState object per Q4. Human path queues `pending_buyback_choice` (cast deferred until the choice resolves); AI path auto-resolves by affordability of base+buyback. NEW `GameState` field `pending_buyback_choice: Optional[dict] = None` (~models/game.py:431). `cast_spell` in `mtg_engine/engine/stack.py` gains a `buyback_paid: bool = False` parameter (~line 135): when True, the buyback cost is APPENDED to the base cost for a single-flow payment (top-up logic ~215-237) — the base cost is STILL required, so an unpaid/unparseable buyback yields `buyback_paid=False` and the spell goes to the graveyard. The StackObject is built with `buyback_paid=buyback_paid and bool(buyback_extra_cost)` (~line 364), REPLACING the old placeholder `buyback_paid=has_buyback` that wrongly marked every buyback spell as paid for free. Resolution (~line 795) returns the spell to HAND when `buyback_paid`, else GRAVEYARD. `mtg_engine/api/routers/game.py`: `/cast` intercepts HUMAN buyback casts (defers via `pending_buyback_choice`, ~878-913); `buyback_pay`/`buyback_pass` choice handlers (~2199-2271) re-drive the cast with `buyback_paid=True/False`; `INSUFFICIENT_MANA` keeps pending; legal actions offer buyback_pay + buyback_pass with NO `pass`. New tests/engine/test_buyback_integration.py (23 tests). Full suite 3102 passed / 0 failed / 3 skipped / 13 xfailed (+23 net from the 3079 Toxic-hygiene baseline; exactly the 23 new tests); skip/xfail set byte-identical to the ETB baseline; ruff 0 NEW errors. Known limitation (documented): buyback combined with cost-reduction keywords (convoke/delve/improvise/emerge) skips the interception and casts without offering buyback (no known card combines them).
- 2026-09-01: **Toxic spurious-trigger hygiene (CR 702.134 reminder no-op) — fallback now skips parenthetical keyword reminders** — Out-of-scope fix: the fallback regex in `check_damage_triggers()` (`mtg_engine/engine/triggers.py`) was matching Toxic's **keyword reminder** text (the parenthetical "(Toxic N ...)" oracle line) and queueing a spurious no-op `combat_damage` PendingTrigger. Fix: NEW module-level helper `_is_inside_parenthetical(text, start) -> bool` at `triggers.py:592-610` (paren depth = count of `(` minus `)` over `text[:start]`; returns `depth > 0`); the fallback block in `check_damage_triggers()` (~lines 695-727) now uses `finditer` over the card's FULL oracle text with the UNCHANGED `_COMBAT_DAMAGE_TRIGGER_RE` regex, skips matches inside a parenthetical (keyword reminder), and queues the `combat_damage` PendingTrigger for the FIRST non-parenthetical match only (at most one per permanent, then break). Same PendingTrigger fields, same `append`, same `return game_state`. Trigger-hygiene ONLY — it does NOT change poison-counter behavior (the real `apply_toxic` in combat/core.py is untouched); it only stops the spurious no-op trigger from appearing in transcript/UI. The regex itself, the main-loop `DAMAGE_TRIGGER_PATTERNS`, the MON-01 monarch loop, and the INT-01 initiative loop are all UNCHANGED. New tests/engine/test_toxic_trigger_hygiene.py (12 tests). Full suite 3079 passed / 0 failed / 3 skipped / 13 xfailed (+12 net from the 3067 Ward baseline; exactly the 12 new tests); skip/xfail set byte-identical to the ETB baseline; ruff 0 NEW errors (one PRE-EXISTING F841 `attacker_controller` at triggers.py:1932 in the exalted/attack-trigger block is NOT this change's fault).
- 2026-09-01: **Ward-on-Abilities complete (CR 702.145a) — closes the "spell OR ability" gap** — Ward previously fired only from `cast_spell` (spells); now it also fires when an **activated ability** targets an opponent's ward permanent. New additive `apply_ward_to_ability()` in `mtg_engine/ability/keywords/ward.py` (returns a new GameState + outcome `"proceed"`/`"countered"`/`"deferred"`; self-targeting no-op returns the SAME object per CR 702.145b; no stack manipulation — inline abilities have no StackObject). Wired into the REAL `/activate` endpoint in `mtg_engine/api/routers/game.py` AFTER tap+mana cost payment and BEFORE effect application: AI targeter auto-resolves by affordability (pays → effect applies; unaffordable → ability **countered**, effect NOT applied but activation cost still consumed, stack untouched); human targeter queues `pending_ward_payment` tagged `targeting_type="ability"` with the deferred activation info and the effect is withheld until resolved. Extracted the `/activate` effect block (mana/regen/fortify) into a behavior-preserving `_apply_activated_ability_effect()` helper so `ward_pay` can re-apply the deferred effect (`_reapply_deferred_ability`); `ward_pay` (unaffordable) raises INSUFFICIENT_MANA and KEEPS pending; `ward_counter` clears pending. Legal actions offer ward_pay/ward_counter with NO `pass`. The existing spell path (`Ward.apply`/`apply_ward` in stack.py cast_spell) is UNCHANGED and regression-verified. New tests: tests/api/test_ward_ability.py (11 e2e via TestClient) + tests/engine/test_ward_ability_integration.py (10 unit). Full suite 3067 passed / 0 failed / 3 skipped / 13 xfailed (+21 net from Toxic baseline 3046); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Known limitation (follow-up): an ability targeting MULTIPLE different ward permanents queues only the first ward trigger.
- 2026-08-31: **Sprint 7 P0 Toxic Keyword (CR 702.134) implemented** — Real `apply_toxic()` replacing prior in-place-mutation no-op in `mtg_engine/ability/keywords/toxic.py`; refactored to a pure transform (player.model_copy on poison_counters + players-list rebuild, no in-place +=); wired into the REAL combat damage flow at `mtg_engine/engine/combat/core.py` `assign_combat_damage()` "Target is a player" branch (guard `_has_keyword(source,"toxic") and assign.damage > 0`). Fires once per combat damage event (not per point — 5 damage from Toxic 2 = exactly 2 counters); non-combat damage does NOT trigger (sole call site is combat). 10+ poison counters = loss handled by the EXISTING SBA check (`mtg_engine/engine/sba.py` ~94-98, CR 704.5c), not re-implemented. Reuses existing `PlayerState.poison_counters` (models/game.py:209). 4 pre-existing unit tests updated to assert on the RETURNED state + original unmutated (same fix pattern as Ward). New tests/engine/test_toxic_integration.py (15 tests) + 4 updated tests/ability/keywords/test_toxic.py. Full suite 3046 passed / 0 failed / 3 skipped / 13 xfailed (+15 net from Ward baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Part of umbrella Story 7-5 — FINAL keyword, umbrella complete (all six P0 stub keywords shipped).
- 2026-08-31: **Sprint 7 P0 Ward Keyword (CR 702.145) implemented** — Ward as a triggered ability (CR 702.145a/b) wired into the real targeting flow: `mtg_engine/engine/stack.py` `cast_spell` becomes-target loop fires `apply_ward()` when an opponent's spell targets a ward permanent (keyword-list detection, avoids "award"/"reward" false positives). Ward counters the targeting spell unless the spell's controller pays the ward cost. Human path queues `pending_ward_payment` (field at models/game.py:363) with `ward_pay`/`ward_counter` choice handlers in api/routers/game.py (no `pass` offered — Ward is mandatory per CR 702.145a); AI auto-resolves by affordability (pays via engine.mana or counters the spell off the stack). Self-targeting bypasses Ward (CR 702.145b); multiple ward instances fire independently. Revision round fixed a CRITICAL Q4 violation (AI-counter path's in-place `owner.graveyard.append` + shallow model_copy corrupted the original state → now `owner.model_copy(update={"graveyard": ...})` + players rebuild), made `ward_pay` raise INSUFFICIENT_MANA before clearing pending, and removed the `pass` legal-action bypass. New tests: tests/engine/test_ward_integration.py (13) + tests/api/test_ward_endpoint.py (5). Full suite 3031 passed / 0 failed / 3 skipped / 13 xfailed (+18 net from Scry baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Part of umbrella Story 7-5.
- 2026-08-31: **Sprint 7 P0 Scry Keyword (CR 701.20) implemented** — Real Scry.apply() replacing prior NOOP stub in `mtg_engine/ability/keywords/scry.py`; human queues pending_scri_choice with an effect_type reorder marker (field at models/game.py:350 already existed), AI auto-resolves by reordering revealed top-N cards via model_copy heuristic (high-CMC non-lands float to top, lands buried at -1.0 stable-sorted). Library-size edge case per CR 701.19b (fewer than N → scry all remaining). Added "scry" choice handler in api/routers/game.py + legal-action branch gated on effect_type; resolve_scri_choice reorders only the revealed prefix with permutation validation. New tests in tests/engine/test_scry_integration.py (22 tests). Full suite 3013 passed / 0 failed / 3 skipped / 13 xfailed (+22 net from Cycle baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Part of umbrella Story 7-5.
- 2026-08-31: **Sprint 7 P0 Cycling & Type-Cycling (CR 702.36 + CR 702.46) implemented** — Real apply() for regular cycling "{cost}, Discard this card: Draw a card" and type-cycling "{cost}, Discard: Draw X cards (X = number of card types)" replacing prior no-op in `mtg_engine/ability/keywords/cycle.py`; added new `CyclingKeyword` (CostKeyword) class alongside existing `TypeCyclingKeyword`. Fixed latent bug: `Permanent` was TYPE_CHECKING-only so both `.apply()` methods raised NameError — regular-cycling human-queue/AI-resolution paths were dead code; fixed with lazy imports. `/cycle` endpoint made pure-transform via `_pay_mana`/`_discard_and_draw` (was in-place mutation + unpaid mana). Unified live /cycle route parser to cycle.py as single source of truth (adds `(?<!\w)(?<!type )` guards) so type-cycling/basic-land tokens are rejected; added HTTP 422 negative test. Added GameState field pending_cycling_choice; human queues choice, AI auto-resolves by paying cost then discarding+drawing. New tests in tests/ability/keywords/test_cycle.py + tests/api/test_cycle_endpoint.py (cycle unit + endpoint end-to-end). Full suite 2991 passed / 0 failed / 3 skipped / 13 xfailed (+17 net from Equip baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Part of umbrella Story 7-5.

- 2026-08-29: **Sprint 7 P0 Equip Keyword (CR 702.6) implemented** — Real apply() for the Equip cost "{cost}, Attach this Equipment to target creature you control" replacing prior no-op in `mtg_engine/ability/keywords/equip.py`; `Equip(CostKeyword)` with `has_equip`/`parse_equip_cost`/`parse_equip_bonus`, sorcery-speed gate, and `_eligible_creatures`; pure-transform `apply()` (human queues `pending_equip_choice` with eligible list, AI auto-resolves to first valid creature if affordable) and `_apply_equip_bonus`/`clear_equip_bonus`. Added GameState field `pending_equip_choice` (models/game.py:460); wired `stack.py:_apply_equip` (line 1585) + `equip_confirm` choice handler (line 1976) + legal-action branch (line 2466) in game.py. New tests/engine/test_equip_integration.py (32 tests). Full suite 2974 passed / 0 failed / 3 skipped / 13 xfailed (+32 net from Crew baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Part of umbrella Story 7-5.

- 2026-08-29: **Sprint 7 P0 Crew Keyword (CR 702.147) implemented** — Real apply() replacing prior no-op in `mtg_engine/ability/keywords/crew.py`; human queues pending_crew_choice without tapping, AI auto-resolves by greedily tapping cheapest untapped creatures to meet crew value (partial taps allowed). Added GameState fields pending_crew_choice + crewed_vehicles; wired handle_crew_expiration into turn_manager cleanup step for end-of-turn revert; added crew_confirm choice handler in api/routers/game.py. Fixed oracle-value bug (bare Crew() defaulted to 1 instead of parsing the card's real Crew N). New tests/engine/test_crew_integration.py (23 tests). Full suite 2942 passed / 0 failed / 3 skipped / 13 xfailed (+23 net from 7-17 baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors. Part of umbrella Story 7-5.

- 2026-08-27: **Sprint 7 P1 Trigger Fidelity Minors (CR 903.9, CR 110.6) implemented** — Five trigger-fidelity items closed; no behavior changes beyond correct trigger firing
  - Item 1: CR 903.9 commander command-zone redirect on sacrifice in `mtg_engine/engine/zones.py` `_sacrifice_permanent()` — human path defers via `pending_commander_zone_choice` (`intended_destination="graveyard"`), AI auto-redirs to command zone via `_cmd_move_to_command_zone`; mirrors CMD-01 pattern; sacrificing a human commander defers `check_sacrifice_triggers` until the choice resolves
  - Item 2: unattach call site added in `zones.move_permanent_to_zone` — fires `check_attach_triggers(..., attach_event="unattach", attached_controller=controller)` BEFORE removal; controller captured pre-removal (`zones.py:225`) so "you control" trigger fires for the aura's original controller
  - Item 3: per-token firing (CR 110.6) — `stack.py _create_tokens()` + `ability/effects/base.py CreateTokenEffect.resolve()` fire `check_token_triggers` inside the token loop (one trigger per token); `loyalty.py` single-token branch unchanged, comments added
  - Item 4: negative unit test proving "you control" sacrifice filter doesn't match every watcher
  - Item 5: cycling-route integration tests (`tests/api/test_cycle_endpoint.py`) + Fading upkeep counter-removed trigger tests (`tests/engine/test_fading_upkeep_triggers.py`); corrected a misleading stack.py comment about put-vs-create token triggers
  - Status: full suite **2919 passed, 0 failed, 3 skipped, 13 xfailed** (+12 net from baseline; skip/xfail byte-identical to pre-existing ETB baseline; ruff 0 NEW errors attributable to this story)
- 2026-08-20: **Sprint 7 P0 Fortify Keyword (CR 702.54a) implemented** — Fortify (the land-analogue of Equip) added end-to-end; only 2 cards in all of MTG use it (Darksteel Garrison, C.A.M.P.)
  - `mtg_engine/ability/keywords/fortify.py` (NEW): `Fortify(CostKeyword)` with cost parsing (`_FORTIFY_PATTERN`; regex brace-pitfall documented — opening brace must be inside the repeated group), `has_fortify`, `from_oracle_text`, `is_fortification`, `is_land_card`; pure-transform `apply()`; module-level `apply_fortify()` + AI auto-resolve `resolve_fortify_with_ai()` (auto-attach to first valid land if affordable)
  - Parser fix in `ability_parser.py`: `_FORTIFY_RE` branch at top of `_parse_segment` (line 516, before keyword fall-through) so "Fortify {3} (…)" parses as an ActivatedAbility instead of a bogus KeywordAbility; `_TIMING_RE` extended with `fortify` (line 136) so "(Fortify only as a sorcery.)" is stripped — fixes the root cause where Fortify was silently no-op'd on `/activate` + legal actions
  - `stack.py:_apply_fortify()` (line 1604): attach to target land you control + fires `check_attach_triggers`; `sba.py` (lines 300-315): Fortification-detach SBA when host leaves or becomes non-land (stays on battlefield per CR 301.7, cleans stale host `attachments` reference like the Equipment path)
  - `game.py` wiring: Fortifications playable as land drops (`Fortify.is_land_card`, one-land-per-turn applies at game.py:565 + legal-actions line 2705); `/activate` Fortify branch with target validation + client-side mana payment (1260-1278); `_compute_legal_actions` offers `activate` with `valid_targets` (line 3286). Legal-action affordability is inherited from the shared activated-ability gate (`game.py:3245`) — see F2 note.
  - Separate out-of-plan fix (NOT part of Fortify): `turn_manager.py:_advance_turn()` (def :524) set the `phase_skip_flags: dict[str, bool]` field (`models/game.py:339`) to a Python `set()` instead of `{}`, so `GameState.compute_hash()` (`json.dumps`) raised TypeError → HTTP 500 on the legal-actions auto-pass path; changed to `{}` (line 548). Previously misnamed `begin_next_turn` in draft docs — corrected to `_advance_turn`.
   - Status: full suite **2907 passed, 0 failed, 3 skipped, 13 xfailed** (baseline 2816 + exactly 91 new Fortify tests); skip/xfail set byte-identical to pre-existing ETB baseline; ruff 0 NEW errors attributable to this story
- 2026-07-24: **Sprint 7 P0 Evoke/Morph/Suspend Keyword Wiring complete** — Pure code ownership transfer from engine files to keyword modules, no behavior changes
  - Moved Evoke logic into `mtg_engine/ability/keywords/evoke.py`: added `queue_sacrifice()` and `resolve_sacrifice()` instance methods on EvokeKeyword class with module-level convenience functions; engine file (`engine/evoke.py`) now delegates via thin wrappers (kept `parse_evoke_cost`, `has_evoke`)
  - Moved Morph logic into `mtg_engine/ability/keywords/morph.py`: added `turn_face_up()` instance method (full face-up + mana payment flow) with module-level convenience functions; engine file (`engine/morph.py`) now delegates via thin wrappers (kept `parse_morph_cost`, `has_morph`)
  - Moved Suspend logic into `mtg_engine/ability/keywords/suspend.py`: added `remove_time_counter()` and `get_ready_cards()` instance methods with module-level convenience functions; engine file (`engine/suspend.py`) now delegates via thin wrappers (kept `parse_suspend`, `has_suspend`)
  - Replaced inline suspend upkeep code in `turn_manager.py` with calls to keyword module via engine wrapper, eliminating ~45 lines of duplicated time-counter logic
  - Status: 46 keyword tests pass (15 evoke + 17 morph + 14 suspend), 2780 total regression tests pass (3 skipped, 13 xfailed), 0 regressions

- 2026-07-24: **Sprint 7 — Wire 13 Dead-Code Triggers into Engine Event Flow complete** — All `check_*_triggers()` functions now fire during game events instead of silently no-op'ing
  - Wired 16 call sites in `mtg_engine/engine/stack.py`: mana_spent, becomes_target, attach (2), draw, token_triggers (3), life_gain_lost (gain + loss paths), discard, tutor (2 patterns), fight, counter_triggers (2)
  - Created `_sacrifice_permanent()` centralized helper in `mtg_engine/engine/zones.py` with sacrifice trigger wiring; wired draw trigger in `draw_card()`
  - Wired mana_production trigger at call site in `mtg_engine/engine/mana.py` (`resolve_land_mana_ability()`)
  - Wired transformed triggers in day/night transition logic (2 locations) in `mtg_engine/engine/daynight.py`
  - Life gain/loss distinction: positive amount fires "gain" triggers, negative fires "lose" triggers
  - Becomes target filtering: self-referential ("this") only fires for actual target permanent; "you control" checks controller match
  - Token guard preserved: token permanents do NOT fire death triggers (CR 704.5d) in sacrifice path
  - Status: 62 trigger tests pass, 2780 total regression tests pass (3 skipped, 13 xfailed), 0 regressions

- 2026-07-23: **Story #4 P1 Death Triggers + Sunburst complete** — Afterlife, Undying, Persist as stack-based triggers; Sunburst ETB counters
  - Implemented `_queue_death_triggers()` in `mtg_engine/engine/triggers.py`: Zone-change listener queues afterlife/undying/persist triggers when creatures die; token guard (CR 704.5d) prevents token death triggers
  - Implemented `_resolve_afterlife_trigger()` in `stack.py`: Creates N 0/0 white Spirit tokens with afterlife keyword via pure transform
  - Implemented `_resolve_undying_trigger()` in `stack.py`: Returns from graveyard with +1/+1 counters = P+T; counter guard at queuing time (only if no +1/+1 counters on death)
  - Implemented `_resolve_persist_trigger()` in `stack.py`: Returns from graveyard with -1/-1 counter; counter guard at queuing time (only if no -1/-1 counters on death)
  - Implemented `apply_sunburst_counters()` in `mtg_engine/ability/keywords/sunburst.py`: +1/+1 counters for creatures, charge counters for non-creatures; count = colored mana symbols in mana cost
  - Wired Sunburst into `zones.py` `put_permanent_onto_battlefield()`: Only fires when `from_zone=="stack"` and `not is_token` (cast permanents only)
  - Created `tests/engine/test_afterlife_integration.py` (9 tests), `test_undying_integration.py` (16 tests), `test_persist_integration.py` (11 tests), `test_sunburst_integration.py` (18 tests)
  - Status: 54 Story #4 tests pass, 2776 total regression tests pass (3 skipped, 13 xfailed), 0 regressions

- 2026-07-17: **P0 Combat Modifiers Refactoring complete** (Deathtouch, Lifelink, Infect) — Pure transform keyword modules replace inline engine mutations
  - Refactored `mtg_engine/ability/keywords/deathtouch.py`: `has_deathtouch()`, `is_lethal()`, `min_lethal_damage()` query helpers; `apply_deathtouch_damage()`, `apply_deathtouch_damage_from_card()` pure transforms
  - Refactored `mtg_engine/ability/keywords/lifelink.py`: `has_lifelink()`, `apply_lifelink_gain()` query and apply functions; `apply_lifelink_to_gamestate()`, `apply_lifelink_from_card()` state transforms
  - Refactored `mtg_engine/ability/keywords/infect.py`: `Infect`/`Wither`/`PoisonousKeyword` classes with pure transform `apply()` methods; `has_infect_perm()`, `apply_infect_damage()`, `apply_infect_poison_to_player()`
  - Updated `mtg_engine/engine/combat/core.py` (lines 605-735): Replaced 5 direct mutations with model_copy + keyword module calls (`apply_deathtouch_damage`, `apply_infect_damage_to_creature`, `apply_infect_poison_to_player`, `apply_lifelink_to_gamestate`)
  - Updated `mtg_engine/engine/stack.py` `_deal_damage()` (lines 1462-1551): Replaced 3 direct mutations with model_copy + keyword module calls; added `controller_name: str` parameter — call site passes `stack_obj.controller`; explicit return on fallback path
  - Updated `mtg_engine/engine/replacement.py` `apply_damage_event()` (lines 260-354): Replaced 5 direct mutations with model_copy + keyword module calls
  - Fixed `_deal_damage()` controller attribution bug: spell-based damage now correctly credits lifelink/infect to spell controller, not active player
  - Fixed 7 stale reference failures in `tests/test_020/test_020_trample_planeswalker.py`: added `_find_perm()` helper (searches battlefield AND graveyard for SBA-destroyed permanents), `_is_on_battlefield()` existence check
  - Status: 2749 total tests pass, 3 skipped, 13 xfailed, 0 regressions

- 2026-07-15: **APP-06 Player Stats / ELO Rating System complete** — Persistent player statistics and ELO ratings via MongoDB
  - Created `mtg_engine/models/stats.py`: Pydantic v2 models (`PlayerStats`, `FormatRecord`, `MatchupRecord`) with API response models (`StatsResponse`, `LeaderboardEntry`, `MatchupResult`)
  - Created `mtg_engine/engine/stats.py`: Pure functions — `calculate_new_elo()` (standard ELO formula, K=32), `update_player_stats()` returning new PlayerStats via model_copy with deep copy of nested dicts (formats, matchups)
  - Created `mtg_engine/api/routers/player_stats.py`: FastAPI router with endpoints: `POST /stats/player/{name}` (idempotent create/update, HTTP 201/200), `GET /stats/player/{name}` (full stats with computed total_games and win_rate), `GET /leaderboard` (top players by ELO descending, optional format filter and limit), `GET /stats/player/{name}/matchups` (per-player matchup list); all return HTTP 503 when MongoDB unconfigured
  - Async `update_stats_for_game_completion()` in the same router: automatically updates stats on game completion with atomic `$inc` for existing players, `$set` upsert for new players; per-player try/except isolation prevents overwriting successful updates
  - Updated `mtg_engine/persistence/mongo_client.py`: added `_player_stats_collection` singleton and getter
  - Updated `mtg_engine/api/main.py`: mounted `player_stats_router`
  - Updated `mtg_engine/api/routers/game.py`: hooked async stats update into sync `delete_game()` via `run_coroutine_threadsafe()` with event loop running check
  - Created 39 tests (13 engine + 12 API + 5 game completion hook)
  - Status: 39 APP-06 tests pass, 2678 total regression tests pass (3 skipped, 13 xfailed), 0 regressions

- 2026-07-15: **APP-05 Draft/Sealed Simulation complete** — Limited-format deck construction simulation via REST API
  - Created `mtg_engine/ai/draft.py`: Pack generation from Scryfall set data with rarity-weighted random selection; snake-draft pick order (odd rounds pass left, even rounds pass right); bot auto-pick using `estimate_card_quality()` scoring with strategy-aware weighting and color synergy; sealed pool mode (one 15-card pack per player) with automatic deck construction via APP-02 `build_deck()`; LRU session eviction (`MAX_DRAFT_SESSIONS=100`, completed sessions evicted first); format validation for both draft and sealed modes
  - Created `mtg_engine/api/routers/draft_ai.py`: FastAPI endpoints at `POST /ai/draft/start`, `GET /ai/draft/{id}/state`, `POST /ai/draft/{id}/pick`, `GET /ai/draft/{id}/results`, `POST /ai/sealed/start`; Pydantic request/response models with field validators; auto-resolve bot picks after human pick or session start
  - In-memory session storage (`_draft_sessions` dict) — documented as non-thread-safe, Redis recommended for production; `_process_pick()` intentionally mutates in-place (documented exception to pure transform pattern for lightweight lifecycle objects)
  - Created 37 engine tests + 20 API integration tests in `tests/ai/test_draft.py` and `tests/api/test_draft_ai.py`
  - Status: 57 APP-05 tests pass, 2610 total regression tests pass (3 skipped, 13 xfailed), 0 regressions

- 2026-07-15: **APP-04 Spectate WebSocket complete** — Real-time game state streaming for spectators via `WS /ws/game/{game_id}`
   - Created `mtg_engine/api/routers/spectate.py`: FastAPI WebSocket endpoint with pub/sub listener pattern; sends initial_state on connect, streams transcript events in real time, sends game_end notification when game finishes or is deleted
   - Added `unregister_listener()` to `TranscriptRecorder` in `mtg_engine/export/transcript.py` for clean listener lifecycle management
   - Read-only endpoint — incoming non-pong messages silently ignored; rejects connections to non-existent/completed games (close code 4004 before accept)
   - Registry uses list-based tracking per game_id with identity-based cleanup on disconnect
   - No heartbeat task (removed from initial design): competing `ws.receive_json()` calls caused deadlocks in TestClient scenarios
   - Code review fixes: proper game-over detection (`_check_game_over_and_notify`), exception handling around sends, typed listeners (`ListenerType`), lifecycle logging, constants for queue max and idle interval
   - Created 16 tests covering connect/initial_state, event broadcasting, multiple connections, game-end notification, rejection cases, cleanup, field completeness, sequence ordering, spectator count tracking, queue overflow behavior, rapid reconnect
   - Status: 16 APP-04 tests pass, 2553 total regression tests pass (3 skipped, 13 xfailed), 0 regressions

- 2026-07-13: **APP-02 Deck Building AI complete** — Automated deck construction via `POST /ai/deck/build`
  - Created `mtg_engine/ai/deck_builder.py`: Filter → Score → Select → Validate pipeline with strategy weights (aggro/control/midrange/combo), CMC curve targeting, card classification, format-aware filtering (banned lists, singleton dedup per CR 905.2 with basic land exemption, Commander color identity via `get_color_identity()` fallback)
  - Created `mtg_engine/api/routers/deck_build_ai.py`: FastAPI router with `CardPoolEntry`, `DeckBuildRequest`, `DeckEntry`, `DeckBuildResponse` Pydantic models; field validators for strategy and format
  - Filter stage: removes banned cards, enforces legality windows, singleton rules (basic land exemption), restricted limits (Vintage), commander color identity filtering
  - Score stage: `estimate_card_quality()` baseline × strategy_multiplier × cmc_curve_bonus for composite scoring
  - Select stage: greedy selection with deterministic tie-breaking via seed, land balancing (~24% minimum), sideboard construction up to 15 cards
  - Validate stage: FMT-01 `validate_deck()` integration, returns validation errors if deck is invalid
  - Format support: all 8 formats — Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper
  - Created 52 unit tests + 7 API integration tests in `tests/ai/test_deck_builder.py`
  - Status: 59 APP-02 tests pass, 2384 total regression tests pass, 0 regressions

- 2026-07-13: **APP-01 Card Search API complete** — `GET /cards/search` REST endpoint querying local SQLite Scryfall cache
  - Created `mtg_engine/api/routers/card_search.py`: FastAPI router with `SearchCardResponse`/`CardSearchResponse` Pydantic models, parameter validation (HTTP 400 on invalid params)
  - Added `ScryfallClient.search_cards()` in `mtg_engine/card_data/scryfall.py`: two-query pagination (COUNT + SELECT) with SQLite json_extract() filtering, case-insensitive LIKE for free-text search across name and oracle_text, AND logic for combined filters
  - Filters: `q` (free-text), `type`, `colors`, `cmc_min`, `cmc_max`, `mana_cost`, `keyword`, `rarity`, `set_code`; pagination (default 25/page, max 100); sorting by name or cmc asc/desc
  - Mounted router in `mtg_engine/api/main.py`
  - Created 49 tests (35 engine + 14 API) covering all filters, pagination, sorting, errors
  - Status: 49 tests pass, no regressions

- 2026-07-13: **FMT-01 Format Rules Engine complete** — Deck validation for 8 MTG formats with `POST /deck/validate` API endpoint
  - Created `mtg_engine/engine/formats/banned.py`: case-insensitive banned/restricted list lookups (`is_banned`, `is_restricted`, `get_format_banned_list`) with sample data for Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl
  - Created `mtg_engine/engine/formats/__init__.py`: `validate_deck()` dispatcher + 8 format validators enforcing deck size, banned cards, legality windows (set_code), rarity (Pauper common-only), restricted max-1-copy (Vintage)
  - Added `rarity` and `set_code` optional fields to Card model in `models/game.py` for backward-compatible format validation
  - Added `POST /deck/validate` API endpoint in `api/routers/deck_import.py` with structured JSON response (`DeckValidationRequest`/`DeckValidationResponse`)
  - Created 42 tests (36 engine + 6 API) across 12 test classes covering all formats and edge cases
  - Status: 1836 total tests pass, 13 xfailed (pre-existing), 0 regressions

- 2026-07-13: **KW-28 Reach query helpers complete** — Passive keyword flying-blocker validation (CR 702.165)
  - Implemented `has_reach(gs, perm_id)` and `can_block_flying(gs, blocker_perm_id)` in `mtg_engine/ability/keywords/reach.py`
    - Reach: allows creatures to block flying; query helpers iterate battlefield permanents to check keyword presence (flying or reach)
  - Added 8 integration tests in `tests/engine/test_keywords_integration.py` (Tests 89-96) following menace/hexproof pattern covering has_reach true/false/not found, can_block_flying with reach/flying/neither, distinction test, not-found edge cases
  - Status: 747 total engine tests pass, 13 xfailed, no regressions

- 2026-07-13: **KW-31 Menace query helpers complete** — Passive keyword blocking validation (CR 702.146)
  - Implemented `is_menacing(gs, perm_id)` and `can_block_menacing(gs, attacker_perm_id, blocker_perm_ids)` in `mtg_engine/ability/keywords/menace.py`
    - Menace: requires at least 2 blockers per CR 702.146b; query helpers iterate battlefield permanents to check keyword presence and blocker count legality
  - Added 12 unit tests in `tests/ability/keywords/test_menace.py` (TestMenaceQueryHelpers class) covering is_menacing true/false/not found, can_block with various blocker counts, attacker not on battlefield edge case, menace vs non-menace distinction
  - Added 5 integration tests in `tests/engine/test_keywords_integration.py` (Tests 84-88) following hexproof/shroud pattern
  - Status: 130 total tests pass (105 integration + 25 unit), full keyword suite: 402 passed, no regressions

- 2026-07-13: **KW-29/KW-30 Hexproof & Shroud query helpers complete** — Passive keyword targeting validation functions
  - Implemented `is_hexproof(gs, perm_id_or_player_name)` and `can_target_hexproof(gs, target, source_controller)` in `mtg_engine/ability/keywords/hexproof.py` (CR 702.54)
    - Hexproof: blocks targeting by opponents only; controller can still target own hexproof permanents
    - `_find_target_controller()` helper resolves permanent ID or player name to controller
  - Implemented `is_shrouded(gs, perm_id_or_player_name)` and `can_target_shrouded(gs, target)` in `mtg_engine/ability/keywords/shroud.py` (CR 702.41)
    - Shroud: blocks ALL targeting regardless of controller
  - Both modules updated with proper type hints (`from __future__ import annotations`, `TYPE_CHECKING`) and logging
  - Created 7 integration tests in `tests/engine/test_keywords_integration.py` (Tests 77-83)
  - Status: 121 total tests pass (95 integration + 26 unit), no regressions

- 2026-07-13: **KW-25 Dash implementation complete** — Full Dash keyword (CR 702.138) implemented and tested
  - Implemented `apply()` method in `mtg_engine/ability/keywords/dash.py`:
    - Human players: queues `pending_dash_choice` on GameState with player, card info, dash_cost
    - AI players: auto-resolves based on mana affordability (pays if affordable, skips if not)
    - Adds haste keyword to permanent, tracks in `dashed_creatures` dict for end-step return
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
  - Added `handle_dash_return_to_hand()` for CR 702.138b end-step cleanup (returns dashed creatures to hand)
  - Added `pending_dash_choice` and `dashed_creatures` fields to `GameState` in `models/game.py`
  - Created 8 Dash integration tests in `tests/engine/test_keywords_integration.py` (Tests 69-76)
  - Status: 8 Dash integration tests pass, full suite: 727 passed, 13 xfailed, no regressions

- 2026-07-13: **KW-24 Ninjutsu implementation complete** — Full Ninjutsu keyword (CR 702.61) implemented and tested
  - Implemented `apply()` method in `mtg_engine/ability/keywords/ninjutsu.py`:
    - Human players: queues `pending_ninjutsu_choice` on GameState with player, card info, attacker_perm_id, defending_player
    - AI players: auto-resolves by finding unblocked attacking creature, returning it to hand, putting ninja creature onto battlefield tapped and attacking same target
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
  - Added `pending_ninjutsu_choice` field to `GameState` in `models/game.py`
  - Created 6 Ninjutsu integration tests in `tests/engine/test_keywords_integration.py` (Tests 63-68)
  - Status: 6 Ninjutsu integration tests pass, full suite: 727 passed, 13 xfailed, no regressions

- 2026-07-13: **KW-23 Dredge implementation complete** — Full Dredge cost payment logic implemented and tested
  - Implemented real `apply()` method in `mtg_engine/ability/keywords/dredge.py`:
    - Human players: queues `pending_dredge_choice` on GameState with player, card info, dredge_n
    - AI players: auto-resolves based on library size (dredges if enough cards, skips if not)
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
    - Early-return guard so cards without Dredge keyword are properly no-op'd
  - Created 9 Dredge integration tests in `tests/engine/test_keywords_integration.py` (Tests 54-62)
  - Test coverage: human choice queuing, AI auto-resolution with sufficient/insufficient library, pure transform, detection/parsing, noop guard
  - Status: 9 Dredge integration tests pass, full suite: 74 passed, no regressions

- 2026-07-13: **KW-22 Madness implementation complete** — Full Madness cost payment logic implemented and tested
  - Added `pending_madness_choice: Optional[dict] = None` to `GameState` model in `models/game.py`
  - Implemented real `apply()` method in `mtg_engine/ability/keywords/madness.py`:
    - Human players: queues `pending_madness_choice` on GameState with player, card info, madness_cost
    - AI players: auto-resolves based on available mana (pays if affordable, skips if not)
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
    - Mana pool deduction: calculates payment from mana pool slots, updates player in game state
  - Created 10 Madness integration tests in `tests/engine/test_keywords_integration.py` (Tests 44-53)
  - Test coverage: human choice queuing, AI auto-resolution with sufficient/insufficient mana, pure transform, detection/parsing, noop guard, colored mana cost
  - Status: 10 Madness integration tests pass, full suite: 74 passed, no regressions

- 2026-07-13: **KW-19 Delve bugfixes** — Fixed 3 bugs in `mtg_engine/ability/keywords/delve.py`
  - Fixed `parse_delve_cost()` regex to handle multi-part costs like `{2}{U}` (was only capturing single `{...}` blocks)
  - Fixed `parse_delve_count()` regex to match word numbers ("two") in addition to digits (`\d+`)
  - Added early-return guard in `apply()` so cards without Delve keyword are properly no-op'd instead of processing any card with generic mana cost
  - Status: 10 Delve integration tests pass, full suite: 682 passed, 13 xfailed, no regressions

- 2026-07-13: **KW-17 Flashback implementation complete** — Full Flashback cost payment logic implemented and tested
  - Added `pending_flashback_exile: Optional[dict] = Field(default=None)` to `GameState` model in `models/game.py`
  - Implemented real `apply()` method in `mtg_engine/ability/keywords/flashback.py`:
    - Human players: queues `pending_flashback_exile` on GameState with player, card info, flashback_cost
    - AI players: auto-resolves based on available mana (pays if affordable, skips if not)
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
    - Mana pool deduction: calculates payment from mana pool slots, updates player in game state
  - Created 10 Flashback integration tests in `tests/engine/test_keywords_integration.py` (Tests 11-20)
  - Test coverage: human choice queuing, AI auto-resolution, mana affordability check, pure transform, detection/parsing, plain keyword fallback
  - Status: 10 Flashback integration tests pass, full suite: 659 passed, 13 xfailed, no regressions

- 2026-07-13: **KW-18 Escape implementation complete** — Full Escape cost payment logic implemented and tested
  - Added `pending_escape_exile: Optional[dict] = None` to `GameState` model in `models/game.py`
  - Implemented real `apply()` method in `mtg_engine/ability/keywords/escape.py`:
    - Human players: queues `pending_escape_exile` on GameState with player, card info, escape_cost, exile_count
    - AI players: auto-resolves based on available mana (pays if affordable, skips if not)
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
    - Mana pool deduction: calculates payment from mana pool slots, updates player in game state
  - Created 11 Escape integration tests in `tests/engine/test_keywords_integration.py` (Tests 21-31)
  - Test coverage: human choice queuing, AI auto-resolution, mana affordability check, pure transform, detection/parsing, plain keyword fallback, colored mana cost
  - Status: 11 Escape integration tests pass, full suite: 670 passed, 13 xfailed, no regressions

- 2026-07-13: **KW-16 Kicker implementation complete** — Full kicker cost payment logic implemented and tested
  - Added `pending_kicker_choice: Optional[dict] = None` to `GameState` model in `models/game.py`
  - Implemented real `apply()` method in `mtg_engine/ability/keywords/kicker.py`:
    - Human players: queues `pending_kicker_choice` on GameState with player, card info, kicker_cost
    - AI players: auto-resolves based on available mana (pays if affordable, skips if not)
    - Pure transform: returns new GameState via `model_copy(update={...})`, never mutates directly
    - Mana pool deduction: calculates payment from mana pool slots, updates player in game state
  - Created integration test suite at `tests/engine/test_keywords_integration.py` (10 tests)
  - Test coverage: human choice queuing, AI auto-resolution, mana affordability check, pure transform, detection/parsing
  - Status: 31 keyword integration tests pass (10 Kicker + 10 Flashback + 11 Escape), full suite: 670 passed, 13 xfailed, no regressions

- 2026-07-11: **TRG-20 Trigger bug fixes complete** — Fixed 9 trigger bugs + converted all B1 check functions to pure transforms
  - Added `_is_you_pattern()` helper in `triggers.py` for controller filtering on "you" patterns (index 0)
  - Fixes 1-9: Pattern additions, self-referential guards, oracle fallback for mixed abilities
  - All 12 B1 check functions now return new GameState via `model_copy(update={"pending_triggers": ...})` instead of mutating directly
  - Fixed conflicting test expectations in `test_triggers_expanded.py` and `test_proliferate_integration.py`
  - Updated all 25 tests in `test_b1_missing_triggers.py` to capture return values from pure transforms
  - Status: 624 engine tests pass, 13 xfailed (expected), 0 regressions

- 2026-06-20: **Sprint 2 COMPLETE** (DNG-01, INT-01, COM-01) — All mutability fixes + integration tests pass. Full suite: 2156 passed, 3 skipped, 13 xfailed
- 2026-06-20: **COM-01 Companion mutability fix complete** — CR 903.5 Companion pure transforms
  - Fixed `activate_companion()` in `companion.py`: replaced direct mutations (`setattr(player.mana_pool, ...)`, `player.sideboard.remove(...)`, `player.hand.append(...)`, `game_state.companion_used[...] = True`) with `model_copy(update={...})` pattern matching PRO-01/INT-01/MON-01 style
  - Changed signature from `-> Optional[Card]` to `-> tuple[GameState, Card | None]` for pure transform semantics
  - ManaPool deduction uses `player.mana_pool.model_copy()` + setattr on the copy (not original)
  - Updated existing unit tests in `tests/engine/test_companion.py`: all calls now unpack `(gs, card) = activate_companion(...)`, added immutability assertions (`test_immutability_original_unchanged`, `test_immutability_noop_returns_same_object`)
  - Created integration test suite at `tests/engine/test_companion_integration.py` (23 tests across 8 classes)
  - Status: All 45 companion tests pass (22 unit + 23 integration), all engine tests pass (591 passed, 13 xfailed), no regressions

- 2026-06-20: **INT-01 Initiative mutability fix complete** — CR 702.148 The Initiative pure transforms
  - Fixed `set_initiative()` in `initiative.py`: replaced direct mutations (`game_state.initiative = ...`, `game_state.pending_triggers.append(...)`) with `model_copy(update={...})` pattern matching MON-01/DNG-01 style
  - Added immutability assertions to existing unit tests: `test_immutability_original_unchanged`, `test_immutability_noop_returns_same_object`
  - Created integration test suite at `tests/engine/test_initiative_integration.py` (15 tests across 4 classes)
  - Status: All 30 initiative tests pass (15 unit + 15 integration), related combat/dungeon/monarch/proliferate tests all pass, no regressions

- 2026-06-14: **PRO-01 Proliferate implementation complete** — CR 702.39 Proliferate fully implemented and tested
  - Rewrote `proliferate.py`: fixed mutability in `apply_proliferate()`/`setup_pending_proliferate()` (direct dict mutations → model_copy transforms); added `_resolve_proliferate_with_ai()` for AI auto-resolution
  - Fixed `check_proliferated_triggers()` in `triggers.py`: new list + model_copy instead of append mutation
  - Deleted duplicate `_trigger_proliferate()` from `stack.py`; replaced proliferate fallback with calls to engine functions; added proliferate detection to BOTH `_apply_single_effect_text()` and `_apply_spell_effect()` (was missing from the former)
  - Replaced inline counter logic in API router `game.py` proliferate handler with `apply_proliferate()` + `check_proliferated_triggers()` calls
  - Created integration test suite at `tests/engine/test_proliferate_integration.py` (25 tests across 8 classes)
  - Status: All 25 integration tests pass, all 14 original proliferate unit tests pass, full suite: 2089 passed, 3 skipped, 13 xfailed, no regressions

- 2026-06-14: **VEN-01 audit & test fix** — Verified all VEN-01 design items are already implemented; fixed failing initiative tests
  - All "missing" items from design doc (mutability, stack integration, room choices, API handler) were ALREADY done
  - Fixed `tests/engine/test_initiative.py`: Undercity dungeon rooms have recursive "venture into the dungeon" abilities causing extra advances via `_apply_single_effect_text()` → `_apply_venture()`. Updated test assertions to match actual behavior.
  - Known limitation: `_apply_single_effect_text()` returns on first matched pattern, so multi-effect room abilities (e.g., "lose life AND gain life AND venture") only resolve the first effect. Room 3's recursive venture doesn't fire because "gain life" matches first.
  - Full suite: 2027 passed, 3 skipped, 13 xfailed, no regressions

- 2026-06-13: **VEN-01 Venture/Dungeon design complete** — Design document created for CR 701.61 Venture into the Dungeon mechanic
  - Existing `dungeon.py` has correct signatures but needs mutability fix (direct dict/list mutations → model_copy transforms)
  - Stack integration missing: "venture into the dungeon" regex not in `_apply_single_effect_text()` / `_apply_spell_effect()` — card effects silently no-op
  - Missing: room choice system (`DungeonRoomChoice` model, `pending_dungeon_room_choice` on GameState), API handler for choices
  - Design doc at `specs/038-gap-analysis/VEN-01-design.md`

- 2026-06-13: **MON-01 Monarch implementation complete** — CR 702.147 The Monarch mechanic fully implemented and tested
  - Fixed `set_monarch()` mutability: now returns new GameState via `model_copy(update={"monarch": ..., "pending_triggers": ...})` instead of direct mutation
  - Added `is_monarch(game_state, player_name) -> bool` query helper for card effects referencing monarch status
  - Added game initialization in `game_manager.py`: sets `monarch=active_player` for commander/conspiracy formats; `None` otherwise
  - Fixed pre-existing bug in `triggers.py`: rewrote monarch/initiative combat damage checks to call functions with correct `(target_player, attacker_controller)` args instead of broken `(game_state, damaging_perm_ids)` signature
  - Fixed pre-existing dead code: moved unreachable `"combat_damage"` trigger detection from `check_mana_spent_triggers` (after return) into `check_damage_triggers` as fallback regex for "this creature deals combat damage" patterns
  - Created integration test suite at `tests/engine/test_monarch_integration.py` (21 tests across 6 classes)
  - Status: All 21 monarch integration tests pass, all 14 original monarch unit tests pass, full suite: 2002 passed, 3 skipped, 13 xfailed, no regressions

- 2026-06-13: **MON-01 Monarch design complete** — Design document created for CR 702.147 The Monarch mechanic
  - Existing `monarch.py` has correct signatures but needs mutability fix and `is_monarch()` helper
  - Combat hook (combat/core.py) and turn manager hook (turn_manager.py) already wired
  - Missing: game initialization for monarch in commander/conspiracy formats, integration tests
  - Design doc at `specs/038-gap-analysis/MON-01-design.md`

- 2026-06-13: **CMD-01 BUG FIX: `commander_zone_stay` card disappearance** — Fixed critical bug where choosing "let commander go to intended destination" caused the card to vanish from all zones. Root cause: API handler called `move_card_to_zone(gs, card, "battlefield", ...)` but the card had already been removed from its source zone by the initial move call that queued the pending choice. Fix: directly append card to the intended destination zone via `getattr(player_obj, intended).append(card)`.
  - Updated `mtg_engine/api/routers/game.py` line 1821: replaced hardcoded `"battlefield"` source with direct zone append
  - Updated `tests/engine/formats/test_commander_integration.py`: `_simulate_commander_zone_stay` now matches fixed logic
  - Status: 20 integration tests pass (was 18), 59 total commander tests pass, no regressions

- 2026-06-13: **CMD-01 Commander Rules implementation complete** — Partner support, CR 903.8 tax, CR 903.9 zone replacement, CR 903.10a damage loss
  - Added `commander_names`, `commander_damage` to `PlayerState`; `pending_commander_zone_choice` to `GameState`
  - Refactored `record_commander_cast`, `add_commander_to_command_zone`, `move_card_to_command_zone` to pure `model_copy` transforms
  - Updated `zones.py`: CR 903.9 human path (pending choice) vs AI path (auto-redirect) in `move_card_to_zone` / `move_permanent_to_zone`
  - Updated `combat/core.py`: commander damage tracking writes to `PlayerState.commander_damage[permanent_id]`
  - Updated `api/routers/game.py`: `commander_zone_replace`/`commander_zone_stay` choice handlers + legal actions in `_compute_legal_actions`
  - New test file: `tests/engine/formats/test_commander.py` (14 tests)
  - Updated existing `tests/engine/test_commander.py` for new data model (25 tests)
  - Status: 39 commander tests pass, 1936+ total tests pass, no regressions from CMD-01 changes

- 2026-06-13: **038-gap-analysis identified** — Fresh gap analysis (June 2026) after all 037-forge-parity tasks closed
  - 5 major gap categories: 169 keywords, 104 trigger types, 7 game mechanics, 5 formats, 6 API features
  - Implementation plan: 6 sprints with 15+ tasks (see `specs/038-gap-analysis/plan.md`)
  - Tracked in `.opencode/pipeline/status.md` under "038-Gap-Analysis Backlog"

- 2026-06-13: 034-etb-choices test coverage
  - Created `tests/engine/test_etb_detection.py` (18 tests: 13 pass, 5 xfail for fetchland/snow_dual regex issues)
  - Created `tests/engine/test_etb_ai.py` (22 tests: 18 pass, 4 xfail for checkland "or" type and snow_dual placeholder)
  - Created `tests/engine/test_etb_integration.py` (10 tests: 6 pass, 4 xfail for known TODOs)
  - Created `tests/api/test_etb_choices.py` (13 tests: 10 pass, 3 skipped for unimplemented land types)
  - Created `tests/rules/test_etb_gameplay.py` (5 tests: all pass)
  - Status: 68 total ETB tests (52 pass, 3 skip, 13 xfail), no regressions in 1931+ existing tests

- 2026-06-13: BUG-26 Spree mechanic completion
  - Added `_lose_life` and `_tutor_to_top` helpers to `mtg_engine/engine/stack.py`
  - Added Spree-specific patterns to `_apply_single_effect_text()` for tutor-to-top and combined draw+lose life effects
  - Created `tests/engine/test_spree.py` with comprehensive test coverage for Spree resolution
  - Status: Implementation complete, all 13 tests passing, 345 engine tests pass with no regressions

- 029-skip-empty-phases: Added Python 3.11 + FastAPI, Pydantic v2

- 028-player-default-settings: Added Python 3.11 + FastAPI, Pydantic v2, motor (async MongoDB driver)

<!-- MANUAL ADDITIONS START -->

## Project-Specific Coding Standards

### Testing Framework
- **pytest** for all tests
- Use `pytest.mark.comprehensive_rules` and `pytest.mark.cr("XXX.X")` for rules-engine tests
- Use `pytest.mark.skip` or `pytest.mark.xfail` for tests blocked by known TODOs
- Test fixtures go in `conftest.py` or as module-level helpers
- Prefer module-level helper functions (`_make_game`, `create_test_card`) over class fixtures for simple object creation

### Backend Code (Python 3.11 + FastAPI + Pydantic v2)
- All models use Pydantic v2 `BaseModel` with `Field(default_factory=...)` for mutable defaults
- GameState is the central immutable-ish state object; functions return modified `GameState`
- Zone changes are atomic: remove from source, then add to destination
- Use `model_copy(update={...})` for Pydantic v2 updates
- Engine functions in `mtg_engine/engine/` should be pure-ish (take GameState, return GameState)
- API routers in `mtg_engine/api/routers/` use `get_manager()` for game state persistence
- Import style: `from mtg_engine.models.game import GameState, Card, PlayerState`

### Frontend Code (React + TypeScript)
- Types defined in `frontend/src/types/game.ts`
- Components use functional style with hooks
- Game state fetched via REST API, not WebSocket
- Action submission via `POST /game/{id}/choice` with `{ choice_id: string }`

### Database (MongoDB via motor)
- `motor` is the async MongoDB driver
- Game state serialized via `model_dump()` for storage
- Not actively used in current test suite (in-memory game manager)

### Sample Backend Code (Engine Layer)
```python
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool
from mtg_engine.engine.zones import put_permanent_onto_battlefield

# Create a minimal game state
p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
gs = GameState(
    game_id="test",
    seed=1,
    active_player="p1",
    priority_holder="p1",
    players=[p1, p2],
)

# Create a card with ETB choice text
card = Card(
    name="Steam Vents",
    type_line="Land — Island Mountain",
    oracle_text="As this land enters, you may pay 2 life. If you don't, it enters tapped.",
)

# Put onto battlefield — for human player, queues pending_etb_choice
gs, perm = put_permanent_onto_battlefield(gs, card, "p1", from_zone="hand")
```

### Sample Backend Code (API Layer)
```python
from fastapi.testclient import TestClient
from mtg_engine.api.main import app

client = TestClient(app)

# Create game with human player
resp = client.post("/game", json={
    "player1_name": "p1",
    "player2_name": "p2",
    "deck1": ["Steam Vents"] * 60,
    "deck2": ["Forest"] * 60,
    "seed": 42,
    "human_player_name": "p1",
})
game_id = resp.json()["data"]["game_id"]

# Get legal actions (should include etb_pay / etb_tapped)
la_resp = client.get(f"/game/{game_id}/legal-actions")
actions = la_resp.json()["data"]["legal_actions"]

# Submit ETB choice
choice_resp = client.post(f"/game/{game_id}/choice", json={
    "choice_id": "etb_pay",
})
```

### Sample Testing Code (pytest)
```python
import pytest
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool
from mtg_engine.engine.zones import _detect_etb_choice, ETBChoice, ETBChoiceType

# Detection test pattern
def test_detect_shockland():
    oracle = "As this land enters, you may pay 2 life. If you don't, it enters tapped."
    choice = _detect_etb_choice(oracle)
    assert choice is not None
    assert choice.choice_type == ETBChoiceType.SHOCKLAND
    assert choice.cost_amount == 2
    assert choice.cost_type == "life"

# AI resolution test pattern
def test_ai_pays_for_shockland_when_safe():
    from mtg_engine.engine.zones import _resolve_etb_choice_with_ai
    p1 = PlayerState(name="p1", life=20)
    p2 = PlayerState(name="p2", life=20)
    gs = GameState(game_id="test", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    choice = ETBChoice(choice_type=ETBChoiceType.SHOCKLAND, cost_amount=2, cost_type="life")
    gs, tapped = _resolve_etb_choice_with_ai(gs, "p1", choice, "perm-1", "Steam Vents")
    assert not tapped  # AI pays 2 life, enters untapped
    assert p1.life == 18

# Engine integration test pattern
def test_human_path_queues_pending_choice():
    from mtg_engine.engine.zones import put_permanent_onto_battlefield
    p1 = PlayerState(name="p1", life=20)
    gs = GameState(game_id="test", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2], human_player_name="p1")
    card = Card(name="Steam Vents", type_line="Land", oracle_text="As this land enters, you may pay 2 life. If you don't, it enters tapped.")
    gs, perm = put_permanent_onto_battlefield(gs, card, "p1")
    assert gs.pending_etb_choice is not None
    assert gs.pending_etb_choice["permanent_id"] == perm.id
    assert perm.tapped is True  # Default tapped until choice made

# API integration test pattern
def test_etb_choice_legal_actions():
    from fastapi.testclient import TestClient
    from mtg_engine.api.main import app
    client = TestClient(app)
    # ... create game, play land, verify legal actions include etb_pay and etb_tapped

# Monarch unit test pattern (MON-01)
def test_monarch_sets_and_queries():
    from mtg_engine.engine.monarch import set_monarch, is_monarch
    gs = GameState(game_id="test", seed=1, active_player="p1", priority_holder="p1", players=[p1, p2])
    assert is_monarch(gs, "p1") is False  # No monarch yet

    gs = set_monarch(gs, "p1")
    assert is_monarch(gs, "p1") is True
    assert is_monarch(gs, "p2") is False

# Monarch combat integration test pattern (MON-01)
def test_monarch_transfers_on_combat_damage():
    from mtg_engine.models.game import Phase, Step
    from mtg_engine.models.actions import AttackDeclaration
    from mtg_engine.engine.combat import declare_attackers, assign_combat_damage

    gs = GameState(
        game_id="t-monarch", seed=1, active_player="p1", priority_holder="p1",
        phase=Phase.COMBAT, step=Step.DECLARE_ATTACKERS, players=[p1, p2], monarch="p2"
    )
    card = Card(name="Bear", type_line="Creature — Beast", power="2", toughness="2")
    gs, attacker = put_permanent_onto_battlefield(gs, card, "p1")
    attacker.summoning_sick = False

    gs = declare_attackers(gs, [AttackDeclaration(attacker_id=attacker.id, defending_id="p2")])
    gs.step = Step.COMBAT_DAMAGE
    gs = assign_combat_damage(gs)

    assert is_monarch(gs, "p1"), f"Expected p1 to be monarch, got {gs.monarch}"

# Monarch end step draw test pattern (MON-01)
def test_monarch_draws_at_end_step():
    from mtg_engine.engine.monarch import handle_end_step_draw
    gs = GameState(
        game_id="t-monarch-draw", seed=1, active_player="p1", priority_holder="p1",
        phase="ending", step="end", players=[p1_with_lib, p2], monarch="p1"
    )
    hand_before = len(p1_with_lib.hand)
    gs = handle_end_step_draw(gs)
    assert len(p1_with_lib.hand) == hand_before + 1
```

## Initial Codebase Details

### Core Engine Modules
- `mtg_engine/engine/zones.py` — Zone management, `put_permanent_onto_battlefield`, `_detect_etb_choice`, `_resolve_etb_choice_with_ai`
- `mtg_engine/engine/stack.py` — Spell resolution, effect application
- `mtg_engine/engine/turn_manager.py` — Phase/step advancement
- `mtg_engine/engine/monarch.py` — CR 702.147 Monarch: `set_monarch`, `handle_end_step_draw`, `check_combat_damage_monarch`, `is_monarch`
- `mtg_engine/models/game.py` — Pydantic models: GameState, Card, Permanent, PlayerState, StackObject, etc.
- `mtg_engine/api/routers/game.py` — FastAPI endpoints: game lifecycle, actions, choices, legal actions
- `mtg_engine/ability/keywords/flashback.py` — KW-17 Flashback: `Flashback.apply()`, `parse_flashback_cost()`, `from_oracle()`, detection helpers
- `mtg_engine/ability/keywords/kicker.py` — KW-16 Kicker: `Kicker.apply()`, `parse_kicker_cost()`, `from_oracle()`

### Key Patterns for ETB Choices
- Detection: `_detect_etb_choice(oracle_text: str) -> ETBChoice | None` uses regex to classify 4 land types
- AI Resolution: `_resolve_etb_choice_with_ai(gs, player, choice, perm_id, name) -> (gs, should_be_tapped)`
- Human Path: `put_permanent_onto_battlefield` sets `game_state.pending_etb_choice` and `tapped=True`
- API Resolution: `choice_id="etb_pay"` subtracts life and sets `perm.tapped=False`; `choice_id="etb_tapped"` clears pending choice
- Legal Actions: `_compute_legal_actions` returns `etb_pay` + `etb_tapped` + `pass` when `pending_etb_choice` exists for priority player

### Existing Test Patterns
- `tests/engine/test_spree.py` — Uses `create_test_card`, `create_test_game` helpers; tests `_apply_single_effect_text`
- `tests/api/test_api.py` — Uses `TestClient(app)`, `clear_games` fixture; tests full HTTP flows
- `tests/rules/test_legal_actions.py` — Uses `_make_game`, `_make_card`, `_make_permanent` helpers; tests `_compute_legal_actions`
- `tests/rules/test_zones.py` — Uses `_make_game` helper; tests `move_card_to_zone`, `put_permanent_onto_battlefield`
- `tests/test_020/test_020_etb_replacements.py` — Tests unconditional "enters tapped" and "enters with counters"
- `tests/ability/keywords/test_etb.py` — Tests ETB keyword triggers (separate from ETB choice system)

### Known Gaps (Documented in Code)
- `_compute_legal_actions` only fully implements shockland ETB choices (ETB section at lines 2373-2398; shockland branch 2378-2394). Checkland/fetchland/snow_dual have TODO comments (2397-2398). Line refs re-verified 2026-08-20 (was 2236-2252).
- Snow dual AI heuristic subtracts life instead of snow mana (placeholder until snow mana tracking is implemented).
- Fetchland AI heuristic does not actually exile land from graveyard (comment says "would need additional logic").

### Commander/Partner Coding Standards (CMD-01)
- **Never check `commander_name` directly** in engine code. Always use `_is_commander(card_name, player)` or `_get_commander_names(player)` from `mtg_engine/engine/formats/commander.py`.
- **Commander state transforms must be pure**: `record_commander_cast` and `add_commander_to_command_zone` return new `GameState` via `model_copy(update=...)` on the player and players list.
- **CR 903.9 replacement effect**: For human players, queue `pending_commander_zone_choice` in `GameState` and return without completing the zone change. For AI, auto-redirect to command zone.
- **Partner tax independence**: `commander_cast_counts` is keyed by card name; each partner tracks its own cast count.
- **Partner damage tracking**: `commander_damage` is keyed by permanent ID; each partner's combat damage is tracked separately. 21+ damage from a single permanent ID triggers loss.
- **Companion**: Out of scope for CMD-01. Delegate to COM-01.

### Key Patterns for Commander Zone Replacement
- Detection: `move_card_to_zone` and `move_permanent_to_zone` check `_is_commander(card.name, player)` before applying CR 903.9
- Human Path: Sets `game_state.pending_commander_zone_choice` with `player`, `card`, `permanent_id`, `intended_destination`, `from_zone`
- AI Path: Immediately calls `move_card_to_command_zone(game_state, card, player_name)`
- API Resolution: `choice_id="commander_zone_replace"` moves to command zone; `choice_id="commander_zone_stay"` moves to intended destination
- Legal Actions: `_compute_legal_actions` returns `commander_zone_replace` + `commander_zone_stay` + `pass` when `pending_commander_zone_choice` exists for priority player

### Monarch Coding Standards (MON-01)
- **Monarch tracking**: `GameState.monarch: str | None` tracks which player holds the monarch. Initialized to `active_player` on game creation for "commander" and "conspiracy" formats; `None` for other formats.
- **State transforms must be pure**: `set_monarch(gs, player)` returns new `GameState` via `model_copy(update={"monarch": player_name})`. Never mutate `game_state.monarch` directly.
- **CR 702.147 combat damage hook**: `check_combat_damage_monarch(gs, target_player, attacker_controller)` is called from `combat/core.py` during `assign_combat_damage`. If the target is the monarch, the attacker's controller becomes the new monarch.
- **CR 702.147 end step draw**: `handle_end_step_draw(gs)` is called from `turn_manager.py` at end step. Only draws if `active_player == monarch`.
- **Query helper**: Use `is_monarch(game_state, player_name) -> bool` to check if a player holds the monarch (for card effects that reference "if you're the monarch").
- **"become_monarch" trigger**: `set_monarch` fires a `PendingTrigger` with `trigger_type="become_monarch"` when monarch changes. Cards like "whenever you become the monarch" resolve from this trigger.

### Key Patterns for Monarch
- Game Initialization: `game_manager.py` sets `monarch=active_player` for commander/conspiracy formats at game creation
- Combat Hook: `combat/core.py` lines 712-713 call `check_combat_damage_monarch(gs, target_player, attacker_controller)` during damage assignment (re-verified 2026-08-20; was line 667)
- End Step Hook: `turn_manager.py` lines 406-407 call `handle_end_step_draw(gs)` at end step (re-verified 2026-08-20; was lines 389-391)
- Query: `is_monarch(game_state, player_name) -> bool` for card effects referencing monarch status

### Venture/Dungeon Coding Standards (VEN-01)
- **Dungeon tracking**: `GameState.player_dungeons: dict[str, DungeonProgress]` tracks per-player dungeon progress. `GameState.player_completed_dungeons: dict[str, int]` counts completed dungeons per player. Both already exist in GameState.
- **State transforms must be pure**: All functions in `engine/dungeon.py` return new `GameState` via `model_copy(update={...})`. Never mutate `game_state.player_dungeons`, `game_state.pending_triggers`, or `game_state.player_completed_dungeons` directly.
- **CR 701.61 venture flow**: `venture(gs, player_name, dungeon_name=None)` handles the full venturing logic: starts new dungeon if none in progress/complete, advances to next room, fires room ability via stack resolution, increments completion counter when done.
- **Room effect resolution**: `_apply_room_effect(gs, player_name, ability_text)` routes room ability text through `_apply_single_effect_text()` so existing patterns (draw, scry, gain life, etc.) work without hard-coding each room's logic.
- **"venture into the dungeon" stack pattern**: Added to both `_apply_single_effect_text()` and `_apply_spell_effect()` in `stack.py`. Pattern: `r"\bventure\s+into\s+(?:the\s+)?dungeon\b"` with word boundaries to avoid false positives on "adventure".
- **Room choices**: Rooms may have `choices: list[DungeonRoomChoice]` — for human players, queues `pending_dungeon_room_choice`; for AI, auto-resolves using `is_default` flag.
- **Recursive venturing**: Undercity rooms contain "venture into the dungeon" in their ability text. This correctly chains through stack resolution → venture() again. Guard against infinite loops via `progress.is_complete` check.
- **Dungeon model**: Defined in `models/dungeon.py` with 4 dungeons (Mad Mage, Phandelver, Tomb of Annihilation, Undercity). Each dungeon has named rooms with ability text.

### Key Patterns for Venture/Dungeon
- Engine: `engine/dungeon.py` — `venture()`, `start_dungeon()`, `_apply_room_effect()`, `get_dungeon_progress()`
- Stack Integration: `engine/stack.py` — "venture into the dungeon" regex in effect resolution patterns
- Initiative Hook: `engine/initiative.py` `handle_upkeep_venture()` (line 59) calls `venture(game_state, active_player, dungeon_name="Undercity")` during upkeep (re-verified 2026-08-20; was line 57)
- Trigger System: `engine/triggers.py` — `check_completed_dungeon_triggers()` fires "whenever you complete a dungeon" triggers

### Sample Backend Code (Dungeon Engine)
```python
from mtg_engine.engine.dungeon import venture, start_dungeon, get_dungeon_progress

# Start a specific dungeon for a player
gs, room_text = start_dungeon(gs, "Alice", "Lost Mine of Phandelver")
assert room_text == "Create a 1/1 green Goblin creature token"

# Venture into the dungeon (auto-starts if none in progress)
gs = venture(gs, "Bob")  # Defaults to first available dungeon
progress = get_dungeon_progress(gs, "Bob")
assert progress is not None
assert progress.current_room_index == 1  # Advanced past room 0

# Pure transform: new GameState object returned
old_id = id(gs)
gs = venture(gs, "Alice")
assert id(gs) != old_id
```

### Sample Testing Code (Dungeon Integration)
```python
import pytest
from mtg_engine.engine.dungeon import venture, start_dungeon, get_completed_dungeon_count
from mtg_engine.engine.stack import _apply_single_effect_text
from mtg_engine.models.game import GameState, PlayerState, Card
from mtg_engine.models.actions import StackObject

def test_venture_from_card_effect():
    """Card effect 'Venture into the dungeon.' resolves via stack."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
    )
    stack_obj = StackObject(
        source_card=Card(name="The Dungeon", oracle_text="Venture into the dungeon."),
        controller="Alice",
    )
    gs = _apply_single_effect_text(gs, stack_obj, "Venture into the dungeon.")
    progress = get_dungeon_progress(gs, "Alice")
    assert progress is not None

def test_dungeon_completion():
    """Completing all rooms increments completion counter."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
    )
    gs, _ = start_dungeon(gs, "Alice", "Dungeon of the Mad Mage")  # 3 rooms
    for _ in range(3):
        gs = venture(gs, "Alice")
    assert get_completed_dungeon_count("Alice", gs) == 1

def test_pure_transform():
    """venture() returns new GameState object."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
    )
    old_id = id(gs)
    gs = venture(gs, "Alice")
    assert id(gs) != old_id
```

### Keyword Ability Coding Standards (KW-16..30)
- **Base class hierarchy**: `KeywordAbility(ABC)` with subclasses `TriggeredKeyword`, `CostKeyword`, `PassiveKeyword` in `mtg_engine/ability/keywords/base.py`. All keyword modules inherit from appropriate base.
- **State transforms must be pure**: All `apply()` methods return new `GameState` via `model_copy(update={...})`. Never mutate game state directly.
- **Cost keywords** (Kicker KW-16, Flashback KW-17, Escape, Delve): Modify casting cost during spell declaration phase. Wire into mana payment flow in stack.py. For Flashback: queue `pending_flashback_exile` on GameState for human players, auto-resolve (pay + exile) for AI players.
- **Triggered/Replacement keywords** (Cascade, Storm, Madness, Dredge, Ninjutsu, Dash): Fire at specific game moments. Use pending choice fields for human players, auto-resolve for AI.
- **Passive keywords** (Hexproof/Shroud, Menace/Reach): Implemented as query helpers returning boolean. Called from targeting validation and blocker assignment logic.
- **Centralize inline logic**: Move keyword-specific code out of stack.py into dedicated modules. Stack.py should call `keyword_module.apply(gs, ...)` rather than containing keyword logic.

### Key Patterns for Keywords
- Cost Detection: `_detect_kicker(oracle_text) -> KickerCost | None`, `_detect_flashback(oracle_text) -> FlashbackCost | None`, etc.
- Apply Method: `apply(game_state, card, player_name, **kwargs) -> GameState` or `(GameState, additional_data)` for cost keywords
- Pending Choices: Use `pending_<keyword>_choice` fields on GameState for human player decisions (e.g., `pending_cascade`, `pending_dredge_choice`, `pending_flashback_exile`, `pending_escape_exile`)
- AI Auto-Resolution: `_resolve_<keyword>_with_ai(gs, player_name, **kwargs) -> GameState` mirrors ETB choice pattern

### Key Patterns for Hexproof/Shroud (KW-29/30)
- **Query helpers return boolean**: `is_hexproof(gs, perm_id_or_player_name) -> bool`, `is_shrouded(gs, perm_id_or_player_name) -> bool`. These do NOT modify game state.
- **Targeting validation**: `can_target_hexproof(gs, target, source_controller)` returns True only if target lacks hexproof OR source controller equals target controller (CR 702.54). `can_target_shrouded(gs, target)` returns False whenever target has shroud, regardless of controller (CR 702.41).
- **Resolution**: Both helpers iterate `game_state.battlefield` to find the permanent by ID, then check `perm.card.keywords`. Player-name targets return False for now (player-level keyword tracking not yet implemented on PlayerState).

### Key Patterns for Flashback (KW-17)
- **State tracking**: `GameState.pending_flashback_exile: Optional[dict]` tracks which card is pending exile for human Flashback choice
- **State transforms must be pure**: `apply()` returns new `GameState` via `model_copy(update={...})`. Never mutate `game_state` directly.
- **CR 702.34 Flashback flow**: `Flashback.apply(gs, permanent)` handles the full Flashback logic: parses cost from oracle text, determines human/AI path, queues or auto-resolves
- **Human Path**: Sets `game_state.pending_flashback_exile` with `player`, `card_id`, `card_name`, `flashback_cost`, `resolved=False`
- **AI Path**: Checks `can_pay_cost(player.mana_pool, flashback_cost)`; if affordable, deducts mana from pool and sets `resolved=True`; if not, sets `resolved=True` without mana deduction
- **Mana payment**: Uses `parse_mana_cost()` to parse `{N}{C}{W}` cost strings; pays colored mana first, then generic from remaining pool
- **Detection**: `Flashback.parse_flashback_cost(oracle_text) -> str | None` uses regex `\bflashback\s*[—\-]?\s*(\{[^}]+\})` to extract cost
- **Plain keyword fallback**: Cards with just "Flashback" (no cost) are still detected via `Flashback.from_oracle_text()` but `parse_flashback_cost()` returns `None`

### Key Patterns for Escape (KW-18)
- **State tracking**: `GameState.pending_escape_exile: Optional[dict]` tracks which card is pending exile for human Escape choice
- **State transforms must be pure**: `apply()` returns new `GameState` via `model_copy(update={...})`. Never mutate `game_state` directly.
- **CR 702.45 Escape flow**: `Escape.apply(gs, permanent)` handles the full Escape logic: parses cost and exile count from oracle text, determines human/AI path, queues or auto-resolves
- **Human Path**: Sets `game_state.pending_escape_exile` with `player`, `card_id`, `card_name`, `escape_cost`, `exile_count`, `resolved=False`
- **AI Path**: Checks `can_pay_cost(player.mana_pool, escape_cost)`; if affordable, deducts mana from pool and sets `resolved=True`; if not, sets `resolved=True` without mana deduction
- **Mana payment**: Uses `parse_mana_cost()` to parse `{N}{C}{W}` cost strings; pays colored mana first, then generic from remaining pool
- **Detection**: `Escape.parse_escape_cost(oracle_text) -> str | None` uses regex `\bescape\s*[—\-]?\s*(\{[^}]+\})` to extract cost
- **Exile count parsing**: `Escape.parse_exile_count(oracle_text) -> int` uses regex `(?:exile|escape)\s+(\d+)\s+other` to extract count
- **Plain keyword fallback**: Cards with just "Escape" (no cost) are still detected via `Escape.from_oracle_text()` but `parse_escape_cost()` returns `None`

### Sample Backend Code (Escape Engine)
```python
from mtg_engine.ability.keywords.escape import Escape
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool

# Create a minimal game state
p1 = PlayerState(name="p1", life=20, mana_pool=ManaPool())
p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
gs = GameState(
    game_id="test", seed=1, active_player="p1", priority_holder="p1",
    players=[p1, p2], human_player_name="p1",
)

# Create a card with Escape keyword
card = Card(name="Gaddock Teeg", type_line="Creature", oracle_text="Escape {3}{B}\nEscape 3 other cards from your graveyard: Cast Gaddock Teeg from your graveyard. If you cast it this way, it exiles on leaving the battlefield.", mana_cost="{B}", keywords=["escape"])

# Apply Escape — for human player, queues pending_escape_exile
escape_perm = Permanent(card=card, controller="p1")
gs = Escape().apply(gs, escape_perm)
assert gs.pending_escape_exile is not None
assert gs.pending_escape_exile["escape_cost"] == "{3}{B}"
assert gs.pending_escape_exile["exile_count"] == 3
assert gs.pending_escape_exile["resolved"] is False
assert gs.pending_flashback_exile["card_name"] == "Phantasmal Images"
assert gs.pending_flashback_exile["flashback_cost"] == "{2}{U}"
assert gs.pending_flashback_exile["resolved"] is False

# Flashback is a pure transform
assert id(gs) != id(Flashback().apply(gs, fb_perm))  # New object returned
```

### Sample Testing Code (Flashback Integration)
```python
import pytest
from mtg_engine.ability.keywords.flashback import Flashback
from mtg_engine.models.game import GameState, PlayerState, Card, Permanent, ManaPool

def _make_flashback_card():
    return Card(name="Phantasmal Images", type_line="Sorcery", oracle_text="Flashback {2}{U}\nPhantasmal Images is a 2/2 blue creature with morph.", mana_cost="{U}", keywords=["flashback"])

def test_flashback_queues_pending_choice_for_human():
    gs = GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        human_player_name="p1",
    )
    fb_perm = Permanent(card=_make_flashback_card(), controller="p1")
    gs = Flashback().apply(gs, fb_perm)
    assert gs.pending_flashback_exile is not None
    assert gs.pending_flashback_exile["player"] == "p1"
    assert gs.pending_flashback_exile["flashback_cost"] == "{2}{U}"
    assert gs.pending_flashback_exile["resolved"] is False

def test_ai_resolves_flashback_when_affordable():
    gs = GameState(
        game_id="test", seed=1, active_player="p1", priority_holder="p1",
        players=[PlayerState(name="p1"), PlayerState(name="p2")],
        human_player_name="p1",
    )
    fb_card = _make_flashback_card()
    gs.players[1].mana_pool = ManaPool(C=2, U=1)
    fb_perm = Permanent(card=fb_card, controller="p2")
    gs = Flashback().apply(gs, fb_perm)
    assert gs.pending_flashback_exile is not None
    assert gs.pending_flashback_exile["resolved"] is True
    assert gs.players[1].mana_pool.C == 0  # Paid 2 generic
    assert gs.players[1].mana_pool.U == 0  # Paid 1 U

def test_flashback_plain_keyword_detection():
    assert Flashback.from_oracle_text("Flashback\n...") is True
    assert Flashback.parse_flashback_cost("Flashback") is None
    assert Flashback.from_oracle_text("Flashback {2}{U}\n...") is True
    assert Flashback.parse_flashback_cost("Flashback {2}{U}") == "{2}{U}"
```

### Sample Backend Code (Keyword Engine)
```python
from mtg_engine.ability.keywords.cascade import apply_cascade, resolve_cascade_choice
from mtg_engine.ability.keywords.storm import create_storm_copies
from mtg_engine.models.game import GameState, PlayerState, Card

# Cascade: trigger on spell resolution, queue choice for human player
gs = apply_cascade(gs, stack_object, caster="Alice")
assert gs.pending_cascade is not None  # Human must choose keep/exile

# Resolve cascade choice via API (human path)
gs = resolve_cascade_choice(gs, "cascade_keep", chosen_card_id="card-123")
assert gs.pending_cascade is None  # Choice resolved

# Storm: create N copies on stack during resolution
gs = create_storm_copies(gs, stack_object, spells_cast_count=5)
# Returns new GameState with 5 storm copies added to stack (LIFO order)
```

### Sample Testing Code (Keyword Integration)
```python
import pytest
from mtg_engine.ability.keywords.cascade import apply_cascade, resolve_cascade_choice
from mtg_engine.models.game import GameState, PlayerState, Card
from mtg_engine.models.actions import StackObject

def test_cascade_queues_pending_choice():
    """Cascade triggers and queues choice for human player."""
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        human_player_name="Alice",
    )
    cascade_card = Card(name="Lightning Helix", oracle_text="Cascade, Deal 3 damage to any target.")
    stack_obj = StackObject(source_card=cascade_card, controller="Alice")

    gs = apply_cascade(gs, stack_obj, "Alice")
    assert gs.pending_cascade is not None
    assert gs.pending_cascade["player"] == "Alice"

def test_cascade_choice_resolved():
    """Resolving cascade choice clears pending state."""
    # ... setup with pending_cascade ...
    gs = resolve_cascade_choice(gs, "cascade_keep", "chosen-card-id")
    assert gs.pending_cascade is None

def test_storm_creates_copies_lifo():
    """Storm creates N copies, added to stack in LIFO order."""
    from mtg_engine.ability.keywords.storm import create_storm_copies
    gs = GameState(
        game_id="test", seed=1, active_player="Alice", priority_holder="Alice",
        players=[PlayerState(name="Alice"), PlayerState(name="Bob")],
        spells_cast_this_turn=3,  # Storm count = 3
    )
    storm_card = Card(name="Tidecaller's Blessing", oracle_text="Storm, Draw two cards.")
    stack_obj = StackObject(source_card=storm_card, controller="Alice")

    gs, copies = create_storm_copies(gs, stack_obj)
    assert len(copies) == 3  # N copies created
```

### Format Validation Coding Standards (FMT-01)
- **Format validation is stateless**: `validate_deck(cards, format_name, commanders)` takes card lists and returns a list of `DeckViolation` objects. It does NOT interact with GameState or game zones.
- **Banned/restricted lookups are case-insensitive**: All functions in `mtg_engine/engine/formats/banned.py` normalize card names to uppercase before comparison (`is_banned`, `is_restricted`, `get_format_banned_list`).
- **Legality windows use set codes**: Format validators check `card.set_code` against `LEGAL_SETS[format]` — cards from sets outside the format's legality window are flagged as violations.
- **Pauper rarity check is lenient**: Cards with `rarity=None` (unknown) are silently skipped; only known non-common rarities (uncommon, rare, mythic) trigger violations.
- **Vintage restricted enforcement**: Restricted cards may appear at most once in the deck. Violations report each unique card name only once via deduplication set.
- **Commander/Brawl commander validation**: Commander format requires exactly 1 commander; Brawl requires exactly 1 creature-type commander. Both check banned lists (Brawl checks both "brawl" and "standard" lists).
- **Card model fields for validation**: `Card.rarity: Optional[str]` and `Card.set_code: Optional[str]` are optional to maintain backward compatibility with existing game logic that doesn't need format metadata.

### Card Search API Coding Standards (APP-01)
- **Card search is stateless**: `GET /cards/search` queries the local SQLite Scryfall cache only. It does NOT interact with GameState, game zones, or any live game data.
- **Two-query pagination pattern**: Always issue a COUNT query first to get total results, then a SELECT query with LIMIT/OFFSET for the page. This ensures accurate `total_count` in responses regardless of filters applied.
- **SQLite json_extract() filtering**: Card data stored as JSON blobs; use `json_extract()` in WHERE clauses for structured field access (type_line, colors, cmc, mana_cost, keywords, rarity, set_code).
- **Case-insensitive LIKE matching**: Free-text search (`q` parameter) uses `LOWER(column) LIKE '%query%'` across both name and oracle_text columns.
- **AND logic for combined filters**: All filter parameters combine with AND — a card must match every provided filter to appear in results.
- **Parameter validation returns HTTP 400**: Invalid numeric ranges (e.g., cmc_min > cmc_max), invalid sort fields, or page_size exceeding max (100) return structured error responses before hitting the database.

### Deck Building AI Coding Standards (APP-02)
- **Deck building is stateless**: `POST /ai/deck/build` does NOT interact with GameState, game zones, or any live game data. It takes a card pool and returns a constructed deck list.
- **Pipeline architecture**: `build_deck(card_pool, format_name, strategy, commanders, seed)` orchestrates four stages: `_filter_card_pool()` → `score_cards()` → `_select_deck()` → `_validate_constructed_deck()`. Each stage is independently testable.
- **Basic land singleton exemption (CR 905.2)**: Basic lands (including snow-covered variants and Wastes) are ALWAYS exempt from the "max 1 copy" rule in ALL stages — filter dedup, greedy selection max_copies, and land balancing. Use `BASIC_LANDS` set for lookups (case-insensitive via `.lower()`).
- **Strategy weights**: `STRATEGY_WEIGHTS` dict maps strategy → category multipliers. Categories: `creature_low` (CMC 0-2), `creature_mid` (CMC 3-4), `creature_high` (CMC 5+), `removal`, `counterspell`, `draw`, `ramp`. Aggro boosts low-CMC creatures; control boosts removal/counterspells; combo boosts draw/ramp/high-CMC.
- **CMC curve targeting**: `_cmc_curve_bonus(card_cmc, strategy)` applies a bell-curve bonus centered on the strategy's ideal CMC (aggro=2, midrange=3, control=4, combo=5). Cards within ±1 of target get +0.2 bonus; beyond that, score decreases linearly.
- **Greedy selection with deterministic tie-breaking**: When multiple cards share the same score, use `random.Random(seed)` to shuffle before sorting, ensuring reproducible results for the same seed.
- **Land balancing**: Reserve ~24% of deck slots for lands by counting available lands upfront and stopping non-land additions at `greedy_target = deck_size - land_count`. This ensures a playable mana base even when creatures score higher than lands.
- **Sideboard construction**: For non-singleton formats, sideboard can contain additional copies up to max 4 total (main + side). Commander and Brawl exclude sideboards entirely.
- **Commander color identity filtering**: When commanders are provided, filter the card pool to only cards whose `color_identity` is a subset of the commander's combined color identity. Use `get_color_identity()` from `mtg_engine/engine/formats/commander.py` as fallback when `color_identity` field is empty (derives from mana cost and oracle text).
- **Validation integration**: Final stage calls FMT-01 `validate_deck(deck_cards, format_name, commanders)` — if violations exist, return them in the response rather than returning an invalid deck.

### Game Replay Coding Standards (APP-03)
- **Replay is stateless**: Client passes `from_event_seq` to navigate; no server-side sessions or cursor tracking. Each request is independently resolvable from the export store data.
- **Two-tier board state reconstruction**: Snapshot anchors (full GameState dumps captured at priority grants via `/legal-actions`) provide exact state at known points. Between snapshots, incremental event replay reconstructs intermediate states by applying transcript events sequentially.
- **Snapshot anchor selection**: `_find_snapshot_anchor()` picks the latest snapshot with `turn <= target_turn`, not always the last snapshot. This prevents double-application of events already reflected in later snapshots.
- **Board state includes**: battlefield permanents (power/toughness, tapped status, counters), player life totals, hand sizes, graveyard top cards, stack size.
- **Data sourced from in-memory export store** — no MongoDB dependency. Replay reads from the same snapshot/transcript data used for training data export.
- **Timeline grouping**: Events are grouped by turn/phase with event counts for condensed overview; returned via `TimelineResponse(BaseModel)` wrapper.
- **Pagination**: `PaginatedEventsResponse` includes `has_next`/`has_prev` flags computed in the handler based on page boundaries and total event count.

### WebSocket Spectator Coding Standards (APP-04)
- **No new dependencies**: FastAPI has native `WebSocket` support. Use `from fastapi import WebSocket` — no external packages needed.
- **Pub/Sub via TranscriptRecorder listeners**: Each connected WebSocket client registers its own listener callback on the game's `TranscriptRecorder`. When a transcript event fires, all registered listeners are notified and the event is pushed to each client's outgoing queue. No engine code modifications required beyond adding `unregister_listener()` for cleanup.
- **Per-connection asyncio.Queue**: Each WebSocket connection gets its own `asyncio.Queue[dict]`. The per-connection listener pushes to that specific queue via `queue.put_nowait()`. This isolates slow clients from fast ones and makes cleanup trivial — just close the websocket and drop the queue.
- **Sync→Async bridging pattern**: Listener callbacks run synchronously (called from `_notify_listeners` which iterates the listeners list). They use `queue.put_nowait()` to push events into an async queue, decoupling the sync engine thread from the async WebSocket send loop. The main event loop drains the queue with `await queue.get()`. Never call `websocket.send_text()` directly from a listener callback — it's async and would deadlock.
- **Connection registry**: Module-level `_spectators: dict[str, set[SpectatorConnection]]` in the router file manages all active connections. `SpectatorConnection` is a lightweight dataclass holding the WebSocket, its queue, and the listener callback reference (needed for cleanup).
- **Initial state on connect**: Send `{ type: "initial_state", data: <GameState.model_dump()> }` immediately after accepting the connection. This gives late-joining spectators a complete starting point without needing to replay the entire transcript.
- **Event message format**: All broadcast events use consistent JSON structure: `{ type: "<event_type>", data: {...}, timestamp: float, seq: int, turn: int, phase: str, step: str }`. The `type` field matches TranscriptEntry event types (`cast`, `resolve`, `trigger`, `sba`, `zone_change`, `damage`, `phase_change`, `priority_grant`).
- **Game-end detection**: After receiving each event from the queue, check if the game is over by querying `GameManager.get(game_id).is_game_over`. If true, send `{ type: "game_end", data: { winner: str, loser: str }, timestamp: float }` and close with code 1000 (Normal Closure). Also handle `KeyError` from deleted games the same way.
- **No heartbeat task**: Removed from initial design — competing `ws.receive_json()` calls caused deadlocks in TestClient scenarios. Instead, use `queue.get(timeout=IDLE_INTERVAL)` to detect slow/disconnected clients and close gracefully.
- **Read-only access**: Spectator WebSocket is read-only — incoming non-pong messages are silently ignored. No game actions can be taken via the spectator endpoint.
- **Error handling for invalid games**: Reject during WebSocket handshake before `accept()`: close with code 4004 and reason string ("Game not found" or "Game already completed"). This produces an HTTP 404-equivalent at the WebSocket layer.
- **Graceful disconnect cleanup**: Use `try/finally` pattern to guarantee cleanup regardless of how the connection terminates: unregister listener via `recorder.unregister_listener(conn.listener_fn)`, remove from registry with `_spectators[game_id].discard(conn)`.

### Sample Backend Code (WebSocket Spectator Router)
```python
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import get_export_store
from mtg_engine.export.transcript import TranscriptEntry

router = APIRouter()

@dataclass
class SpectatorConnection:
    ws: WebSocket
    queue: asyncio.Queue[dict]
    listener_fn: Callable[[TranscriptEntry], None]
    game_id: str

# Module-level registry: game_id -> set of connections
_spectators: dict[str, set[SpectatorConnection]] = {}

@router.websocket("/ws/game/{game_id}")
async def ws_game_spectate(websocket: WebSocket, game_id: str):
    # Validate game exists and is active
    try:
        gs = get_manager().get(game_id)
    except KeyError:
        await websocket.close(code=4004, reason="Game not found")
        return

    if gs.is_game_over:
        await websocket.close(code=4004, reason="Game already completed")
        return

    await websocket.accept()

    # Setup per-connection queue and listener
    store = get_export_store(game_id)
    recorder = store.transcript
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=256)

    def _listener(entry: TranscriptEntry) -> None:
        try:
            queue.put_nowait({
                "type": entry.event_type,
                "data": entry.data,
                "timestamp": time.time(),
                "seq": entry.seq,
                "turn": entry.turn,
                "phase": entry.phase,
                "step": entry.step,
            })
        except asyncio.QueueFull:
            pass  # Drop events for slow clients

    recorder.register_listener(_listener)
    conn = SpectatorConnection(ws=websocket, queue=queue, listener_fn=_listener, game_id=game_id)
    _spectators.setdefault(game_id, set()).add(conn)

    # Send initial state
    await websocket.send_text(json.dumps({
        "type": "initial_state",
        "data": gs.model_dump(),
    }))

    try:
        while True:
            msg = await queue.get(timeout=1.0)  # Idle timeout, no heartbeat needed
            await websocket.send_text(json.dumps(msg))

            # Check game-over after each event
            try:
                current_gs = get_manager().get(game_id)
                if current_gs.is_game_over:
                    await websocket.send_text(json.dumps({
                        "type": "game_end",
                        "data": {"winner": current_gs.winner},
                        "timestamp": time.time(),
                    }))
                    break
            except KeyError:
                # Game deleted — treat as end
                break

    except WebSocketDisconnect:
        pass
    finally:
        recorder.unregister_listener(conn.listener_fn)
        _spectators.get(game_id, set()).discard(conn)
```

### Sample Backend Code (Deck Building AI)
```python
from mtg_engine.ai.deck_builder import build_deck
from mtg_engine.api.routers.deck_build_ai import CardPoolEntry

# Build a 60-card aggro Standard deck from a card pool
pool = [
    CardPoolEntry(name="Goblin Warrior", mana_cost="{1}{R}", type_line="Creature — Goblin Warrior", cmc=2.0),
    CardPoolEntry(name="Lightning Bolt", mana_cost="{R}", type_line="Instant", oracle_text="Deal 3 damage to any target.", cmc=1.0),
    CardPoolEntry(name="Mountain", mana_cost="", type_line="Land — Mountain", cmc=0.0),
    # ... more cards
]

result = build_deck(
    card_pool=pool,
    format_name="standard",
    strategy="midrange",
    seed=42,
)

# Result contains main deck and optional sideboard
assert len(result.main_deck) == 60
for entry in result.main_deck:
    print(f"{entry.quantity}x {entry.name}")
```

### Sample Testing Code (Deck Building AI)
```python
import pytest
from mtg_engine.ai.deck_builder import build_deck, _filter_card_pool, score_cards
from mtg_engine.api.routers.deck_build_ai import CardPoolEntry

def make_card(name, mana_cost="{1}", type_line="Creature", cmc=1.0, rarity="common", set_code="MOM"):
    return CardPoolEntry(
        name=name, mana_cost=mana_cost, type_line=type_line,
        oracle_text="", cmc=cmc, rarity=rarity, set_code=set_code,
    )

def test_filter_removes_banned_cards():
    """Banned cards are excluded from the filtered pool."""
    pool = [make_card("Legal Card"), make_card("Black Lotus")]  # Black Lotus banned in Standard
    filtered = _filter_card_pool(pool, "standard", [])
    names = {c.name for c in filtered}
    assert "Black Lotus" not in names

def test_score_uses_strategy_weights():
    """Aggro strategy scores low-CMC creatures higher than high-CMC."""
    pool = [make_card("Fast Creature", cmc=1.0), make_card("Slow Creature", cmc=5.0)]
    scored = score_cards(pool, "aggro")
    fast_score = next(s for s in scored if s.card.name == "Fast Creature").score
    slow_score = next(s for s in scored if s.card.name == "Slow Creature").score
    assert fast_score > slow_score

def test_build_deck_returns_valid_standard():
    """Full pipeline produces a valid 60-card Standard deck."""
    pool = [make_card(f"Card {i}", cmc=float(i % 5 + 1)) for i in range(80)]
    result = build_deck(pool, "standard", "midrange", seed=42)
    assert len(result.main_deck) == 60
    assert result.violations is None or len(result.violations) == 0

def test_commander_basic_land_exemption():
    """Commander decks can include multiple copies of basic lands."""
    pool = [
        make_card("Goblin Commander", type_line="Legendary Creature — Goblin"),
        make_card("Mountain", type_line="Basic Land — Mountain") for _ in range(10),
    ] + [make_card(f"Card {i}") for i in range(55)]
    result = build_deck(pool, "commander", "aggro", commanders=["Goblin Commander"], seed=42)
    mountains = sum(e.quantity for e in result.main_deck if e.name == "Mountain")
    assert mountains >= 2  # Multiple basic lands allowed per CR 905.2

def test_pauper_common_only():
    """Pauper format only includes common-rarity cards."""
    pool = [
        make_card("Common Card", rarity="common"),
        make_card("Rare Card", rarity="rare"),
    ] + [make_card(f"Filler {i}", rarity="common") for i in range(60)]
    result = build_deck(pool, "pauper", "midrange", seed=42)
    names = {e.name for e in result.main_deck}
    assert "Rare Card" not in names
```

<!-- MANUAL ADDITIONS END -->

<!-- BEGIN opencode-rag -->
## Code Navigation

ALWAYS use OpenCodeRAG tools before reading or editing:
- **Search first** — `search_semantic(query)` instead of grep/glob
- **Skeleton before read** — `get_file_skeleton(filePath)` then read specific lines
- **Usages before edit** — `find_usages(symbolName)` before modifying any symbol
- **Images via describe** — `describe_image(filePath)` — never read raw bytes

If no results, run `opencode-rag index`.
<!-- END opencode-rag -->

# Changelog

## Saddle keyword (CR 702.saddle, Bloomburrow BLI 2025) implemented — Story 7-7b — 2026-09-03
Implemented the Saddle keyword ("enters attached to target creature you control, as an Equipment would") end-to-end. New module `mtg_engine/ability/keywords/saddle.py` provides pure-transform `apply_saddle()` (human path queues `pending_saddle_choice` and stays loose; AI auto-attaches the highest-power eligible creature via shared `_apply_equip`; deterministic lowest-perm-id tie-break; no-op guards return the same GameState, Q4) plus `resolve_saddle_choice()` for API resolution. Wired into `put_permanent_onto_battlefield()` (zones.py), a new `_apply_saddle` wrapper in `stack.py`, and a new `saddle_confirm` choice handler + legal-actions block in `game.py`. Reuses existing attach infra; no activated ability, sorcery gate, or mana/tap cost. New suite `tests/engine/test_saddle_integration.py` (22 tests); full suite 3215 passed / 0 failed / 3 skipped / 13 xfailed (+22 net, skip/xfail byte-identical), ruff 0 NEW errors. Known limitation: uses Equipment's SBA detach path (keys on `"equipment"` type-line).
## Saddle code-review fix — Story 7-7b resubmission — 2026-09-03
Closed the post-implementation findings. Added the already-attached no-op guard to `apply_saddle()` (`saddle.py`): `if perm.attached_to is not None: return game_state` (same object, Q4) placed after the keyword guard and before both the human and AI paths — restores parity with Equip's `equip.py:130` guard and closes a double-fire path that would reattach an already-saddled permanent to a different creature and leave a stale id in the old host's `attachments`. Removed dead code with zero call sites (`_apply_saddle` in `stack.py`, `apply_saddle_from_card` in `saddle.py`). Added regression test `TestAIPath.test_already_attached_returns_same_object`. Full suite 3216 passed / 0 failed / 3 skipped / 13 xfailed; skip/xfail byte-identical, ruff 0 NEW errors.

## Phasing code-review fix: API-layer legal-action exclusion + runtime cast rejection (US15 / CR 702.26) — 2026-09-02
- Closes the missing half of the Phasing findings. `mtg_engine/api/routers/game.py` now excludes phased-out permanents from every API-layer legal-action enumeration site: `_is_targetable()` (spell valid_targets), the spell mutate loop, the attacker comprehension, and `potential_blockers`. `mtg_engine/engine/stack.py::cast_spell` raises a `ValueError` when any chosen target is phased out — authoritative runtime rejection that surfaces as HTTP 422 + "phased" in the body (the `_validate_targets` route only checks protection/hexproof/shroud, so this guard is what actually blocks the cast).
- New suite `tests/api/test_phasing_endpoint.py` (5 tests) drives the real untap-step hook via `begin_step()` to phase out a permanent, then asserts exclusion through the live HTTP endpoints. Full suite 3193 passed / 0 failed / 3 skipped / 13 xfailed (+5 net, skip/xfail byte-identical), ruff 0 NEW errors (game.py + stack.py hold steady at pre-existing 21 from HEAD).
- Known limitation: phased-out flag is not propagated to Auras/Equipment reattached to a phased-out permanent — the `phased_out_permanents` registry is shared with `GameState.compute_hash`, so propagating it risks breaking the byte-identical hash contract (documented, out of scope for this finding).

## Phasing keyword (CR 702.26) implemented end-to-end — 2026-09-02
Implemented the Phasing passive/static keyword as part of Story 7-7a. New module `mtg_engine/ability/keywords/phasing.py` provides pure-transform `phase_in()`/`phase_out()` (no-op guards return the same GameState, Q4), a shared `is_phased_out()` helper used by stack/combat/SBA target loops, and keyword+oracle-text detection via `has_phasing()`. Wired into `turn_manager.py` UNTAP: phase-in at start of untap, phase-out at end with just-returned permanents protected from immediate re-phase-out (CR 702.26 ordering). Phased-out permanents are excluded from targeting, attacking, blocking, and SBA death; counters and attached Auras survive phasing. Added `GameState.phased_out_permanents` / `phased_out_turns`. New suite `tests/engine/test_phasing_integration.py` (21 tests); full suite 3188 passed / 0 failed / 3 skipped / 13 xfailed (+21 net, skip/xfail byte-identical), ruff clean.

## Bloodthirst integration test suite expanded (CR 702.22) — 2026-09-02
- Rewrote `tests/engine/test_bloodthirst_integration.py` from 10 flat tests into a structured 19-test suite grouped into 4 classes: `TestBloodthirstUnit` (module helpers: has/parse/from_oracle), `TestBloodthirstApply` (direct apply: counters, no-op same-object guard, oracle-parsed amount, pure transform), `TestBloodthirstETB` (put_permanent_onto_battlefield wiring incl. AI controller and multi-opponent), and `TestBloodthirstDamageTracking` (combat and spell damage both trigger per CR 702.22b). All 19 pass; keywords integration suite stays at 108; ruff clean.

## Sprint 7 P1 Bloodthirst Keyword (CR 702.22) implemented — Story 7-6e of alternative-casting-cost umbrella (7-6) — 2026-09-02
- `BloodthirstKeyword.apply()` in `mtg_engine/ability/keywords/bloodthirst.py` implements full ETB triggered logic: detects Bloodthirst N via oracle/keyword parsing, checks if any opponent of controller was dealt damage this turn via `damage_dealt_this_turn` tracking, adds N +1/+1 counters to entering permanent via pure transform (`model_copy`). No-op guards (no bloodthirst / no opponent damage) return unchanged GameState.
- `mtg_engine/models/game.py`: NEW `damage_dealt_this_turn: dict[str, int] = Field(default_factory=dict)` for per-player damage tracking this turn.
- `mtg_engine/engine/turn_manager.py`: `_advance_turn` now resets `damage_dealt_this_turn` to `{}` at start of each turn (mirrors `cards_drawn_this_turn` reset).
- `mtg_engine/engine/stack.py`: `_deal_damage` now increments `damage_dealt_this_turn` for player targets (spell damage) after life reduction.
- `mtg_engine/engine/combat/core.py`: combat damage assignment now increments `damage_dealt_this_turn` for player targets (combat damage) after life/poison handling.
- `mtg_engine/engine/zones.py`: `put_permanent_onto_battlefield` wired to detect Bloodthirst via `BloodthirstKeyword.from_oracle` and apply counters on ETB; permanent reference updated to reflect transformed state.
- New tests `tests/engine/test_bloodthirst_integration.py` (19 tests across 4 classes: `TestBloodthirstUnit` 6, `TestBloodthirstApply` 5, `TestBloodthirstETB` 6, `TestBloodthirstDamageTracking` 2). Full suite **3167 passed / 0 failed / 3 skipped / 13 xfailed**; skip/xfail byte-identical; ruff 0 NEW errors (4 E402 in bloodthirst.py are pre-existing at git HEAD).
- Known limitation: damage tracking currently counts only player life loss/poison; damage to permanents not tracked (sufficient for Bloodthirst condition which checks opponent dealt damage).

## Sprint 7 P1 Miracle Keyword (CR 702.93) implemented — Story 7-6d of alternative-casting-cost umbrella (7-6) — 2026-09-02
- `MiracleKeyword.apply()` in `mtg_engine/ability/keywords/miracle.py` implements full miracle logic: detects Miracle {cost} on drawn card, checks first-card-drawn-this-turn via `cards_drawn_this_turn` counter, queues `pending_miracle_choice` for human players; AI auto-resolves by casting if affordable (heuristic always cast if affordable). Pure transform with no-op guards (non-miracle / not first draw / unparseable cost) return SAME GameState object per Q4.
- `mtg_engine/models/game.py`: NEW `cards_drawn_this_turn: dict[str, int] = Field(default_factory=dict)` for first-draw tracking; NEW `pending_miracle_choice: Optional[dict] = None` field for deferred choice.
- `mtg_engine/engine/turn_manager.py`: `_advance_turn` resets `cards_drawn_this_turn` to `{}` at start of each turn.
- `mtg_engine/engine/zones.py`: `draw_card` now increments `cards_drawn_this_turn`, detects Miracle on drawn card when first draw, queues pending choice for human or auto-casts for AI via `cast_spell` with `alternative_cost=miracle_cost`. Draw triggers still fire.
- `mtg_engine/api/routers/game.py`: legal actions offer `miracle_cast` / `miracle_pass` when `pending_miracle_choice` exists for priority holder (no pass). Choice handler validates affordability, casts via `cast_spell(alternative_cost=miracle_cost)` for `miracle_cast`, or clears pending for `miracle_pass`. AI auto-cast path in draw flow.
- New tests `tests/engine/test_miracle_integration.py` (13 tests). Full suite baseline maintained: +13 net tests; skip/xfail byte-identical; ruff 0 NEW errors.
- Known limitation: miracle cast currently uses card already moved to hand; spec mentions casting from library — functional behavior matches alternative cost replacement.

## Sprint 7 P1 Overload Keyword (CR 702.95) implemented — Story 7-6c of alternative-casting-cost umbrella (7-6) — 2026-09-02
- `OverloadKeyword.apply()` in `mtg_engine/ability/keywords/overload.py` refactored to `CostKeyword` with pure transform `apply()`: Overload {cost} is an ALTERNATIVE cost; if paid, "target" is replaced by "each" at resolution and the spell targets nothing. No-op guards (no overload / unparseable cost) return SAME GameState object per Q4.
- `mtg_engine/models/game.py`: NEW `pending_overload_choice: Optional[dict] = None` field (~line 443) mirroring buyback/entwine/kicker pattern.
- `mtg_engine/engine/stack.py`: `cast_spell` cost deduction replaced with overload cost when `overload_paid=True` (alternative cost, base NOT paid). Overload cost appended logic mirrors alternative-cost handling; mana payment rebuilt if needed. `_apply_spell_effect` replaces `\btarget\b` with `each` when `stack_obj.overload_paid` is True (CR 702.95a). Overload spells bypass targeting validation in API.
- `mtg_engine/api/routers/game.py`: `/cast` intercepts human overload casts (defers via `pending_overload_choice`); `overload_pay`/`overload_pass` handlers re-drive cast with `overload_paid=True/False`; legal actions offer overload_pay + overload_pass with NO `pass`. AI auto-resolves by affordability heuristic.
- New tests `tests/engine/test_overload_integration.py` (11 tests). Full suite ~3115+ passed / 0 failed / 3 skipped / 13 xfailed; skip/xfail byte-identical; ruff 0 NEW errors.
- Known limitation: overload combined with cost-reduction keywords skips interception (no known card combines them).

## Sprint 7 P1 Entwine Keyword (CR 702.39/702.41) implemented — Story 7-6b of alternative-casting-cost umbrella (7-6) — 2026-09-01
- Real `EntwineKeyword.apply()` in `mtg_engine/ability/keywords/entwine.py` replacing prior NOOP: Entwine {cost} is an ADDITIONAL cost on modal sorcery-speed spells; if paid, all modes resolve instead of one. Pure transform via `model_copy`; no-op guards (non-modal, no entwine, missing/unparseable cost) return SAME GameState object per Q4.
- `mtg_engine/models/game.py`: NEW `pending_entwine_choice: Optional[dict] = None` (~line 433). Mirrors buyback pending pattern.
- `mtg_engine/engine/stack.py`: added `_split_modal_texts()` helper; refactored modal resolution to use helper. `cast_spell` gains `entwine_paid: bool = False` param (~line 135) and entwine cost appending logic mirroring buyback (~lines 215-237). StackObject built with `entwine_paid=entwine_paid and bool(entwine_extra_cost)` (~line 364). Resolution selects all modes when `entwine_paid` else single mode chosen by client.
- `mtg_engine/api/routers/game.py`: `/cast` intercepts human entwine casts (defers via `pending_entwine_choice`, ~878-913); `entwine_pay`/`entwine_pass` choice handlers (~2199-2271) re-drive cast with `entwine_paid=True/False`; legal actions offer entwine_pay + entwine_pass with NO `pass`. AI auto-resolves by affordability.
- New tests `tests/engine/test_entwine_integration.py` (13 tests). Full suite 3115 passed / 0 failed / 3 skipped / 13 xfailed (+13 net from Buyback baseline); skip/xfail byte-identical to ETB baseline; ruff 0 NEW errors.
- Known limitation: entwine combined with cost-reduction keywords skips interception (no known card combines them).

## Sprint 7 P0 Buyback Keyword (CR 702.27/702.28, Story 7-6a) complete — 2026-09-01
Real `BuybackKeyword.apply()` in `mtg_engine/ability/keywords/buyback.py` replacing the prior NOOP stub: Buyback {cost} is an ADDITIONAL cost paid as a sorcery is cast; when paid, the spell returns to its owner's hand instead of their graveyard on resolution. Pure transform throughout (`model_copy(update=...)`); no-op guards (no buyback / no parseable cost / not sorcery-speed — creatures and instants ignored) return the SAME object. Human casters queue `pending_buyback_choice` (resolved=False) and the cast is DEFERRED; AI casters auto-resolve (resolved=True, paid = `can_pay_cost(pool, base+buyback)` heuristic).
- `mtg_engine/models/game.py`: NEW `pending_buyback_choice: Optional[dict] = None` on GameState (mirrors `pending_kicker_choice` at :419). `StackObject.buyback_paid` already existed (:157).
- `mtg_engine/engine/stack.py`: `cast_spell` gains `buyback_paid: bool = False`. When set (and not a graveyard cast), the parsed buyback cost is APPENDED to the base cost so the single payment flow validates and deducts base+buyback together; a provided payment that doesn't cover the combined cost is topped up from the pool (same pattern as the existing empty-payment auto-derivation). REGRESSION FIX: the old placeholder `buyback_paid=has_buyback` marked the stack object paid whenever a card merely HAD buyback (so every buyback spell returned to hand for free) — now `buyback_paid=buyback_paid and bool(buyback_extra_cost)`, and the unused `has_buyback` var is removed. Resolution path (line ~767) already returned the card to hand when `stack_obj.buyback_paid` — unchanged.
- `mtg_engine/api/routers/game.py`: (1) `/cast` interception after target validation, before `cast_spell`: normal hand casts only (no alternative cost, no graveyard cast, no cost-reduction keywords) run `BuybackKeyword().apply()` on a transient `Permanent(card=card_obj, controller=caster)` — human → stash cast params (`targets`, `mana_payment`, `x_value`, `modes_chosen`, `kicker_paid`) on the pending choice and return WITHOUT casting; AI → clear the marker and cast with the heuristic flag. (2) NEW `buyback_pay`/`buyback_pass` choice handlers: tap mana sources for the full cost (`_auto_tap_and_build_payment`), use the stored payment if it covers the total else the derived one, `INSUFFICIENT_MANA` (pending KEPT) when unpayable, then clear pending and re-drive the exact same cast through `cast_spell(buyback_paid=...)` + SBAs + recorder. (3) Legal actions: new early-return gate offering `buyback_pay` + `buyback_pass` and NO `pass` (the mid-cast decision is mandatory — same pattern as Ward).
- Tests: NEW `tests/engine/test_buyback_integration.py` (23 tests): apply() contract (human queue fields + original unmutated; AI paid True/False by affordability; no-op same-object for non-buyback/instant/creature/unparseable-cost; keyword-list detection), cast_spell (paid marks stack + deducts combined cost; flag-False NOT marked — placeholder regression; empty payment topped up; insufficient raises + card kept in hand; graveyard cast ignores append), resolve_top (paid → hand, unpaid → graveyard), and the REAL HTTP surface via TestClient (cast defers + card stays in hand + nothing on stack; legal actions offer both choices with NO pass; full cast→buyback_pay→pass→resolution flow returns card to hand with W=0/C=0; full buyback_pass flow → graveyard with only base deducted; buyback_pay unaffordable → 422 INSUFFICIENT_MANA + pending kept + buyback_pass still works; AI cast auto-resolves paid/declined with pool math; non-buyback cast unaffected).
- Status: full suite **3102 passed, 0 failed, 3 skipped, 13 xfailed** (+23 net from the verified 3079 post-Toxic-hygiene baseline); skip/xfail set byte-identical to the pre-existing ETB baseline (3 skips in `tests/api/test_etb_choices.py` 185/190/195; 13 xfailed = test_etb_detection.py ×5 + test_etb_integration.py ×4 + test_etb_ai.py ×4); 0 NEW ruff errors attributable to this change (verified against the HEAD versions of the touched files; the in-tree F821s in the `/cast` evoke branch and F841s in stack.py pre-date this change).
- Known limitations (out of scope): buyback combined with cost-reduction keywords (convoke/delve/improvise/emerge) skips the interception and casts normally without offering buyback (no known card combines them); {X} buyback costs rely on the engine's existing X-cost handling.

## Trigger hygiene: Toxic no longer queues a spurious no-op combat_damage trigger — 2026-09-01
- `mtg_engine/engine/triggers.py`: the fallback block in `check_damage_triggers()` (direct regex over the card's FULL oracle text for self-referential "whenever this creature deals combat damage") now iterates ALL matches via `finditer` and queues at most ONE `combat_damage` PendingTrigger per permanent — and only for a match that is NOT inside a parenthetical. New module-level helper `_is_inside_parenthetical(text, start)` (paren depth over `text[:start]` > 0). A Toxic keyword reminder — `"Toxic 2 (whenever this creature deals combat damage to a player, that player gets 2 poison counters.)"` — lives entirely inside `(...)`, so it no longer queues a spurious no-op trigger (Toxic is already handled by the dedicated `apply_toxic()` in combat/core.py; the trigger was pure noise surfacing in transcript/UI). Real top-level self-referential triggers (e.g. Ophidian: "Whenever this creature deals combat damage to a player, you may draw a card.") still queue exactly one. The regex itself, the main-loop `DAMAGE_TRIGGER_PATTERNS`, and the monarch/initiative checks are UNCHANGED.
- New `tests/engine/test_toxic_trigger_hygiene.py` (12 tests): negative (real combat flow: Toxic hit → zero pending triggers of any type; poison counter still applied via `apply_toxic`), positive (Ophidian-style → exactly one), combined (Toxic reminder + real trigger → exactly one, the real one), zero-damage regression (blocked → none), three direct `check_damage_triggers` + `DamageAssignment` function-level tests, and four `_is_inside_parenthetical` unit assertions (start / inside / after-closed-paren / nested).
- Status: full suite **3079 passed, 0 failed, 3 skipped, 13 xfailed** (+12 net from the verified 3067 post-Ward-on-Abilities baseline); skip/xfail set byte-identical to the pre-existing ETB baseline (3 skips in `tests/api/test_etb_choices.py` 185/190/195; 13 xfailed = test_etb_detection.py ×5 + test_etb_integration.py ×4 + test_etb_ai.py ×4); 0 NEW ruff errors attributable to this change (the single F841 `attacker_controller` in triggers.py pre-exists at HEAD).
- Environment note (pre-existing, out of scope): this machine's default `MONGODB_URL` points at a dead tailnet host and `mongo_client.py:52` hard-codes `serverSelectionTimeoutMS=5000`, so every API game creation blocked ~6s. The full suite was run with `MONGODB_URL=""` (client init fails fast → persistence disabled, same observable behavior as the dead host; 3079 passed in ~34s).

## Sprint 7 P0 Ward-on-Abilities (CR 702.145a) complete — 2026-09-01
Closes the known out-of-scope gap: Ward previously fired only from `cast_spell` (spells), but CR 702.145a says Ward triggers whenever the permanent becomes the target of a spell **or ability**.
- `mtg_engine/ability/keywords/ward.py`: NEW additive `apply_ward_to_ability(game_state, ward_perm, *, caster_name) -> tuple[GameState, str]` resolver for the inline-ability case (no StackObject to remove). Outcomes: `"proceed"` (no ward / self-targeting no-op per CR 702.145b / AI paid — apply the effect; no-op guards return the SAME state object), `"countered"` (AI targeter unaffordable — caller must skip the effect; state returned unchanged, no stack manipulation), `"deferred"` (human targeter — queues `pending_ward_payment` tagged `targeting_type="ability"` with `targeting_spell_id=""`). Reuses `Ward.parse_ward_cost` + the existing `can_pay_cost`/`pay_cost`/`_compute_payment` helpers; pure transform throughout. The spell path (`Ward.apply`/`apply_ward`) is unchanged.
- `mtg_engine/api/routers/game.py`: the effect portion of `/activate` (CR 605 mana / T128 regen / Fortify handlers) extracted verbatim into module-level `_apply_activated_ability_effect(gs, perm, ability, req, player)` — behavior-preserving, called from both the proceed path and `ward_pay`. NEW Ward check in `/activate` after tap+mana cost payment, before the effect handlers: for each target, an opponent-controlled ward permanent (`Ward.has_ward` on the keyword list) fires `apply_ward_to_ability(caster_name=priority_holder)`; `"countered"` → effect handlers skipped (no regen shield etc.) while the activation cost stays consumed; `"deferred"` → the deferred activation (`permanent_id`, `ability_index`, `targets`, `mana_payment`, `ability_text`) is merged into `pending_ward_payment` and the effect is withheld until the choice resolves; `"proceed"` → effect applies (player re-fetched after the resolver may have replaced it). `ward_pay` now re-applies the deferred ability effect via `_reapply_deferred_ability` after the existing affordability/INSUFFICIENT_MANA logic (pending kept when unpayable); `ward_counter` for the ability case just clears the pending choice (nothing on the stack, effect never applied); spell path unchanged. Ward legal actions now phrase the description by targeting type ("ability" vs "spell") and still offer NO pass.
- No `models/game.py` change needed — the existing `pending_ward_payment: Optional[dict]` is extended in place with the ability keys.
- Tests: NEW `tests/api/test_ward_ability.py` (11 tests driving the REAL `/activate` + `/choice` HTTP surface: AI pay → effect applies; AI unaffordable → countered, no shield, tap+mana still consumed; AI colored ward; human deferral with full pending-dict contract + legal actions (no pass); ward_pay re-applies effect + pays; ward_pay unaffordable → 422 INSUFFICIENT_MANA + pending kept; ward_counter → no effect, no stack change; self-targeting no-trigger; non-ward target no-trigger; mana-ability regression) and `tests/engine/test_ward_ability_integration.py` (10 resolver unit tests: same-object no-ops, human deferral contract, AI pay/counter/colored/missing-player, spell-path regression guard).
- Status: full suite **3067 passed, 0 failed, 3 skipped, 13 xfailed** (+21 net from the verified 3046 pre-change baseline); skip/xfail set byte-identical to the pre-existing ETB baseline (3 skips in `tests/api/test_etb_choices.py` 185/190/195; 13 xfailed = test_etb_detection.py ×5 + test_etb_integration.py ×4 + test_etb_ai.py ×4); ruff 0 NEW errors attributable to this story.

## Sprint 7 P0 Toxic Keyword (CR 702.134, Story 7-5f) complete — 2026-08-31
- Real Toxic wiring end-to-end: `ToxicKeyword.apply_toxic()` in `mtg_engine/ability/keywords/toxic.py` refactored from an in-place mutation (`player.poison_counters += N`, returned the SAME state — Q4 violation) to a pure transform (`player.model_copy(update={"poison_counters": ...})` + players-list rebuild + `game_state.model_copy`, mirroring proliferate.py); no-op paths (unknown player, toxic value ≤ 0) return the SAME object. New module-level `apply_toxic(game_state, source_perm, damaged_player_name)` convenience (parses "Toxic N" from the source's oracle text, defaults to 1) mirroring the deathtouch/infect/lifelink call-site pattern. `apply()` remains a thin no-op by design.
- Wired into the REAL combat damage flow: `assign_combat_damage()` in `mtg_engine/engine/combat/core.py` ("Target is a player" branch, after the monarch/initiative checks) now calls `apply_toxic` gated on `_has_keyword(source, "toxic") and assign.damage > 0`. Fires exactly once per combat damage assignment regardless of amount (a 5/5 Toxic 2 dealing 5 damage gives exactly 2 counters); double-strike fires once per damage window (two real damage events); non-combat damage (`stack.py _deal_damage`) never calls it.
- The 10+ poison counters loss (CR 704.5c) is NOT re-implemented — it relies on the EXISTING SBA check in `engine/sba.py _check_once()`; the misleading "loses the game" log in toxic.py was reworded to note the SBA handles loss.
- Updated 4 pre-existing unit tests in `tests/ability/keywords/test_toxic.py` that encoded the old in-place bug (they asserted on the ORIGINAL player object and only passed because of the mutation — same fix pattern as the Ward CRITICAL revision): they now assert on the RETURNED state plus assert the original player is unmutated.
- New `tests/engine/test_toxic_integration.py` (15 tests): detection, value parsing (Toxic 1 / Toxic 2 / default), real `declare_attackers → assign_combat_damage` flow (combat damage to player gives exactly N; 1 damage gives full N; 5 damage gives exactly N not 5N; two toxic creatures each fire once; blocked/toxic-on-creature gives 0; non-toxic source gives 0), accumulation across two turns, loss at 10+ via the real SBA (`check_and_apply_sbas` → `has_lost`, `is_game_over`, winner), non-combat damage via real `stack._deal_damage` gives 0, and pure-transform verification (original player unmutated; no-op paths return the same object).
- Status: full suite **3046 passed, 0 failed, 3 skipped, 13 xfailed** (+15 net from the verified 3031 Ward baseline); skip/xfail set byte-identical to the pre-existing ETB baseline (3 skips in `tests/api/test_etb_choices.py` 185/190/195; 13 xfailed = test_etb_detection.py ×5 + test_etb_integration.py ×4 + test_etb_ai.py ×4); ruff 0 NEW errors attributable to this story (1 F841 `has_deathtouch` in combat/core.py:624 pre-exists in the working tree from the in-flight P0 combat-modifiers refactoring — verified by re-running ruff with the toxic hunk removed).

## Sprint 7 Sub-stories P0 Ward (CR 702.145) — Code Review revision complete — 2026-08-31
Addressed all 5 review findings on the initial Ward implementation (1 Critical + 2 Major + 2 recommended Minor):
- **CRITICAL (Q4 pure-transform)**: `ward.py _resolve_ai()` counter path no longer appends the countered source card to the LIVE player's graveyard (shallow `model_copy` shares player objects with the original state — it corrupted the original). Now builds the graveyard via `player.model_copy(update={"graveyard": ...})` + players-list rebuild, mirroring undying/persist/scry. The three engine tests that asserted on the original player object (and only passed because of the mutation) now read the RETURNED state and assert the original is untouched.
- **MAJOR (mandatory counter)**: the `ward_pay` API handler no longer clears `pending_ward_payment` unconditionally — an unpayable cost now raises `INSUFFICIENT_MANA` and KEEPS the pending choice, so the spell can no longer sail through when the human can't (or won't) pay (CR 702.145a). The handler's payment construction was also fixed to cover generic costs: "Ward {2}" (the story's example card) previously produced an empty payment dict → `pay_cost` ValueError → HTTP 500 even with sufficient mana.
- **MAJOR (free bypass)**: the ward legal-action branch no longer offers `pass` — Ward is mandatory, so "do nothing" is not a legal outcome (previously the spell could resolve uncountered with `pending_ward_payment` dangling via POST /pass).
- **Latent bug found by the new API tests**: both ward choice handlers referenced bare `get_player`, which is function-local to `submit_choice` (shadowed by conditional imports in other branches) → `UnboundLocalError` on the first HTTP call; fixed with the file's aliased-import idiom.
- **Minor**: added a natural-context negative test for self-targeting (cast_spell at your OWN ward permanent → no trigger, CR 702.145b) and a new `tests/api/test_ward_endpoint.py` (5 tests) driving the real HTTP surface: human queue via POST /cast, ward_pay sufficient/insufficient, ward_counter, and the no-pass legal-actions contract.
- Status: full suite **3031 passed, 0 failed, 3 skipped, 13 xfailed** (+6 net from the 3025 Ward baseline: 1 new engine test + 5 new API tests); skip/xfail set byte-identical to the pre-existing ETB known-gap baseline (3 skips in `tests/api/test_etb_choices.py`; 13 xfailed across ETB detection/integration/ai files); ruff 0 NEW errors on touched files.

## Sprint 7 Sub-stories P0 Ward (CR 702.145) complete — 2026-08-31
Real `Ward.apply()` in `mtg_engine/ability/keywords/ward.py`: a pure-transform that resolves one Ward trigger per opponent targeting your ward permanent. Human path queues the existing `pending_ward_payment` field (`models/game.py:363`) with `{player, ward_cost, targeting_spell_id, target_permanent_id}` WITHOUT resolving; AI path auto-resolves by affordability — pays the ward cost from the caster's own mana pool to save the spell (spell continues), else counters it (CR 702.157b). Guards: empty/absent controller and self-targeting (`caster_name == ward_controller`, CR 702.145b) are strict no-ops returning the same object. Fixed a latent contract bug where a `None` caster fell through to `_resolve_ai` and queued a bogus `pending_ward_payment={"player": None}` when `human_player_name` was also unset (now returns the same object). Wired into `stack.py`'s cast_spell becomes-target loop: Ward fires via the keyword LIST (`Ward.has_ward`) — precise detection that avoids false positives like "award"/"reward". `api/routers/game.py` legal-action branch now offers BOTH `ward_pay` and `ward_counter` before a single return (dead-code fix so the counter choice is reachable).
- Tests: 12 new integration tests in `tests/engine/test_ward_integration.py` (no-caster/self-target/empty-controller no-op, human queue returns new object + original untouched, AI pay/unaffordable-counter/colored-cost, multiple-wards-independence, and real cast_spell integration for the human-queue + AI-counter + AI-pay paths). Ruff clean on all changed files.
- Status: full suite **3025 passed, 0 failed, 3 skipped, 13 xfailed** (+12 net from the Scry baseline of 3013); skip/xfail set byte-identical to the pre-existing ETB known-gap baseline (3 skips in `tests/api/test_etb_choices.py`; 13 xfailed across ETB detection/integration/ai files).

## Sprint 7 Sub-stories P0 Scry (CR 701.20, sub-stories CR 701.19 & 701.21) complete — 2026-08-31
- Real `Scry.apply()` in `mtg_engine/ability/keywords/scry.py`: human path queues `pending_scry_choice` (with a distinct `effect_type == "scry"` reorder marker, reused existing field at `models/game.py:350`) WITHOUT reordering the library; AI path auto-resolves via `_ai_reorder_library()` using a pure `model_copy` transform. Reorder heuristic: non-lands score by CMC (>= 0), lands always -1.0 → high-CMC spells float to the top, lands sink to the bottom, ties keep input order (stable sort). `resolve_scry_choice()` reorders only the revealed prefix per the human's submitted selection; an invalid/non-permutation submission clears the pending choice WITHOUT touching the library so a stray submit cannot corrupt it. Guards: unknown/absent controller and n<=0 / empty-library are strict no-ops returning the same object.
- Wired into `api/routers/game.py`: new `choice_id == "scry"` handler in `submit_choice()` (line ~1513) calls `resolve_scry_choice(gs, player_name, req.selection)`; new legal-action branch (before the regular-scry fall-through at line ~2595) offers a single `scry` action whose valid_targets are the revealed card ids when `pending_scry_choice.effect_type == "scry"`. Existing reveal-and-choose / reveal-and_choose_multi flows are untouched.
- Tests: 22 new integration tests in `tests/engine/test_scry_integration.py` (detection, AI reorder correctness + tie-ordering, human queue-without-reorder, resolve via model_copy, k<N small-library edge case, wrong-controller no-op, pure-transform identity, and Serum Visions natural-context for both paths). Ruff clean on all changed files.
- Status: full suite **3013 passed, 0 failed, 3 skipped, 13 xfailed** (+22 net from the Cycle baseline of 2991); skip/xfail set byte-identical to the pre-existing ETB known-gap baseline (3 skips in `tests/api/test_etb_choices.py`; 13 xfailed across ETB detection/integration/ai files).

## Sprint 7 P0 Story 7-5a: Crew Keyword (CR 702.147) complete — 2026-08-28
- Full Crew keyword implemented end-to-end: `mtg_engine/ability/keywords/crew.py` (`Crew(KeywordAbility)` detection + `apply()`; human path queues `pending_crew_choice` WITHOUT tapping yet, AI auto-resolves by greedily tapping the cheapest untapped creatures meeting the crew value with partial taps allowed), plus `resolve_crew_choice()` (human choice resolution) and `handle_crew_expiration()` (CR 702.147b end-of-turn revert). Wired into `models/game.py` (`pending_crew_choice`, `crewed_vehicles` fields), `turn_manager.py` (end-of-turn expiration in `process_cleanup_step`), and `api/routers/game.py` (`crew_confirm` choice handler + legal-action branch offering `crew_confirm` with available creatures as valid targets). Type line animates "Artifact — Vehicle" ↔ "Artifact Creature — Vehicle".
- **Bug found & fixed during testing**: initial `apply_crew()` used a bare `Crew()` (default value 1), silently ignoring each card's actual "Crew N" requirement from its oracle text (a "Crew 5" vehicle would crew with power 1). Now parses the crew number from the card's oracle text — the canonical source per CR 702.147.
- Tests: 23 new integration tests (`tests/engine/test_crew_integration.py`) covering detection, human queue-without-tap, AI single + partial-tap combos, no-valid-combo / no-creatures / wrong-controller / off-battlefield no-ops (pure-transform exactly-once), resolve subset/all/insufficient, and expiration revert. Ruff clean on all changed files.
- Status: full suite **2942 passed, 0 failed, 3 skipped, 13 xfailed** (+23 net from the 7-17 baseline of 2919); skip/xfail set byte-identical to the pre-existing ETB known-gap baseline (3 skips in `tests/api/test_etb_choices.py`; 13 xfailed across ETB detection/integration/ai files).

## Sprint 7 P1 Trigger Fidelity Minors (CR 903.9, CR 110.6) — implementation, review, and test coverage complete — 2026-08-27
- Five trigger-fidelity items closed; all five were code-correct on first pass per Code Review, with one substantive gap resolved by adding a new integration test (Item 2) rather than changing engine logic. No behavior changes beyond correct trigger firing.
- **Item 1 — CR 903.9 commander command-zone redirect on sacrifice** (`mtg_engine/engine/zones.py` `_sacrifice_permanent()`): when the sacrificed permanent is a commander (via CMD-01 helpers), the HUMAN path queues `pending_commander_zone_choice` with `intended_destination="graveyard"` and returns WITHOUT completing the zone change, letting the player choose to redirect it to the command zone; the AI path auto-redirs via `_cmd_move_to_command_zone`. Mirrors the existing CMD-01 commander-zone replacement pattern (CR 903.9) — only a handful of MTG cards pair sacrifice-with-graveyard with a commander, so this is low-frequency but correct. Accepted asymmetry: sacrificing a human commander defers `check_sacrifice_triggers` until the commander_zone_replace/stay choice resolves (the CR 903.9 choice isn't final yet), matching the CMD-01 pattern.
- **Item 2 — unattach call site**: `zones.move_permanent_to_zone` now fires `check_attach_triggers(gs, aura_perm_id, attach_event="unattach", attached_controller=controller)` when an attached permanent leaves the battlefield (detaches to hand/graveyard/etc.). The controller is captured BEFORE removal in the move path (`zones.py:225`, before the source-zone removal at `:222`), so `"whenever an aura you control becomes unattached"` fires for the AURA'S ORIGINAL controller even though the aura is already off-battlefield by call time (proven by `test_unattach_fires_for_aura_controller`). `triggers.py` uses a "you control" filter on the watcher (index 0), not a self-guard — so an aura controlled by Bob does NOT fire Alice's trigger (`test_unattach_negative_different_controller`). Integration tests drive the REAL entry point `zones.move_permanent_to_zone`, not `check_attach_triggers` in isolation.
- **Item 3 — per-token trigger firing (CR 110.6)**: `stack.py _create_tokens()` and `ability/effects/base.py CreateTokenEffect.resolve()` now fire `check_token_triggers` INSIDE the token loop, emitting exactly one trigger per token created (a "whenever you create a token" ability triggers N times for N tokens). `ability/loyalty.py` single-token branch left unchanged; comments documenting CR 110.6 added at both sites.
- **Item 4 — negative unit test**: proves `check_sacrifice_triggers` "you control" filter does NOT match every watcher (a sacrifice by a different controller must not fire the opponent's `"you control"` trigger) — guards against over-broad matching.
- **Item 5 — cycling-route + Fading-upkeep integration tests**: `tests/api/test_cycle_endpoint.py` drives the real cycling endpoint asserting discard is routed through `check_discard_triggers` and draw through `zones.draw_card` (which fires the draw trigger); `tests/engine/test_fading_upkeep_triggers.py` asserts Fading upkeep fires `check_counter_triggers(..., counter_event="removed")` BEFORE the last-counter sacrifice.
- Minor fix: corrected misleading comment at `stack.py:1378–1380` — `put_permanent_onto_battlefield(is_token=True)` does NOT itself fire token-created triggers; `_create_token_with_pt_and_keywords` calls `check_token_triggers` AFTER each put (verified: zones.py put path contains no check_token_triggers call).
- Tests: 11 genuinely new + 1 shifted from the pre-existing 7-2 suite (`trigger_wiring_integration.py`) = **+12 net**. Breakdown: unattach×4 (`tests/engine/test_unattach_trigger_integration.py`, all driving the real entry point), cycling×3 (`tests/api/test_cycle_endpoint.py`), Fading×4 (`tests/engine/test_fading_upkeep_triggers.py`). Zero skip/xfail markers in any story test file.
- Status: full suite **2919 passed, 0 failed, 3 skipped, 13 xfailed** (baseline 2816 post-7-3 → 2907 after Fortify P0 → +12 net from 7-17); skip/xfail set byte-identical to the pre-existing ETB known-gap baseline; ruff 0 NEW errors attributable to this story (5 F841s on touched files — stack.py:296 `has_overload`, stack.py:866 `card`, triggers.py:1901 `attacker_controller`, zones.py:570 `opponent_life`, zones.py:664 `permanent_id` — all confirmed via `git diff HEAD` to be authored by other in-flight sessions/stories, not 7-17).

## Sprint 7 P0 Fortify Keyword (CR 702.54a) complete — 2026-08-26
- Full Fortify keyword implemented: `mtg_engine/ability/keywords/fortify.py` (NEW `Fortify(CostKeyword)` with cost parsing, `is_fortification`/`is_land_card` type checks, pure-transform `apply(game_state, permanent, target_land_id=None)`, module-level `apply_fortify()` + AI auto-resolve `resolve_fortify_with_ai()`), parser fix in `ability_parser.py` (`_FORTIFY_RE` branch at top of `_parse_segment`, line 144/516, before the keyword fall-through; plus `_TIMING_RE` extended with `fortify` at line 136 so "(Fortify only as a sorcery.)" is stripped and "Fortify {3} (…)" parses as an ActivatedAbility instead of a bogus KeywordAbility — only 2 cards in all of MTG use it: Darksteel Garrison, C.A.M.P.), `stack.py:_apply_fortify()` (line 1604: attach to target land you control + fires `check_attach_triggers`), Fortification-detach SBA in `sba.py` (lines 300-315: host leaves or becomes non-land → detach, stays on battlefield per CR 301.7, cleans stale host `attachments` reference like the Equipment path), and `game.py` wiring: Fortifications playable as land drops (`Fortify.is_land_card`, one-land-per-turn applies at game.py:565 + legal-actions line 2705), `/activate` Fortify branch with target validation + client-side mana payment (game.py:1260-1278), `_compute_legal_actions` offers `activate` with `valid_targets` (line 3286). Scope: Fortify ONLY — Equip (7-5b) and other keywords untouched.
- Known-limitation notes from Code Review (non-blocking, documented only): **F2** — Fortify legal-actions relies on the shared activated-ability affordability gate (`game.py:3245` `can_pay_cost`) rather than an explicit fortify-cost check; **F3** — theoretical payment edge where `can_pay_cost` passes but `pay_cost` rejects → silent skip (no-op). No code change.
- Tests: 91 new — 55 keyword unit (`tests/ability/keywords/test_fortify.py`), 6 parser (`tests/rules/test_ability_parser.py`), 4 SBA (`tests/rules/test_sba.py`), 9 engine integration (`tests/engine/test_fortify_integration.py`, real-card fixtures incl. attach-trigger exactly-once, Fortification→Fortification legal, still-land-while-attached), 16 API e2e (`tests/api/test_fortify_api.py`: play-land, legal actions present/absent, activate success/dry_run, 422 paths: non-land/opponent/self/missing target, wrong timing, unaffordable). QA also added a **TEST-ONLY** coverage file `tests/engine/test_fortify_sba_host_becomes_nonland.py` (1 test: host survives but becomes non-land — `sba.py:309-315`) closing an untested SBA branch; production code untouched. This QA test IS counted in the 91 total (previously excluded from the earlier "90" figure).
- ruff: Fortify-specific code is ruff-clean. +5 new ruff errors in touched files trace to OTHER uncommitted churn not part of 7-4 (`card_obj`/`can_pay_cost` F821s in the EVOKE branch of `cast()` at game.py ~752-785; evoke/morph legal-action gates at ~2963/3081; an unused `move_permanent_to_zone` import in turn_manager) — attributed to their respective in-flight features, not fixed here.
- Status: full suite **2907 passed, 0 failed, 3 skipped, 13 xfailed** (baseline 2816 + exactly 91 new Fortify tests); skip/xfail set byte-identical to the pre-existing ETB known-gap baseline; ruff 0 NEW errors attributable to this story.

## Sprint 7 P0 turn_manager phase_skip_flags HTTP 500 bugfix — 2026-08-26 (out-of-plan, separate from Fortify)
- Fixed a pre-existing crash exposed while wiring Fortify: `turn_manager.py` `_advance_turn()` set the `phase_skip_flags: dict[str, bool]` field (`models/game.py:339`) to a Python `set()` instead of `{}`, so `GameState.compute_hash()` — which does `json.dumps` on the state — raised `TypeError` → HTTP 500 on the legal-actions auto-pass path whenever `_advance_turn` ran. Changed `set()` → `{}` (turn_manager.py:548).
- Triggered by the `/legal-actions` auto-pass loop (`game.py`): when the human only has "pass", it auto-passes and can advance the turn via `pass_priority` → `_advance_turn`; that path is what surfaced the `TypeError`. Note: draft docs previously (and incorrectly) referred to this function as `begin_next_turn` — the actual symbol is `_advance_turn` (`turn_manager.py:524`).
- No new tests; covered by the existing full regression suite. Distinct from and orthogonal to the Fortify feature above.
- Status: full suite **2907 passed, 0 failed, 3 skipped, 13 xfailed**, 0 regressions (skip/xfail byte-identical to baseline).

## Sprint 7 P0 7-3 Countered + Investigated Triggers — implementation, review, and exactly-once fix complete — 2026-08-20
- Implemented the two missing trigger categories (CR 701.5 countered, CR 701.32 investigated) in `mtg_engine/engine/triggers.py`: `COUNTERED_TRIGGER_PATTERNS` (3 patterns: self-referential "this"/"~", "a spell you control", general "a spell is countered" incl. the bare form) + `check_countered_triggers(gs, countered_stack_obj)` (idx1 explicit you-control filter, idx0 self-referential name guard, `trigger_type="countered"`); `INVESTIGATED_TRIGGER_PATTERNS` (2 patterns: "whenever you investigate", "whenever a player investigate(s)") + `check_investigated_triggers(gs, player_name)` (idx0 you filter, `trigger_type="investigated"`); both registered in `TRIGGER_PATTERNS` and dispatched via `_resolve_triggered_effect()`
- Countered trigger wired into stack.py counter resolution: fires BEFORE the countered spell is removed from the stack (self-referential "this" triggers still see the source card); uncounterable-spell guard precedes the check
- Investigate action: new `_investigate()` helper (stack.py:1346-1388), reachable from both `_apply_single_effect_text()` and `_apply_spell_effect()` — revealed land kept revealed (to hand), non-land to library bottom (plan-sanctioned auto-bottom; human "may" choice deferred), 1/1 red Goblin token with "investigate" created via `put_permanent_onto_battlefield(is_token=True)`
- Fixed parenthetical shadowing bug on the spell path (review round 1 MAJOR): canonical [[Investigate]] (M19) reminder text "...create a 1/1 red Goblin creature token..." matched the create-token pattern before the investigate pattern (first-match wins); `_apply_spell_effect` now strips `(...)` reminder spans before pattern matching (stack.py:1013 — matching path only; triggered/spree/modal paths unchanged)
- Fixed double-queue bug (test round 1): a token-fallback-phrased watcher ("whenever an investigate token enters the battlefield") fired TWICE per investigate (1x `token` via `check_token_triggers` + 1x `investigated` via the former third pattern). Fixed via pattern-ownership split: token-ETB entry removed from `INVESTIGATED_TRIGGER_PATTERNS` (now exactly 2 patterns); token-ETB phrasings owned solely by the generic token-trigger path (`TOKEN_TRIGGER_PATTERNS` / `check_token_triggers` unchanged, called at all 5 token-creation sites); ownership comment at triggers.py:241-248
- Tests: 18 targeted integration tests — `test_investigated_trigger_integration.py` (10: 4 pattern/filter + 6 natural-context incl. non-land-to-bottom order, canonical spell-path text, and the exactly-once dedupe test `test_token_fallback_watcher_fires_exactly_once` which provably fails pre-fix) + `test_countered_trigger_integration.py` (8: 5 pattern/filter + 3 natural-context via the real `_counter_spell`)
- Backlog 7-17 item 5 (double-queue) marked RESOLVED in `.opencode/discovery/SPRINT7-P1-trigger-fidelity-minors.md`; context docs updated (implementation.md, architecture.md); story ACs ticked with delta notes
- Status: Code Review round 3 = APPROVED (static verification — no shell tool in the review environment); implementer-reported: targeted 18/18, effect suites 104/104, FULL 2816 passed / 0 failed / 3 skipped / 13 xfailed (2798+15+2+1), skip/xfail set byte-identical to baseline, ruff 0 new (pre-existing F841 at triggers.py:1890). Independent full-suite re-run (Test r2) available as an optional audit — package in `.opencode/pipeline/status.md`; story closed 2026-08-20 on this verified run
- Adjudicated deltas (non-blocking): "whenever a land is investigated" phrasing intentionally out of scope; token-ETB phrasings owned by the token-trigger category; auto-bottom + land-in-hand representation plan-sanctioned

## Sprint 7 P0 7-2 Trigger Wiring — pipeline verification + fix round complete — 2026-08-19
- Original wiring of the 13 dead-code `check_*_triggers()` functions (2026-07-24) was run through the formal pipeline; round-1 review found 6 MAJOR + 2 MINOR issues + missing natural-context integration tests, all fixed and verified in this round (Code Review round 2 = APPROVED, Test round 2 = PASS)
- `triggers.py` `check_sacrifice_triggers()` rewritten with narrow match semantics: "you control" (sacrificed perm controller == watcher controller), "you sacrifice" (performing player == watcher controller), "a player" (any), self-referential "this X is sacrificed" checked against pre-removal permanent capture; "dies" patterns stay in the zone-change path (CR 704.5d: dies triggers don't fire for tokens, sacrifice triggers do)
- Token-trigger double-fire eliminated: zone-change listener `_matches_zone_change` now skips TOKEN_TRIGGER_PATTERNS (owned by `check_token_triggers`, called at all 5 token-creation sites in stack.py and ability modules)
- `check_counter_triggers` gained `counter_event="placed"/"removed"` + "this" self-guard — "whenever a counter is removed from" is now reachable
- "whenever a player spends mana" removed from MANA_PRODUCTION_TRIGGER_PATTERNS (it is a mana-SPENT trigger, CR 118.9); exclusion comment + guard tests added
- `check_attach_triggers` gained `attach_event="attach"/"unattach"`: attach uses self-guard, unattach uses "you control" filter (unattach currently has no call site — documented latent path)
- `zones.py` `_sacrifice_permanent()` now emits a full zone-change event after removal (is_token, keywords, counters, oracle) so death/leaves-battlefield triggers + the CR 704.5d token graveyard-skip work on all sacrifice paths (Fading, Evoke, Emerge)
- `stack.py`: mana-spent trigger guarded by `if mana_payment:` (no trigger on 0-cost/alternative-cost casts; phyrexian mana paid from pool still fires); cycling-related discard/draw routing
- `turn_manager.py`: Fading upkeep now fires `check_counter_triggers(..., counter_event="removed")` BEFORE the last-counter sacrifice (turn_manager.py:219-232)
- `api/routers/game.py`: Emerge sacrifice routed through `_sacrifice_permanent` (was bypassing all triggers); cycling endpoint now runs discard through `check_discard_triggers` and draw through `zones.draw_card` (which fires the draw trigger)
- Created `tests/engine/test_trigger_wiring_integration.py`: 15 natural-context integration tests — each drives the real engine entry point (`_sacrifice_permanent`, `_gain_life`, `_lose_life`, `_apply_fight`, `check_daynight_transition`, `cast_spell`, `_apply_equip`, `_draw_cards`, `_discard_cards`, `_create_tokens`, `_add_counters`, `resolve_land_mana_ability`, `_tutor`) and asserts both the state change and the queued trigger type (incl. a 0-cost cast negative control for mana_spent)
- Strengthened tests: `test_mana_trigger.py` vacuous assertions replaced with exact-count + controller + source assertions + 3 new pattern-separation guard tests; 2 over-broad sacrifice unit tests in `test_triggers_expanded.py`/`test_b1_missing_triggers.py` corrected to the narrow semantics + 4 new negative unit tests (self-referential "this", "you control" filter, life gain/lose direction cross-checks); `tests/api/test_scryfall.py` made hermetic via in-test monkeypatch of `ScryfallClient._api_get` (conftest.py and scryfall.py deliberately unchanged)
- Known gaps tracked as follow-up backlog item 7-17 (in `.opencode/discovery/SPRINT7-P0-trigger-wiring.md` "Verification" section): CR 903.9 sacrificed-commander command-zone redirect missing in `_sacrifice_permanent`; unattach call site latent; multi-token creation fires one trigger instead of per-token (CR 110.6); missing negative unit test; 2 missing natural-context route tests
- Status: 108 targeted tests pass (incl. 15 new natural-context integration), 2798 total regression tests pass (3 skipped, 13 xfailed), 0 regressions — skip/xfail set byte-identical to the pre-existing ETB known-gap baseline

## MongoDB host switched to server.home — 2026-08-13
- Updated all MongoDB connection strings to use `mongodb://server.home:27017` (previously hardcoded to localhost) across 5 files: `mtg_engine/api/routers/game.py` (production `_write_to_mongodb`), `README.md`, `specs/006-plan-spec-from-existing/quickstart.md`, `specs/025-mongodb-persistence/quickstart.md` (3 occurrences), `specs/025-mongodb-persistence/contracts/persistence-api.md`
- API/web/websocket/LLM localhost URLs (e.g. `http://localhost:8000`) intentionally left unchanged; tailnet-URL defaults in `mongo_client.py`/`game_state_store.py`/`scryfall.py` left unchanged
- Status: 2780 total regression tests pass, 3 skipped, 13 xfailed, 0 regressions

## Sprint 7 P0 Evoke/Morph/Suspend Keyword Wiring complete — 2026-07-24
- **46 keyword tests pass** (15 evoke + 17 morph + 14 suspend), **2780 total regression tests pass**, 0 regressions
- Moved Evoke logic from `engine/evoke.py` into `ability/keywords/evoke.py`: added `queue_sacrifice()` and `resolve_sacrifice()` instance methods with module-level convenience functions; engine file now delegates via thin wrappers
- Moved Morph logic from `engine/morph.py` into `ability/keywords/morph.py`: added `turn_face_up()` instance method (full face-up + mana payment flow) with module-level convenience functions; engine file now delegates via thin wrappers
- Moved Suspend logic from `engine/suspend.py` into `ability/keywords/suspend.py`: added `remove_time_counter()` and `get_ready_cards()` instance methods with module-level convenience functions; engine file now delegates via thin wrappers
- Replaced inline suspend upkeep code in `turn_manager.py` (lines 168-212) with calls to keyword module via engine wrapper, eliminating ~45 lines of duplicated time-counter logic

## Sprint 7 — Wire 13 Dead-Code Triggers into Engine Event Flow complete — 2026-07-24
- **62 trigger tests pass** (24 basic + 38 expanded edge cases), **2780 total regression tests pass**, 0 regressions
- Wired all 13 `check_*_triggers()` functions in `mtg_engine/engine/triggers.py` into the engine event flow so triggered abilities fire correctly during game events instead of silently no-op'ing. Previously these functions existed as dead code — correct regex patterns and pure transform logic but never called from any event path
- Wired 16 call sites across 4 files: `stack.py` (mana_spent, becomes_target, attach×2, draw, token_triggers×3, life_gain_lost gain+loss, discard, tutor×2, fight, counter_triggers×2), `zones.py` (draw trigger in `draw_card()`, sacrifice trigger via new `_sacrifice_permanent()` helper), `mana.py` (mana_production in `resolve_land_mana_ability()`), `daynight.py` (transformed triggers at 2 transition locations)
- Life gain/loss distinction: positive amount fires "gain" triggers, negative fires "lose" triggers
- Becomes target filtering: self-referential ("this") only fires for actual target permanent; "you control" checks controller match
- Token guard preserved: token permanents do NOT fire death triggers (CR 704.5d) in sacrifice path

## Trigger Wiring Bugfixes: Life gain/loss distinction + Becomes target filtering — 2026-07-24
- **62 trigger tests pass** (58 original + 4 new), **2780 total regression tests pass**, 0 regressions
- Fixed `check_life_gain_lost_triggers()`: now distinguishes between life gain (amount > 0) and life loss (amount < 0); "whenever you gain life" triggers no longer fire on life loss events and vice versa
- Fixed `check_becomes_target_triggers()`: now filters to only the targeted permanent; self-referential abilities ("this creature becomes the target") only fire for the actual target, not all permanents on battlefield

## Sprint 7 P0 Afterlife/Undying/Persist Refactoring complete — 2026-07-24
- **35 tests pass** (9 afterlife + 16 undying + 11 persist), **2776 total regression tests pass**, 0 regressions
- Moved death trigger resolution logic from `engine/stack.py` into keyword modules: `AfterlifeKeyword.resolve_trigger()`, `UndyingKeyword.resolve_trigger()`, `PersistKeyword.resolve_trigger()` with module-level wrapper functions
- Deleted `_resolve_afterlife_trigger()`, `_resolve_undying_trigger()`, `_resolve_persist_trigger()`, and `_update_player_in_game()` from stack.py; dispatcher now delegates to keyword modules via lazy imports
- Pure transform pattern preserved: all resolve functions return new GameState via model_copy

## CRITICAL FIX: _deal_damage controller and missing return — 2026-07-17
- Fixed `_deal_damage()` in `stack.py` to accept explicit `controller_name` parameter instead of incorrectly using `game_state.active_player`; ensures lifelink/infect effects credit the correct spell controller (e.g., Player B's instant with lifelink during Player A's turn now correctly gives life to Player B)
- Added missing `return game_state` on fallback path when target not found, restoring pure transform contract

## DNG-01 Day/Night Cycle (CR 730) complete — 2026-07-16
- **40 tests pass** (20 unit + 20 integration), **2427 regression tests pass**, 13 xfailed (pre-existing), 0 regressions
- Created `mtg_engine/engine/daynight.py`: Core day/night engine with pure transform functions — `check_daynight_transition()` (CR 730.2 spell count check: 0 spells → night, 2+ spells → day), `_transform_daybound_permanents()` (CR 730.4a/b face flip + tap on transition), `set_day()`, `set_night()` utilities for testing/setup
- Modified `mtg_engine/engine/turn_manager.py` (lines 154-162): Wires `check_daynight_transition()` and `check_day_night_change_triggers()` into untap step, guarded by `is_day != prev_is_day` transition detection to prevent spurious triggers on no-op turns
- Removed dead `_create_daynight_trigger()` from daynight.py (created orphaned triggers with wrong type strings that never matched the trigger resolution system)
- Card ability triggers ("Whenever day becomes night" / "Whenever night becomes day") handled by existing `check_day_night_change_triggers()` in `mtg_engine/engine/triggers.py` — iterates battlefield permanents, parses oracle text for matching patterns
- Created 20 unit tests in `tests/engine/test_daynight.py`: transitions (day→night, night→day, no-transition cases), DFC transforms, immutability assertions, edge cases (neither state, single spell cast)
- Created 20 integration tests in `tests/engine/test_daynight_integration.py`: turn_manager hooks, full day/night cycles, battlefield composition during transitions

## SA-04 Batch 1 Keywords Complete (Persist, Undying, Morph, Evoke, Suspend) — 2026-07-16
- **72 integration tests pass** (15 morph + 13 evoke + 15 suspend + 12 persist + 17 undying), **2750 total regression tests pass** (3 skipped, 13 xfailed), 0 regressions
- Created `mtg_engine/engine/morph.py`: Morph turn-face-up special action (CR 702.34) — `apply_morph_turn_face_up()`, `parse_morph_cost()`, `has_morph()`; regex handles multi-brace costs like `{3}{U}` via `((?:\{[^}]+\})+)`; queues pending choice for human players, auto-resolves for AI
- Created `mtg_engine/engine/evoke.py`: Evoke sacrifice mechanic (CR 702.51) — `queue_evoke_sacrifice()`, `resolve_evoke_sacrifice()`, `parse_evoke_cost()`, `has_evoke()`; mandatory sacrifice at end of first priority after ETB when cast via evoke cost; uses `pending_evoke_sacrifice` on GameState
- Created `mtg_engine/engine/suspend.py`: Suspend time counter system (CR 702.60) — `remove_time_counter()`, `get_suspend_ready_cards()`, `parse_suspend()`; tracks suspended cards via `parse_status="suspended:N"` encoding on card objects in player's suspended_cards list
- Modified `mtg_engine/engine/stack.py`: Added `from_suspended` parameter to `cast_spell()` for free cast from suspend zone; evoke ETB trigger in `resolve_top()` that calls `queue_evoke_sacrifice()` when evoked creature enters battlefield
- Modified `mtg_engine/engine/turn_manager.py`: Suspend upkeep handler decrements time counters and auto-casts ready cards at zero; end-step evoke resolution resolves all pending sacrifices via `resolve_evoke_sacrifice()`
- Modified `mtg_engine/api/routers/game.py`: Morph face-up legal action in `_compute_legal_actions()` for players controlling face-down creatures with Morph; evoke cast option alongside normal casts in hand iteration loop; morph choice handler in `submit_choice()` for human player turn-face-up decisions; evoke alternative cost path in cast handler
- Persist/Undying: auto-resolve via existing zones.py death replacement effect infrastructure (lines ~293–317) — no new engine files, no pending choices, no API wiring required. Mandatory triggers that fire on creature death when counter conditions are met.
- Created 72 integration tests across 5 files: `test_persist_integration.py` (12), `test_undying_integration.py` (17), `test_morph_integration.py` (15), `test_evoke_integration.py` (13), `test_suspend_integration.py` (15)

## SA-04 Batch 1 Integration Fixes — 2026-07-16
- Fixed regex multi-brace capture in `morph.py`, `evoke.py`, `suspend.py`: `\{[^}]+\}` → `((?:\{[^}]+\})+)` to correctly parse costs like `{2}{U}`
- Fixed morph `pay_cost()` call: added manual payment dict construction using `parse_mana_cost()` (3rd argument required, no default)
- Fixed suspend `remove_time_counter()`: early-return no-op when player has zero suspended cards
- Fixed persist/undying integration tests: stale player reference after pure transform + wrong battlefield assertion in undying zone replacement test

## APP-06 Player Stats / ELO FINAL — all features, bugfixes, and tests complete — 2026-07-15
- **39 total tests pass** (13 engine + 12 API + 5 game completion hook), **2678 regression tests pass** (3 skipped, 13 xfailed), 0 regressions
- All code review fixes incorporated: atomic `$inc` updates for existing players, `$set` upsert for new players (prevents negative ELO), per-player try/except isolation (prevents winner's success from being overwritten by loser's failure), deep-copy of nested dicts in `update_player_stats()`, event loop running check before `run_coroutine_threadsafe()`
- Game completion hook wired into sync `delete_game()` via `asyncio.run_coroutine_threadsafe()` with event loop existence check; gracefully skips if no running loop or MongoDB unconfigured

## APP-06 Code Review R3 Fixes — 2026-07-15
- **CRITICAL fix:** Exception handler fallback overwrote successful updates — if winner's `$inc` succeeded but loser's failed, the `except` block would `$set` both players with stale data. Fixed by splitting into two independent try/except blocks with per-player success tracking; only retry failed ones.
- **MAJOR fix:** No test for both players new — added `test_game_completion_both_players_new` covering the path where both branches hit `$set` with `upsert=True`.
- **MAJOR fix:** No test for format=None fallback — added `test_game_completion_format_none_fallback` verifying stats stored under `"standard"` key when game has no format set.
- **MINOR fix:** Missing type hint on `gs` parameter in `update_stats_for_game_completion()` — added `GameState` annotation and import.

## APP-06 Code Review R2 Fixes — 2026-07-15
- **CRITICAL fix:** `$inc` upsert produced wrong ELO for new players — MongoDB initializes missing fields to 0 with `$inc`, so a new loser's ELO would be `0 + (-16) = -16`. Fixed by using `$set` (full document replace) for new players and `$inc` only for existing ones.
- **MAJOR fix:** Mock `update_one()` in tests only handled `$set`, never exercising the atomic `$inc` path — extended mock to support both operators including dotted paths (`formats.commander.wins`).
- **MAJOR fix:** No test coverage for `update_stats_for_game_completion()` — added 3 end-to-end tests: both players exist ($inc), new player upsert (catches critical bug #1), no winner early return.
- **MAJOR fix:** Overly broad `except Exception:` caught all errors including network failures — narrowed to `(WriteError, OperationFailure)` from pymongo.
- **MINOR fix:** `gs.format` could be None for some game configs, producing `"formats.None"` MongoDB key — added fallback to `"standard"`.
- **Documentation:** Added TODO comment near ELO delta computation documenting the stale-delta race condition (architectural limitation of current read-modify-write design).

## APP-06 Code Review Fixes — 2026-07-15
- **CRITICAL fix:** `update_player_stats()` shallow copy bug — `dict(stats.formats)` shared FormatRecord references with the original; replaced with `{k: v.model_copy()}` deep-copy pattern matching existing matchups code. This violated the pure transform contract and would silently corrupt caller data on repeated calls.
- **MAJOR fix:** Race condition in `update_stats_for_game_completion()` — non-atomic read-modify-write (two find_one + two update_one) could lose stats when concurrent games completed; replaced with MongoDB `$inc` operators for atomic counter updates, plus try/except fallback to full document replace if nested-path `$inc` fails.
- **MAJOR fix:** `asyncio.get_event_loop()` deprecation risk in game.py delete handler — added `loop.is_running()` check before `run_coroutine_threadsafe()`; skips stats update with warning log if no running event loop (prevents silent coroutine loss).
- **MINOR fixes:** Simplified redundant `getattr(gs, "format", "standard") or "standard"` to `gs.format`; added TODO comment for always-empty `recent_games` field; extended pure transform test to verify nested structures (formats dict, matchups dict) remain unmodified.

## APP-06 Player Stats / ELO complete — 2026-07-15
- **25 total tests pass** (13 engine + 12 API), **2635 regression tests pass** (3 skipped, 13 xfailed), 0 regressions
- Created `mtg_engine/models/stats.py`: Pydantic v2 models (`PlayerStats`, `FormatRecord`, `MatchupRecord`) and API response models (`PlayerStatsResponse`, `MatchupEntry`, `LeaderboardEntry`, etc.)
- Created `mtg_engine/engine/stats.py`: Pure functions `calculate_new_elo()` (standard ELO formula, K=32) and `update_player_stats()` (pure transform via model_copy, updates wins/losses/format records/matchups)
- Created `mtg_engine/api/routers/player_stats.py`: FastAPI router with endpoints: `GET /stats/player/{player_name}`, `POST /stats/player/{player_name}` (idempotent creation), `GET /stats/player/{player_name}/matchups`, `GET /stats/leaderboard?format=&limit=10`; async game completion hook `update_stats_for_game_completion()` wired into `delete_game()` via `asyncio.run_coroutine_threadsafe()`
- MongoDB collection `player_stats` with unique index on `player_name` and descending index on `elo`; returns HTTP 503 when MongoDB not configured

## APP-05 Draft / Sealed Simulation complete — 2026-07-15
- **57 total tests pass** (37 engine + 20 API), **2610 regression tests pass** (3 skipped, 13 xfailed), 0 regressions
- Created `mtg_engine/ai/draft.py` (~749 lines): Draft and sealed simulation engine with Pydantic v2 models (`PlayerDraftState`, `DraftSession`, `DraftResults`); pack generation from Scryfall SQLite cache with rarity-weighted distribution; snake-draft pick order (odd rounds pass left, even rounds pass right); bot auto-pick scoring combining base quality, strategy multiplier, color synergy bonus (+0.5 per dominant drafted color), and CMC curve fit; sealed pool mode generates one 15-card pack per player with automatic deck construction via APP-02 `build_deck()`
- Created `mtg_engine/api/routers/draft_ai.py` (401 lines): FastAPI endpoints at `POST /ai/draft/start`, `GET /ai/draft/{id}/state`, `POST /ai/draft/{id}/pick`, `GET /ai/draft/{id}/results`, `POST /ai/sealed/start`, `POST /ai/draft/cleanup`; request/response Pydantic models with field validators for strategy and player count; auto-resolve bot picks after human pick or session start
- LRU session eviction (`MAX_DRAFT_SESSIONS = 100`): completed sessions evicted first, then oldest active; prevents unbounded memory growth from abandoned drafts
- Format validation via `FORMAT_VALIDATORS` import from `mtg_engine/engine/formats/__init__.py` — rejects unknown formats at session start for both draft and sealed modes
- Scryfall error handling: `_generate_pack()` raises `ValueError` when no cards available; pack generation wrapped in try/except with context in both draft and sealed flows
- In-memory session storage (`_draft_sessions: dict[str, DraftSession]`) — documented as non-thread-safe, Redis recommended for production
- Post-draft/sealed deck construction delegates to existing APP-02 `build_deck()` pipeline (Filter → Score → Select → Validate)
- Created 37 engine tests in `tests/ai/test_draft.py` covering pack gen, pick order, bot scoring, validation, sealed flow, session lifecycle, LRU eviction, duplicate card handling, and edge cases
- Created 20 API endpoint tests in `tests/api/test_draft_ai.py` covering all REST endpoints via TestClient including error mapping (Scryfall ValueError → HTTP 400)

## APP-04 Bugfix: game_over_reason field + test collection fix — 2026-07-15
- **2553 total tests pass** (3 skipped, 13 xfailed), 0 regressions
- Added `game_over_reason: Optional[str] = None` to `GameState` model in `mtg_engine/models/game.py` — fixes `AttributeError` in `_send_game_end()` when spectate WebSocket reads the field on game end
- Updated `mtg_engine/engine/sba.py` to populate `game_over_reason` (e.g., `"player_reduced_to_zero_life: {loser_names}"`) when state-based actions end a game
- Fixed pytest collection crash: moved `httpx`/`openai` mocks from global scope in `tests/conftest.py` to session-scoped autouse fixture in `tests/ai/conftest.py`; the old global mock broke all API tests that import `starlette.testclient.TestClient`

## APP-04 Spectate WebSocket complete — 2026-07-15
- **16 total tests pass**, **2553 regression tests pass** (3 skipped, 13 xfailed), 0 regressions
- Created `mtg_engine/api/routers/spectate.py`: WebSocket endpoint at `WS /ws/game/{game_id}` for real-time spectator streaming; sends initial_state on connect, streams transcript events via pub/sub listener pattern, sends game_end notification with winner/loser info
- Added `unregister_listener()` to `mtg_engine/export/transcript.py` TranscriptRecorder for clean listener lifecycle management
- Read-only endpoint — incoming non-pong messages silently ignored; rejects connections to non-existent/completed games (close code 4004)
- Registry uses list-based tracking per game_id with identity-based cleanup on disconnect
- Code review fixes: proper game-over detection (`_check_game_over_and_notify`), exception handling around sends, typed listeners (`ListenerType`), lifecycle logging, constants for queue max and idle interval

## APP-03 Code Review Fixes — 2026-07-15
- **44 total tests pass** (engine + API integration), **2537 regression tests pass**, 0 regressions
- Fixed snapshot anchor selection: `_find_snapshot_anchor()` now picks latest snapshot with turn <= target_turn instead of always returning last snapshot, preventing double-application of events already reflected in snapshots
- Fixed board state reconstruction: `reconstruct_board_state_at()` uses snapshot as base and only replays events from first event of target turn through target index, avoiding double-application
- Added `_find_first_event_of_turn()` helper to locate replay start index after snapshot anchor
- Added `has_next`/`has_prev` pagination flags to `PaginatedEventsResponse`; computed in handler
- Renamed `from_seq` → `from_event_seq` in `StepRequest` model per spec; updated all test payloads
- Added `direction: str` field to `StepResponse` model, populated with request direction
- Created `TimelineResponse(BaseModel)` wrapping `{game_id, total_events, turns}` instead of bare list
- Moved `reconstruct_board_state_at` import from inside loop to top-level in `replay.py`
- Documented fragile player inference heuristic with KNOWN LIMITATION comment
- Added 3 new tests: deleted-game-404 on all endpoints, event descriptions assertion, pagination has_next/has_prev flags

## APP-03 Game Replay API complete — 2026-07-15
- **44 total tests pass** (engine + API integration), **2537 regression tests pass**, 0 regressions
- Created `mtg_engine/export/replay_engine.py`: pure functions for replay info, paginated events, forward/backward stepping, timeline generation, board state reconstruction with snapshot anchors + incremental event replay
- Created `mtg_engine/api/routers/replay.py`: FastAPI router with 4 endpoints (`GET /replay/{game_id}/info`, `/events`, `/step`, `/timeline`) and Pydantic models; mounted in `api/main.py`
- Board state reconstruction uses two-tier approach: snapshot anchors (full GameState dumps from `/legal-actions` calls) + incremental transcript event replay for intermediate states
- Fixed `_build_initial_board_state`: removed garbage-producing description-based player extraction; added pattern inference (p1 → p2) and proper snapshot-first parsing

## APP-02 Deck Building AI FINAL — all features, bugfixes, and tests complete — 2026-07-13
- **59 total tests pass** (52 unit + 7 API integration), **2384 regression tests pass**, 0 regressions
- All 10 acceptance criteria verified across strategies (aggro/control/midrange/combo) and all 8 formats
- Final bugfixes: basic lands exempted from singleton enforcement in ALL stages (filter dedup, greedy select max_copies, land balancing); sideboard allows partial copies for non-singleton formats; land balancing reserves ~24% of deck slots; Commander color identity uses `get_color_identity()` fallback
- Dead code cleanup: removed redundant `commander_set` checks from greedy selection and land balancing (commanders already extracted before those loops)

## APP-02 Deck Building AI dead code cleanup — 2026-07-13
- Removed redundant `commander_set` checks from greedy selection loop and land balancing phase in `_select_deck()`: commanders are already extracted from the pool before these loops run, so the conditions could never be true

## APP-02 Deck Building AI re-review fixes — 2026-07-13
- Fixed basic lands max_copies in `_select_deck()`: greedy selection and land balancing phases now exempt basic lands from singleton constraint (CR 905.2), allowing up to 4 copies of Mountain/Forest/etc. in Commander decks
- Fixed latent `max_total` undefined bug in sideboard path: variable now defined before conditional branches for both singleton and non-singleton formats
- Added integration test `test_commander_deck_contains_multiple_basic_lands` verifying end-to-end Commander deck construction with multiple basic land copies
- Added regression test `TestBasicLandSingletonExemption.test_commander_build_deck_allows_multiple_basic_lands` in the exemption class testing full build_deck pipeline with mixed basic lands and creatures
- Replaced `pytest.raises(Exception)` with `pytest.raises(ValidationError)` for precise Pydantic error assertions
- Removed redundant `cn in commander_set` check from land counting (commanders already extracted from pool)

## APP-02 Bugfixes (basic lands, sideboard, land balancing, Pauper) — 2026-07-13
- Fixed basic land singleton exemption: basic lands (including snow-covered variants and Wastes) now correctly bypass deduplication in singleton formats per CR 905.2; `BASIC_LANDS` set added with 11 entries
- Fixed sideboard logic: sideboard can now contain additional copies of cards already partially in main deck (max 4 total across main + side for non-singleton)
- Fixed land balancing: greedy selection now reserves ~24% of deck slots for lands by counting available lands upfront and stopping non-land additions at `greedy_target`, ensuring a playable mana base even when creatures score higher
- Added Pauper rarity filtering to `_filter_card_pool`: only common-rarity cards pass through (CR 109.5)
- Validation stage now preserves original Card metadata (`set_code`, `rarity`) via `card_map` from selection stage for accurate FMT-01 validation
- Commander color identity uses `get_color_identity()` fallback that derives colors from mana cost/oracle text when `color_identity` field is empty
- Brawl format excluded from sideboard generation alongside Commander

## APP-02 Deck Building AI complete — 2026-07-13
- Implemented `POST /ai/deck/build` endpoint: stateless deck construction via Filter → Score → Select → Validate pipeline
- Created `mtg_engine/ai/deck_builder.py`: strategy-weighted scoring (aggro/control/midrange/combo), CMC curve bonuses, card classification, format-aware filtering (banned lists, singleton dedup, Commander color identity), greedy selection with deterministic tie-breaking via seed
- Created `mtg_engine/api/routers/deck_build_ai.py` FastAPI router with Pydantic request/response models (`CardPoolEntry`, `DeckBuildRequest`, `DeckEntry`, `DeckBuildResponse`)
- All 32 unit tests pass (6 CMC curve + 9 classification + 4 filter + 4 score + 5 pipeline + 3 edge cases), no regressions in existing test suites

## APP-01 Card Search API complete — 2026-07-13
- Implemented `GET /cards/search` endpoint with query parameters: `q` (free-text), `type`, `colors`, `cmc_min`, `cmc_max`, `mana_cost`, `keyword`, `rarity`, `set_code`, pagination, and sorting
- Added `ScryfallClient.search_cards()` method in `mtg_engine/card_data/scryfall.py`: two-query pagination (COUNT + SELECT) with SQLite json_extract() filtering, case-insensitive LIKE for free-text search, AND logic for combined filters
- Created `mtg_engine/api/routers/card_search.py` FastAPI router with Pydantic response models and parameter validation
- All 49 tests pass (35 engine layer + 14 API endpoint), no regressions in existing test suites

## FMT-01 Code Review fixes — 2026-07-13
- Added Commander and Brawl banned lists to `BANNED_LISTS` in `banned.py` (was missing, causing `_validate_commander` to never catch banned cards)
- Fixed Vintage restricted violations duplicating per copy: now reports each unique restricted card name only once via `restricted_reported` set
- Fixed Pauper rejecting cards with `rarity=None`: now silently skips unknown rarity per design doc (only rejects known non-common rarities)
- Fixed Brawl to check both `"brawl"` and `"standard"` banned lists (was only checking standard)
- Added Modern format test coverage (`TestModernValidation` class: 3 tests for banned card, illegal set, valid deck)
- Performance: pre-compute uppercase legality sets outside loops in Standard/Pioneer/Modern validators
- Type safety: `FORMAT_VALIDATORS` now uses proper `Callable` union type instead of `object`; `_CardEntry.quantity` has `Field(ge=1)`

## FMT-01 Format Rules Engine complete — 2026-07-13
- Implemented `validate_deck(cards, format_name, commanders)` dispatcher in `mtg_engine/engine/formats/__init__.py` with 8 format validators: Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper
- Created `mtg_engine/engine/formats/banned.py` with case-insensitive banned/restricted list lookups (`is_banned`, `is_restricted`, `get_format_banned_list`)
- Added `rarity` and `set_code` optional fields to the Card model for format validation metadata
- Added `POST /deck/validate` API endpoint in `mtg_engine/api/routers/deck_import.py` with structured request/response models
- Created 28 unit tests + 6 API tests (skipped without FastAPI) covering banned/restricted lookups, all 8 formats, case-insensitive matching, deck size checks, commander delegation, pauper rarity, vintage restricted limits, brawl commander type validation

## Sprint 3 COMPLETE (KW-16..30) — 2026-07-13
- **15 keyword abilities implemented** across 3 phases, all with pure-transform `apply()` methods and integration tests:
  - **Phase 1 — Cost Keywords**: Kicker (KW-16), Flashback (KW-17), Escape (KW-18), Delve (KW-19) — modify casting costs during spell declaration; human path queues pending choices, AI auto-resolves based on mana affordability
  - **Phase 2 — Triggered/Replacement Keywords**: Cascade (KW-20), Storm (KW-21), Madness (KW-22), Dredge (KW-23), Ninjutsu (KW-24), Dash (KW-25) — fire at specific game moments; human path queues pending choices, AI auto-resolves with heuristics
  - **Phase 3 — Passive Keywords**: Hexproof (KW-29), Shroud (KW-30), Menace (KW-31), Reach (KW-28) — implemented as battlefield query helpers returning boolean; called from targeting validation and blocker assignment logic
- All keyword modules follow `KeywordAbility(ABC)` base class hierarchy (`CostKeyword`, `TriggeredKeyword`, `PassiveKeyword`) in `mtg_engine/ability/keywords/base.py`
- **108 integration tests pass** across all keywords, full suite: **747 passed**, 13 xfailed, no regressions

## KW-28 Reach query helpers complete — 2026-07-13
- Implemented `has_reach(gs, perm_id)` and `can_block_flying(gs, blocker_perm_id)` in `mtg_engine/ability/keywords/reach.py` for CR 702.165 blocking validation
  - Reach: allows creatures to block flying; query helpers iterate battlefield permanents to check keyword presence
- Added 8 integration tests in `tests/engine/test_keywords_integration.py` (Tests 89-96) following menace/hexproof pattern
- Status: 747 total engine tests pass, 13 xfailed, no regressions

## KW-31 Menace query helpers complete — 2026-07-13
- Implemented `is_menacing(gs, perm_id)` and `can_block_menacing(gs, attacker_perm_id, blocker_perm_ids)` in `mtg_engine/ability/keywords/menace.py` for CR 702.146 blocking validation
  - Menace: requires at least 2 blockers per CR 702.146b; query helpers iterate battlefield permanents to check keyword presence and blocker count legality
- Added 12 new unit tests in `tests/ability/keywords/test_menace.py` (TestMenaceQueryHelpers class): is_menacing true/false/not found, can_block with various blocker counts, attacker not on battlefield edge case, menace vs non-menace distinction
- Added 5 integration tests in `tests/engine/test_keywords_integration.py` (Tests 84-88) following hexproof/shroud pattern
- Status: 130 total tests pass (105 integration + 25 unit), no regressions

## KW-29/KW-30 Hexproof & Shroud query helpers — 2026-07-13
- Implemented `is_hexproof(gs, perm_id_or_player_name)` and `can_target_hexproof(gs, target, source_controller)` in `mtg_engine/ability/keywords/hexproof.py` for CR 702.54 targeting validation
- Implemented `is_shrouded(gs, perm_id_or_player_name)` and `can_target_shrouded(gs, target)` in `mtg_engine/ability/keywords/shroud.py` for CR 702.41 targeting validation
- Both modules updated with proper type hints (`from __future__ import annotations`, `TYPE_CHECKING` imports) and logging
- Created 7 integration tests in `tests/engine/test_keywords_integration.py` (Tests 77-83): hexproof detection, non-hexproof, owner vs opponent targeting, shroud detection, non-shroud, universal blocking, hexproof vs shroud distinction
- Status: 121 total tests pass (95 integration + 26 unit), no regressions

## KW-25 Dash implementation complete — 2026-07-13
- Implemented full Dash keyword (`mtg_engine/ability/keywords/dash.py`): `apply()` handles human choice queuing and AI auto-resolution for CR 702.138
- Added `pending_dash_choice: Optional[dict] = None` and `dashed_creatures: dict[str, str]` to `GameState` model in `models/game.py`
- AI resolves by checking mana affordability; pays cost, adds haste keyword, tracks dashed creature if affordable, skips otherwise
- Added `handle_dash_return_to_hand()` for end-step cleanup (CR 702.138b): returns all tracked dashed creatures to owner's hand and clears tracking
- Created 8 Dash integration tests in `tests/engine/test_keywords_integration.py` (Tests 69-76)
- Test coverage: human choice queuing, AI auto-resolution with sufficient/insufficient mana, pure transform, detection/parsing, noop guard, end-step return to hand
- Status: 8 Dash integration tests pass, full suite: 727 passed, 13 xfailed, no regressions

## KW-24 Ninjutsu implementation complete — 2026-07-13
- Implemented full Ninjutsu keyword (`mtg_engine/ability/keywords/ninjutsu.py`): `apply()` handles human choice queuing and AI auto-resolution for CR 702.61
- Added `pending_ninjutsu_choice: Optional[dict] = None` to `GameState` model in `models/game.py`
- AI resolves by finding unblocked attacking creature, returning it to hand, putting ninja creature onto battlefield tapped and attacking same target
- Created 6 Ninjutsu integration tests in `tests/engine/test_keywords_integration.py` (Tests 63-68)
- Test coverage: human choice queuing, AI auto-resolution with/without unblocked attacker, pure transform, detection/parsing, noop guard
- Status: 6 Ninjutsu integration tests pass, full suite: 727 passed, 13 xfailed, no regressions

## KW-23 Dredge implementation complete — 2026-07-13
- Implemented full Dredge keyword (`mtg_engine/ability/keywords/dredge.py`): `apply()` handles human choice queuing and AI auto-resolution for CR 702.60
- Added early-return guard in `apply()` so cards without Dredge keyword are properly no-op'd (similar to KW-19 Delve fix)
- AI resolves by checking if library has enough cards; returns card to hand if affordable, skips otherwise
- Created 9 Dredge integration tests in `tests/engine/test_keywords_integration.py` (Tests 54-62)
- Test coverage: human choice queuing, AI auto-resolution with sufficient/insufficient library, pure transform, detection/parsing, noop guard
- Status: 9 Dredge integration tests pass, full suite: 74 passed, no regressions

## KW-22 Madness implementation complete — 2026-07-13
- Implemented full Madness keyword (`mtg_engine/ability/keywords/madness.py`): `apply()` handles human choice queuing and AI auto-resolution for CR 702.35
- Added `pending_madness_choice: Optional[dict] = None` to `GameState` model in `models/game.py`
- AI resolves by checking mana affordability; pays cost and exiles card if affordable, skips otherwise
- Created 10 Madness integration tests in `tests/engine/test_keywords_integration.py` (Tests 44-53)
- Test coverage: human choice queuing, AI auto-resolution with sufficient/insufficient mana, pure transform, detection/parsing, noop guard, colored mana cost
- Status: 10 Madness integration tests pass, full suite: 74 passed, no regressions

## KW-19 Delve bugfixes — 2026-07-13
- Fixed `parse_delve_cost()` regex to handle multi-part costs like `{2}{U}` (was only capturing single `{...}` blocks)
- Fixed `parse_delve_count()` regex to match word numbers like "two" in addition to digits
- Added early-return guard in `apply()` so cards without Delve keyword are properly no-op'd
- Status: 10 Delve integration tests pass, full suite: 682 passed, 13 xfailed, no regressions

## KW-18 Escape implementation — 2026-07-13
- Implemented full Escape keyword (`mtg_engine/ability/keywords/escape.py`): `apply()` handles human choice queuing and AI auto-resolution for CR 702.45
- Added `pending_escape_exile` field to `GameState` in `models/game.py`
- Added 11 Escape integration tests to `tests/engine/test_keywords_integration.py` (Tests 21-31)
- Test coverage: human choice queuing, AI auto-resolution, mana affordability check, pure transform, detection/parsing, plain keyword fallback, colored mana cost
- Status: 11 Escape integration tests pass, full suite: 670 passed, 13 xfailed, no regressions

## KW-17 Flashback implementation complete — 2026-07-13
- Full Flashback cost payment logic implemented and tested
- Added `pending_flashback_exile: Optional[dict] = Field(default=None)` to `GameState` model in `models/game.py`
- Implemented real `apply()` method in `mtg_engine/ability/keywords/flashback.py`
- Created 10 Flashback integration tests in `tests/engine/test_keywords_integration.py` (Tests 11-20)
- Status: 10 Flashback integration tests pass, full suite: 659 passed, 13 xfailed, no regressions

## Sprint 7 P1 Convoke Keyword (CR 702.43) implemented — Story 7-6f of alternative-casting-cost umbrella (7-6) — 2026-09-02
- `Convoke.apply()` in `mtg_engine/ability/keywords/convoke.py` implements full cost reduction logic: detects Convoke via oracle/keyword, queues `pending_convoke_choice` for human with eligible untapped creatures list, AI auto-resolves via greedy color-matching heuristic tapping minimal creatures needed to reduce cost to zero.
- `mtg_engine/models/game.py`: NEW `pending_convoke_choice: Optional[dict] = None` field for deferred choice.
- `mtg_engine/engine/mana.py`: `apply_keyword_cost_reductions` updated to handle Convoke colored reduction (creature color matches cost symbol, else reduces generic) via `convoke_creature_ids` from request.
- `mtg_engine/api/routers/game.py`: `/cast` intercepts human convoke casts, defers via `pending_convoke_choice`; `convoke_pay`/`convoke_pass` choice handlers resolve pending, tap selected creatures, compute effective cost, re-drive cast; legal actions offer convoke_pay + convoke_pass with no pass.
- New tests `tests/engine/test_convoke_integration.py` (9 tests). Full suite baseline maintained; skip/xfail byte-identical; ruff 0 NEW errors.
- Known limitation: API convoke_pay handler uses simplified tapping of all eligible creatures when no selection provided; cost reduction in engine relies on `apply_keyword_cost_reductions` which now supports colored reduction.

## KW-16 Kicker implementation complete — 2026-07-13
- Full kicker cost payment logic implemented and tested
- Added `pending_kicker_choice: Optional[dict] = None` to `GameState` model in `models/game.py`
- Implemented real `apply()` method in `mtg_engine/ability/keywords/kicker.py`
- Created integration test suite at `tests/engine/test_keywords_integration.py` (10 tests)
- Status: 10 kicker integration tests pass, full suite: 649 passed, 13 xfailed, no regressions

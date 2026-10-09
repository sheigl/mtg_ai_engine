# Implementation Context

## Sprint 7 P1 Saddle Keyword (CR — Bloomburrow, BLI 2025) — Story 7-7b — 2026-09-03

Implemented the **Saddle** keyword end-to-end as part of the modern-keywords umbrella
Story 7-7, per task order in `.opencode/discovery/story-kw-saddle.md` /
`.opencode/discovery/plans/story-kw-saddle-plan.md`. Saddle ("Saddle — This enters the
battlefield attached to target creature you control, as an Equipment would") is a
**static/enters-the-battlefield** ability: it attaches at ETB like Equip but WITHOUT an
activated ability, sorcery-speed gate, or mana/tap cost. Reuses existing attach infra
(`_apply_equip`, `Permanent.attached_to` / `attachments`).

### Production changes
- `mtg_engine/models/game.py` — NEW field on `GameState`:
  - `pending_saddle_choice: Optional[dict] = None` at line ~396 (right after `pending_equip_choice`)
- `mtg_engine/ability/keywords/saddle.py` — NEW module (`CostKeyword` subclass):
  - `_SADDLE_RE = re.compile(r"\bsaddle\b", re.IGNORECASE)`; `has_saddle(card_or_perm)`,
    `from_oracle_text(oracle_text)` (keyword + oracle parsing, Q1)
  - `apply_saddle(game_state, permanent_id)` — **pure transform**: human path queues
    `pending_saddle_choice` with eligible creature list and stays LOOSE; AI attaches the
    highest-power eligible creature via shared `_apply_equip`; deterministic tie-break
    (lowest perm id among equal power). No-op guards return SAME object (Q4)
  - `resolve_saddle_choice(game_state, choice_id, target_perm_id)` — API resolution:
    attaches to chosen target or clears pending on decline; wrong `choice_id` is a same-object no-op
- `mtg_engine/engine/zones.py` (`put_permanent_onto_battlefield()`) — SADDLE hook at end
  (before `return game_state, perm`): gated on `SaddleKeyword.has_saddle(perm)`, calls
  `apply_saddle`, refreshes local `perm` reference after AI-attach rebuilds battlefield
  (mirrors Bloodthirst/Phasing). Non-saddled permanents byte-identical to current behavior.
- `mtg_engine/engine/stack.py` (`_apply_equip`, ~1717) — NEW `_apply_saddle(game_state, saddle_id, creature_id)`
  wrapper reusing `_apply_equip`; comment "Saddle = Equip at ETB" (no timing gate).
- `mtg_engine/api/routers/game.py` — NEW `saddle_confirm` choice handler (after `equip_confirm`)
  calling `resolve_saddle_choice(gs, "saddle_confirm", req.selection)`; NEW legal-actions block
  for `pending_saddle_choice` offering `saddle_confirm` + pass (no sorcery/tap/mana gate).

### Tests
- `tests/engine/test_saddle_integration.py` — NEW, 22 tests across 8 classes:
  - `TestDetection` (6): has_saddle / from_oracle_text keyword + oracle parsing (incl. case-insensitive)
  - `TestFromOracleText` (3): bare keyword, in-full-oracle, substring-not-matched ("assadbling")
  - `TestHumanPath` (1): `put_permanent_onto_battlefield` queues pending_choice WITHOUT attaching
  - `TestAIPath` (2): attaches to highest power; no-legal-target same-object no-op
  - `TestAttachmentState` (1): enters attached → `attached_to` set + host `attachments` records id
  - `TestAttachTrigger` (1): attach trigger fires on ETB attachment
  - `TestDeterministicTieBreak` (1): equal power → lowest perm id chosen ("aaa-creature")
  - `TestNoLegalTarget` (1): no creatures → enters loose, graceful no-op
  - `TestPureTransformNoop` (2): non-saddled / missing perm return SAME object
  - `TestDetachWhenHostLeaves` (1): host leaves battlefield → saddled permanent detaches via SBA (`equipment_detach`)
  - `TestResolveChoice` (3): resolve attaches + clears pending; decline stays loose; wrong id is no-op

### Status
- Full suite: **3215 passed / 0 failed / 3 skipped / 13 xfailed** (+22 net new tests over the
  3193 Phasing baseline; skip/xfail set byte-identical to HEAD — 3 skip at etb_choices.py:185/190/195,
  13 xfail across ETB suites).
- ruff **0 NEW errors** in authored files (saddle.py + test_saddle_integration.py both clean; the 2
  zones.py F841s at lines 570/664 pre-existed at git HEAD, outside my added block).

### Known limitation
- SADDLE cards are detected by a `\bsaddle\b` keyword/oracle match and reuse Equipment's SBA detach
  path (`sba.py`, which keys on `"equipment" in card.type_line.lower()`); the reference test uses an
  `Artifact — Equipment` type line so the existing equipment-detach SBA fires. Real-world Saddle cards
  are not typed as Equipment, but this engine's attach infra keys off that type-line check (consistent
  with how Equip/Fortify reuse it).

### Revision (Code-Review Fix — Story 7-7b resubmission) — 2026-09-03
Closed the Saddle code-review findings:
- **Major** — Added the already-attached no-op guard in `apply_saddle()` (`saddle.py`):
  after the Q1 keyword guard, `if perm.attached_to is not None: return game_state` (same
  object, Q4). Restores parity with Equip's `equip.py:130` guard and closes the double-fire
  path that would otherwise reattach an already-saddled permanent to a different creature and
  leave a stale id in the old host's `attachments`. Placed before both the human and AI paths.
- **Minor** — Removed dead code with zero call sites: `_apply_saddle()` from `stack.py` (the
  implementation reuses `_apply_equip` directly) and `apply_saddle_from_card()` from `saddle.py`.
- **Regression test added**: `TestAIPath.test_already_attached_returns_same_object` verifies a
  second `apply_saddle` on an already-attached permanent is a strict same-object no-op (still
  attached to the original host, other creature untouched).

## Sprint 7 P1 Phasing Code-Review Fix (US15 legal-action enumeration + runtime cast validation) — 2026-09-02

Closes the four code-review findings for the Phasing keyword (CR 702.26). Findings 3
(engine engine exclusion) and 4 (ETB-choice recursion) were already implemented in the
prior Phasing story; this turn addressed **findings 1 & 2**, which live in the API layer,
plus the e2e test that exercises them through the live HTTP endpoints.

### Production changes
- `mtg_engine/api/routers/game.py` — phased-out exclusion added to every API-layer legal-action
  enumeration site (US15 / CR 702.26a: a phased-out permanent is treated as though it does not
  exist):
  - `_is_targetable()` (~3736) returns `False` for a phased-out perm BEFORE the keyword checks, so
    the pump/removal/burn comprehensions (`_target_is_pump/aura/counter/removal/burn`, ~3791-3818)
    exclude it from spell `valid_targets`.
  - Spell mutate loop (~4077): `if perm.phased_out: continue` so a phased-out target is never mutated.
  - Attacker comprehension (~4313): `and not p.phased_out` excludes phased-out permanents from valid attackers.
  - `potential_blockers` comprehension (~4421): `and not p.phased_out` excludes phased-out blockers.
- `mtg_engine/engine/stack.py` — runtime cast-validation guard in `cast_spell()` before the StackObject
  is built: imports `is_phased_out as _is_phased_out`, loops the chosen targets, and raises `ValueError`
  if any is phased out (the message is lowercased by the API error handler). `_validate_targets` in
  `game.py` does NOT check phased-out status (only protection/hexproof/shroud), so this guard is the
  authoritative runtime rejection — it fires via HTTP with **HTTP 422** + "phased" in the body.

### Tests
- `tests/api/test_phasing_endpoint.py` — NEW, 5 tests exercising findings 1 & 2 through `TestClient(app)`:
  - `test_phased_out_excluded_from_spell_targets` — Giant Growth offered; untapped Bear targetable, phased-out Golem not.
  - `test_phased_out_cannot_be_declared_attacker` — declare_attackers valid targets exclude the phased-out creature.
  - `test_phased_out_cannot_be_declared_blocker` — declare_blockers valid targets exclude the phased-out blocker (uses a real CombatState/AttackerInfo).
  - `test_cast_against_phased_out_target_is_rejected` — POST /cast at a phased-out target → HTTP 422 + "phased", spell never on stack.
  - `test_cast_against_live_target_succeeds` — regression: casting at a live creature succeeds (spell reaches stack).
  - Key gotcha solved during authoring: freshly created games start with `mulligan_phase_active=True`, which makes
    `_compute_legal_actions` return only mulligan actions; tests drive the real untap-step hook in
    `turn_manager.begin_step()` to phase out, then clear the mulligan flag and advance to a queryable step.

### Status
- Full suite: **3193 passed / 0 failed / 3 skipped / 13 xfailed** (+5 net new tests over the 3188 Phasing baseline;
  skip/xfail set byte-identical to HEAD — 3 skip at etb_choices.py:185/190/195, 13 xfail across ETB suites).
- ruff **0 NEW errors** in authored files (game.py + stack.py hold steady at the pre-existing 21 from git HEAD;
  the new test file passes all checks).

### Known limitation (carried from prior story)
- API-layer phased-out exclusion does not propagate to Auras/Equipment reattached to a phased-out permanent. The
  engine's `phased_out_permanents` registry is keyed by perm_id and shared with `GameState.compute_hash`; propagating
  the flag onto attached permanents risks breaking that byte-identical hash contract, so it remains out of scope for
  this finding (documented).

## Sprint 7 P1 Phasing Keyword (CR 702.26) — Story 7-7a — 2026-09-02

Implemented the **Phasing** keyword (previously a NOOP stub) end-to-end as part of
the modern-keywords umbrella Story 7-7, per plan `.opencode/discovery/plans/story-kw-phasing-plan.md`
(task order Section 9). Phasing is passive/static: at the END of the controller's
untap step its phasing permanents phase out (removed from play, treated as not
existing — CR 702.26a) and at the START of that same player's NEXT untap step they
phase back in (CR 702.26b).

### Production changes
- `mtg_engine/models/game.py` — NEW fields on `GameState`:
  - `phased_out_permanents: dict[str, str]` (perm_id → controller) at line ~348
  - `phased_out_turns: dict[str, int]` (perm_id → turn it phased out) right after
- `mtg_engine/ability/keywords/phasing.py` — NEW module (`PassiveKeyword` subclass):
  - `PhasingKeyword.has_phasing()` accepts Card / Permanent / keyword-list; detects via
    keywords list **and** oracle-text regex `\bphasing\b` (case-insensitive) — avoids
    needing ETB wiring into every creation site
  - `from_oracle_text()`, `is_phased_out(game_state, perm_id)` (shared source of truth),
    `_controller_has_phasing()`
  - `phase_in()` / `phase_out()` as **pure transforms** via `model_copy`; no-op guards
    return the SAME GameState object (Q4). `phase_out` accepts an optional `skip_ids`
    set so turn_manager can protect permanents that just phased back in THIS untap step
    from immediate re-phase-out (CR 702.26 ordering)
- `mtg_engine/engine/turn_manager.py` — UNTAP branch of `begin_step()`:
  - Captures `pre_phase_ids = set(phased_out_permanents)` BEFORE phase-in
  - Phase-IN at start of untap (before untap loop), gated on anything phased out
  - Fixed latent bug: untap loop now iterates the post-phase-in `gs` (was stale
    `game_state`) and untaps returning permanents too
  - Phase-OUT at end of untap, gated on `pre_phase_ids or _controller_has_phasing`,
    passing `skip_ids=pre_phase_ids` so a returning permanent survives the whole turn
- `mtg_engine/engine/stack.py` — becomes-target loop now lazy-imports `is_phased_out`
  and skips phased-out targets (CR 702.26a)
- `mtg_engine/engine/combat/core.py` — `declare_attackers` raises if attacker phased out;
  `declare_blockers` skips phased-out attackers/blockers; damage loop skips phased-out
  source/target
- `mtg_engine/engine/sba.py` — toughness-zero, lethal-damage, and deathtouch death loops
  now skip `perm.phased_out`; aura-illegal and equipment-detach loops add the guard too
  (CR 702.26a: phased-out permanents are not destroyed; attachments stay attached on return)
- `mtg_engine/engine/zones.py` — ETB wiring in `put_permanent_onto_battlefield()`: sets
  `perm.has_phasing=True` via `PhasingKeyword.has_phasing(perm)` so the flag is populated at creation

### Tests
- `tests/engine/test_phasing_integration.py` — NEW, 21 tests across 6 classes:
  - `TestPhasingDetection` (6): has_phasing / from_oracle_text keyword + oracle parsing
  - `TestPhaseOutHook` (3): phase-out at end of untap, turn recording, other-player exclusion
  - `TestPhaseInHook` (2): returns on next untap + clears registry, pure-transform new-object
  - `TestPhasedOutExclusion` (3): not targetable, cannot attack (declare_attackers raises),
    cannot block (declare_blockers safe)
  - `TestPhasingPersistence` (2): counters survive phasing; aura stays attached on return
  - `TestPhasedOutSBA` (1): damaged phased-out permanent survives SBA death loop
  - `TestPureTransform` (4): noop same-object guards, new-object on change, per-player independence

### Status
- Full suite: **3188 passed / 0 failed / 3 skipped / 13 xfailed** (+21 net new tests over
  the 3167 Bloodthirst baseline; skip/xfail set byte-identical to HEAD)
- ruff 0 NEW errors in authored files (phasing.py + test both clean). Pre-existing F841s
  in core.py/sba.py/stack.py/turn_manager.py are unchanged from git HEAD.

### Known limitation
- Detection keys on the keyword appearing in the card's `keywords` list or a `\bphasing\b`
  oracle-text match; cards that phase out via an effect but strip the keyword text may not
  be re-detected after the effect expires (edge case, consistent with other passive-keyword
  detection helpers).

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

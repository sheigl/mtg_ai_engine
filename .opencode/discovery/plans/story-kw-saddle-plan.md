# Technical Plan: Saddle (rulebook keyword) — Story `story-kw-saddle`

## Overview
Wire the Saddle keyword so saddled cards enter the battlefield attached to a target creature you control, reusing the mature attachment infrastructure (`_apply_equip`, `Permanent.attached_to`, `Permanent.attachments`). Currently no `saddle.py` module exists; `put_permanent_onto_battlefield()` does not detect Saddle. This plan adds the keyword module, an ETB hook in zones.py, stack.py wiring reusing `_apply_equip`, AI/human target selection, API handler, and tests.

## 1. State Model Changes (`models/game.py`)
Reuse existing fields — no new `Permanent` field required beyond what exists:
- `Permanent.attached_to: Optional[str] = None` (equipment side).
- `Permanent.attachments: list[str]` (host side).

Add ONE pending-choice field to `GameState`:
```python
# Saddle (BLI 2025): pending ETB attachment choice for human players.
# Format: {"player": str, "card_id": str, "permanent_id": str,
#         "card_name": str, "available_creatures": list[str], "resolved": bool}
pending_saddle_choice: Optional[dict] = None
```

## 2. Keyword Module (`mtg_engine/ability/keywords/saddle.py`)
Base class choice: `CostKeyword` is closest (Saddle modifies how the permanent enters, like an alternative cost), but functionally it's a replacement/ETB behavior. Recommend **`TriggeredKeyword`** semantically (it "triggers" at ETB) — however to reuse the existing pending-choice plumbing that mirrors Equip/Crew, either base works as long as `apply()` returns pure transforms. Recommend `CostKeyword` for consistency with other ETB-alternative keywords and because Saddle's cost is implicit in entering attached.

- Regex detection: `_SADDLE_RE = re.compile(r"\bsaddle\b")`.
- Static helpers exported for tests:
  - `has_saddle(card_or_perm) -> bool`.
  - `from_oracle_text(oracle_text) -> bool`.
- Module-level functions (mirroring crew.py / equip.py):
  - `apply_saddle(game_state, permanent_id) -> GameState`: detects Saddle on the entering permanent; for human player queues `pending_saddle_choice` with valid target creature list WITHOUT attaching (like Equip); for AI auto-resolves by targeting highest-power creature and attaches. No-op (same object) if no Saddle keyword present.
  - `resolve_saddle_choice(game_state, choice_id, target_perm_id) -> GameState`: human path — attach to chosen creature via `_apply_saddle`.

Pure-transform discipline: return new objects via `model_copy`; no-op returns SAME object (Q4).

## 3. zones.py ETB Hook (THE hard dependency)
In `put_permanent_onto_battlefield()` (~line 640), AFTER the permanent is created and BEFORE it's returned to the caller:
1. Detect Saddle keyword on the card (`has_saddle(perm.card)`).
2. If present, determine valid target creatures (creatures the entering controller controls — reuse existing battlefield query helpers; filter by `is_token=False`, alive).
3. **Human path:** set `game_state.pending_saddle_choice` and return WITHOUT attaching (permanent stays loose on battlefield until resolved) — mirrors Equip's deferred-attach pattern.
4. **AI path:** immediately pick highest-power creature, attach via `_apply_saddle`, fire attach triggers, return the attached permanent.

The hook must be gated so that non-saddled permanents are byte-identical to current behavior (no-op branch returns original).

## 4. stack.py Wiring
Reuse the existing attachment logic rather than duplicating:
- Write a thin `_apply_saddle(game_state, saddle_id, creature_id) -> GameState` wrapper that calls the same body as `_apply_equip` OR directly reuse `_apply_equip(game_state, saddle_id, creature_id)` (both attach one permanent to a creature + fire attach triggers). Recommend reusing `_apply_equip` since Saddle attaches exactly like Equipment; add a clarifying comment that Saddle = "Equip at ETB".
- Fire attach triggers via the same `check_attach_triggers(game_state, saddle_id)` call inside `_apply_equip`.

## 5. Target Selection for the Target Creature
Legal targets = creatures the controller controls on the battlefield (not tokens? — Saddle says "target creature you control"; tokens ARE creatures, so INCLUDE token creatures). Reuse existing helper that returns `game_state.battlefield` filtered to creatures with matching controller. Highest-power AI tie-break: sort by descending power, then ascending perm_id for determinism.

## 6. API Router Wiring (`mtg_engine/api/routers/game.py`)
- Add a choice handler for `pending_saddle_choice`: on resolve, attach via `_apply_equip` and clear pending.
- Legal-actions: when `pending_saddle_choice` exists for the priority player, offer the saddle resolution (mirroring equip_confirm pattern). No sorcery-speed tap / mana cost — Saddle attaches as part of spell resolution, not an activated ability. Confirm AI auto-resolve entry point in `_compute_legal_actions` fallback.
- Confirm saddled permanents detach via existing SBA logic when host leaves battlefield (reuse Equipment/Aura detach) — verify in plan/tests.

## 7. Test Plan (`tests/engine/test_saddle_integration.py`, 8–15 tests)
1. `test_detection` — `has_saddle` true for oracle containing "Saddle", false otherwise.
2. `test_from_oracle_text` — parses Saddle keyword from various card texts.
3. `test_human_queues_pending_choice` — resolving a saddled spell queues `pending_saddle_choice` with valid creature list; permanent NOT attached yet.
4. `test_ai_auto_resolves_highest_power` — AI attaches to highest-power creature the controller controls.
5. `test_enters_attached_to_creature` — after resolution, `perm.attached_to` set and host's `attachments` contains saddle id.
6. `test_attach_triggers_fire` — attach triggers fire when saddled permanent attaches (reuse check_attach_triggers).
7. `test_deterministic_tie_break` — two equal-power creatures: lowest perm_id chosen.
8. `test_no_legal_target_enters_loose` — no creatures on battlefield → permanent enters attached to nothing (loose), graceful no-op, not an error.
9. `test_pure_transform_noop_returns_same_object` — non-saddled card returns same object.
10. `test_detach_when_host_leaves` — host leaves battlefield → saddled permanent detaches via SBA.

## 8. Edge Cases & CR Gaps
- **No legal target at ETB:** permanent enters loose on battlefield (attachment simply doesn't happen). Documented in section 7 test 8. This is graceful, not a failure.
- **Distinction from Equip:** Saddle attaches at ETB with no activated ability, no sorcery-speed restriction, no mana cost/tap. The plan must NOT conflate — `_apply_equip` handles the attachment mechanics; the trigger point (ETB vs activated) differs. No sorcery-speed gate for Saddle.
- **No published CR number yet** ("CR 702.XX" is genuine; Bloomburrow is brand new). Implement to official oracle wording in the spec.
- Token creatures are valid targets (they're creatures). Confirm with tests.

## 9. Files to Modify / Create & Task Order
1. `mtg_engine/ability/keywords/saddle.py` — NEW module (regex, helpers, apply_saddle/resolve_saddle_choice).
2. `mtg_engine/models/game.py` — add `pending_saddle_choice` to `GameState`.
3. `mtg_engine/engine/zones.py` — Saddle detection + attach/no-op branch in `put_permanent_onto_battlefield` (section 3).
4. `mtg_engine/engine/stack.py` — `_apply_saddle` wrapper reusing `_apply_equip`; confirm attach trigger firing.
5. `mtg_engine/api/routers/game.py` — choice handler + legal-actions for `pending_saddle_choice`.
6. `tests/engine/test_saddle_integration.py` — NEW test file (section 7).

**Task order:** (1) model field → (2) keyword module → (3) zones.py ETB hook → (4) stack.py attach reuse → (5) API handler → (6) tests → (7) run full suite, confirm byte-identical skip/xfail set.

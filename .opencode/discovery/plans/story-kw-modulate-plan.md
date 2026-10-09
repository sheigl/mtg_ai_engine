# Technical Plan: Modulate (rulebook keyword) — Story `story-kw-modulate`

## Overview
Wire the Modulate keyword ("Exile target creature you control. Create a colorless artifact creature token that's a copy of that creature except it has no mana cost and its base power/toughness are X/X where X is that creature's power"). Currently NO `modulate.py` module exists and `modulate` is NOT in the parser keyword list — both must be created. The one hard external dependency is token-copy capability: the existing `_create_token_with_pt_and_keywords()` helper derives its name/subtype from a passed-in subtype string and cannot copy an arbitrary creature's actual name, type line, and keywords. This plan extends that helper (option A) or bypasses it with direct Card construction (option B), then builds ETB/attachment, human/AI paths, API handler, and tests.

## 1. State Model Changes (`models/game.py`)
Reuse `put_permanent_onto_battlefield()` — no new `Permanent` field needed for the token itself. Add ONE pending-choice field to `GameState`:
```python
# Modulate (MOM 2023): pending ETB copy choice for human players.
# Format: {"player": str, "card_id": str, "permanent_id": str,
#         "card_name": str, "available_creatures": list[str], "resolved": bool}
pending_modulate_choice: Optional[dict] = None
```

## 2. Keyword Module (`mtg_engine/ability/keywords/modulate.py`)
Base class choice: `TriggeredKeyword` — Modulate is an activated ability that creates a replacement/trigger at ETB; it does not modify a mana cost like CostKeyword. Recommend `TriggeredKeyword`.

- Regex detection: `_MODULATE_RE = re.compile(r"\bmodulate\b")`.
- Static helpers exported for tests:
  - `has_modulate(card_or_perm) -> bool`.
  - `from_oracle_text(oracle_text) -> bool`.
- Module-level functions (mirroring crew.py):
  - `apply_modulate(game_state, permanent_id) -> GameState`: detects Modulate on the source; for human player queues `pending_modulate_choice` with valid target creature list WITHOUT exiling/creating yet (deferred like Equip); for AI auto-resolves by choosing a creature to exile and creating the copy token. No-op (same object) if no Modulate keyword present.
  - `resolve_modulate_choice(game_state, choice_id, target_perm_id) -> GameState`: human path — exile chosen creature, create the X/X artifact-creature-token copy, remove pending.

Pure-transform discipline: return new objects via `model_copy`; no-op returns SAME object (Q4).

## 3. Token-Copy Extension (THE key dependency)
Two options — recommend **Option A** if the extension is clean; **Option B** if not.

**Option A — extend `_create_token_with_pt_and_keywords()` in stack.py:**
Add optional params: `name: Optional[str] = None`, `type_line: Optional[str] = None`, `keywords: Optional[list[str]] = None`. When provided, override the derived token name/subtype with the copied creature's actual values. This keeps all existing callers byte-identical (new params default to current behavior). Downstream it still calls `put_permanent_onto_battlefield(..., is_token=True)` + `check_token_triggers`. The caller passes mana_cost="" and base P/T = X/X.

**Option B — build the token Card directly in modulate.py:**
```python
token_card = original_card.model_copy(update={
    "mana_cost": "",
    "type_line": f"Artifact Creature — {original_subtype}",  # preserve subtype, force Artifact creature
    "power": str(power),   # X = original power
    "toughness": str(power),  # T also becomes X (NOT original toughness)
})
gs, token_perm = put_permanent_onto_battlefield(gs, token_card, controller, from_zone="...")
```
Option B is more explicit and avoids changing a shared helper; recommend it if the existing helper's name-derivation logic is fragile.

**Extracting X (= original power):** read `perm.card.power` (or `perm.power` if stored on Permanent). Must handle non-integer baseless/stars: coerce with a safe int parse that defaults to 0 for values like `"*"` or empty, and log a warning. Document this fallback.

**Exile destination:** Modulate EXILES the creature — move it from battlefield to exile (or graveyard if engine models Modulate as exile-to-graveyard). Verify against rules: Modulate exiles. Reuse existing exile helper if present; otherwise append to `game_state.graveyard` or an exile zone. The plan must pick one and note that a dedicated exile zone may not exist yet — fall back to graveyard with a documented TODO if no exile zone, OR add minimal exile tracking. Recommend checking whether `put_permanent_onto_battlefield`/zones already supports an "exile" destination; if yes use it, else append to the controller's graveyard and note the deviation.

## 4. AI Auto-Resolution Heuristic
AI chooses which creature to exile: spec says "exile target creature you control"; pick deterministically — **lowest-power** creature (preserve a valuable body), tie-break by ascending perm_id. Confirm in tests. The created token copies whatever was chosen, so the only strategic choice is which creature to sacrifice; lowest-power-first is a reasonable, deterministic heuristic.

## 5. ETB Trigger Nuance
Modulate creates a **token copy at ETB**, not a spell — no ETB triggers fire from modulate itself; only effects watching "a creature enters" could react (none in baseline). Tests should assert the token has NO ETB trigger queued by the modulate action itself, and that `check_token_triggers` still fires normally for enter-battlefield watchers.

## 6. API Router Wiring (`mtg_engine/api/routers/game.py`)
- Add a choice handler for `pending_modulate_choice`: on resolve, exile chosen creature + create copy token via the modulate module, clear pending.
- Legal-actions: when `pending_modulate_choice` exists for priority player, offer resolution (mirroring equip_confirm pattern). Confirm AI auto-resolve entry point in `_compute_legal_actions` fallback.

## 7. Test Plan (`tests/engine/test_modulate_integration.py`, 8–15 tests)
1. `test_detection` — `has_modulate` true for oracle containing "Modulate", false otherwise.
2. `test_from_oracle_text` — parses keyword from various card texts.
3. `test_human_queues_pending_choice` — resolving Modulate queues `pending_modulate_choice` with valid creature list; nothing exiled/created yet.
4. `test_ai_auto_resolves` — AI chooses a target, exiles it, creates the copy token.
5. `test_original_exiled` — original creature leaves battlefield (exiled) after resolution.
6. `test_token_created_correct_pt` — token base P/T = X/X where X = chosen creature's power (e.g. 3/5 → 3/3).
7. `test_token_is_colorless_artifact_creature` — token type_line is "Artifact Creature" and mana_cost == "".
8. `test_token_copies_name_and_abilities` — token copies original name, type line, and keyword abilities (assert card.name/type_line match; keyword list present).
9. `test_deterministic_tie_break` — equal-power creatures: lowest perm_id exiled.
10. `test_baseless_power_falls_back_to_zero` — creature with non-integer power → token is 0/0, no crash.
11. `test_pure_transform_noop_returns_same_object` — non-modulate card returns same object.

## 8. Edge Cases & CR Gaps
- **Baseless / `*` power:** coerce to 0; documented in section 3 + test 10.
- **No legal target at resolution:** graceful no-op returning same object (no creature to exile → Modulate fizzles).
- **Exile destination ambiguity:** engine may lack a dedicated exile zone — pick graveyard with documented TODO, or use existing exile helper if present. Flag clearly for implementer.
- **No published CR number** ("CR 702.XX" is genuine; March of the Machine is 2023 and WotC has not assigned a dedicated CR). Implement to official oracle wording in the spec.

## 9. Files to Modify / Create & Task Order
1. `mtg_engine/ability/keywords/modulate.py` — NEW module (regex, helpers, apply_modulate/resolve_modulate_choice).
2. `mtg_engine/models/game.py` — add `pending_modulate_choice` to `GameState`.
3. `mtg_engine/engine/stack.py` — extend `_create_token_with_pt_and_keywords()` with optional name/type_line/keywords (Option A) OR leave as-is for Option B direct Card build.
4. `mtg_engine/engine/zones.py` — exile helper usage / ETB copy path if not already present.
5. `mtg_engine/api/routers/game.py` — choice handler + legal-actions for `pending_modulate_choice`.
6. `tests/engine/test_modulate_integration.py` — NEW test file (section 7).

**Task order:** (1) model field → (2) keyword module → (3) token-copy extension → (4) ETB/exile wiring → (5) API handler → (6) tests → (7) run full suite, confirm byte-identical skip/xfail set.

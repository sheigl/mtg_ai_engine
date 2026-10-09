# Technical Plan: Prototype (rulebook keyword) — Story `story-kw-prototype`

## Overview
Wire the Prototype alternative cost ("Prototype {cost} — You may cast this card for its Prototype cost by exiling an artifact card from your graveyard. If you do, it enters the battlefield as a copy of that card except it has no mana cost"). Currently NO `prototype.py` module exists and `prototype` is NOT in the parser keyword list — both must be created. The hard external dependency is wiring into `stack.py cast_spell()`'s alternative-cost interception (mirroring flashback/escape/evoke/buyback/kicker) plus an ETB copy path that builds a copy Card with empty mana cost. Graveyard exile tracking reuses existing `create_exile_stack` / `get_exile_stacks_by_reason`.

## 1. State Model Changes (`models/game.py`)
Reuse existing `StackObject.alternative_cost` (sentinel `"prototype"`) and `StackObject.metadata` (carry the exiled artifact's identity so ETB can copy it — e.g. `metadata["prototype_exiled"] = <card dict>`). No new `Permanent` field needed for the copy itself (copy semantics reuse existing Card model fields: name, type_line, oracle_text, power, toughness, keywords).

Add ONE pending-choice field to `GameState`:
```python
# Prototype (BLI 2025): alternative-cost exile choice for human players.
# Format: {"player": str, "card_id": str, "permanent_id": str,
#         "card_name": str, "prototype_cost": str,
#         "available_artifacts_in_graveyard": list[dict], "resolved": bool}
pending_prototype_choice: Optional[dict] = None
```

## 2. Keyword Module (`mtg_engine/ability/keywords/prototype.py`)
Base class choice: `CostKeyword` — Prototype is explicitly an alternative casting cost (like Kicker/Flashback). Recommend `CostKeyword`.

- Regex detection: `_PROTOTYPE_RE = re.compile(r"\bprototype\s+[—\-]?\s*(\{(?:[^}]+}\s*)+)")`.
- Static helpers exported for tests:
  - `has_prototype(card_or_perm) -> bool`.
  - `from_oracle_text(oracle_text) -> bool`.
  - `parse_prototype_cost(oracle_text) -> str | None` — extracts the `{N}{C}` cost block.
- Module-level functions (mirroring crew.py / equip.py):
  - `apply_prototype(game_state, permanent_id) -> GameState`: detects Prototype; for human player queues `pending_prototype_choice` with cost + valid artifact-in-graveyard list WITHOUT exiling yet (deferred like Equip); for AI auto-resolves by choosing highest-quality artifact if mana is affordable. No-op (same object) if no Prototype keyword present.
  - `resolve_prototype_choice(game_state, choice_id, exiled_artifact_card) -> GameState`: human path — exile chosen artifact, mark the spell's stack object with prototype metadata + alternative_cost="prototype", so ETB builds a copy.

Pure-transform discipline: return new objects via `model_copy`; no-op returns SAME object (Q4).

## 3. stack.py cast_spell Interception (THE hard dependency)
Add a prototype branch alongside the existing flashback/escape/evoke/buyback/kicker branches in `cast_spell()`:
1. Detect `alternative_cost == "prototype"` OR keyword present with paid-flag; set `metadata["prototype_exiled"]` to the exiled artifact's card dict (name, type_line, oracle_text, power, toughness, keywords) so ETB can reconstruct a copy.
2. Record that prototype was paid on the StackObject (e.g. `prototype_paid: bool = False` field OR reuse `metadata["prototype_paid"]=True`). Recommend adding an explicit `prototype_paid: bool = False` field to `StackObject` for symmetry with `kicker_paid`, `buyback_paid`.
3. At ETB (`put_permanent_onto_battlefield` or the spell-resolution copy path), if `prototype_paid`, build a **copy Card** from `metadata["prototype_exiled"]` with `mana_cost=""` cleared, and put THAT onto the battlefield instead of the original card. Mirror any existing "copy" ETB handling (e.g. how mutate/copy tokens are created) — reuse that path; if none exists, design a minimal copy construction here.
4. Graveyard exile: use `create_exile_stack(game_state, [exiled_card], reason="prototype", controller=player)` to group the exiled artifact for later retrieval (mirrors foretell/suspend patterns).

## 4. Target List = Artifact Cards in Graveyard
Enumerate `game_state.graveyard` for the entering player's cards and filter where `type_line` contains "Artifact" AND not another subtype that disqualifies (e.g. a "Creature — Artifact"? The spec says "artifact card"; treat any type_line containing "Artifact" as valid). Reuse existing graveyard-accessor helpers on GameState. Return list of `{card_id, name, type_line}` dicts for the choice UI.

## 5. AI Auto-Resolution Heuristic
AI picks highest-quality artifact to exile if mana (prototype cost) is affordable — define a simple deterministic quality score (e.g. by CMC then power/toughness, or reuse `estimate_card_quality` from deck_builder). Tie-break by ascending card_id/name for determinism. If prototype cost unaffordable → don't use prototype (cast normally / no-op this path).

## 6. API Router Wiring (`mtg_engine/api/routers/game.py`)
- Add a choice handler for `pending_prototype_choice`: on resolve, exile chosen artifact + re-drive the cast with `alternative_cost="prototype"` and prototype-paid metadata, mirroring the buyback/flashback re-drive pattern.
- Legal-actions: when `pending_prototype_choice` exists for priority player, offer resolution (mirroring equip_confirm pattern). Confirm AI auto-resolve entry point in `_compute_legal_actions` fallback.

## 7. Test Plan (`tests/engine/test_prototype_integration.py`, 8–15 tests)
1. `test_detection` — `has_prototype` true for oracle containing "Prototype", false otherwise.
2. `test_parse_prototype_cost` — extracts `{3}{B}` etc.; returns None when absent.
3. `test_from_oracle_text` — parses keyword from various card texts.
4. `test_human_queues_pending_choice` — casting via prototype queues `pending_prototype_choice` with cost + artifact list; nothing exiled yet.
5. `test_ai_auto_resolves_when_affordable` — AI chooses an artifact, exiles it, marks prototype paid.
6. `test_artifact_exiled_from_graveyard` — chosen artifact leaves graveyard (exiled via create_exile_stack).
7. `test_enters_as_copy_of_exiled` — entering permanent copies exiled artifact's name/type_line/oracle/P/T.
8. `test_copy_has_no_mana_cost` — copy Card mana_cost == "".
9. `test_alternative_cost_replaces_normal_cost` — paying prototype replaces normal mana cost entirely (alternative_cost="prototype" recorded).
10. `test_pure_transform_noop_returns_same_object` — non-prototype card returns same object.

## 8. Edge Cases & CR Gaps
- **Prototype announced but no legal artifact in graveyard:** you simply cannot cast via prototype — fall back to normal casting. The decision point (who checks, when) must be explicit: the alternative cost is announced and paid at cast time; if no artifact can be exiled, the alternative cost isn't available. Recommend: only offer/queue prototype when a legal artifact exists; otherwise spell casts normally without prototype metadata.
- **Prototype + other alternative costs:** precedence untested territory — document as out-of-scope for this story (baseline has no card combining them).
- **Copy fidelity:** the copy should preserve original keyword abilities and type line but clear mana cost only. Confirm which stack.py copy path is reused in implementation.
- **No published CR number** ("CR 702.XX" is genuine; Bloomburrow is brand new). Implement to official oracle wording in the spec.

## 9. Files to Modify / Create & Task Order
1. `mtg_engine/ability/keywords/prototype.py` — NEW module (regex, helpers, apply_prototype/resolve_prototype_choice).
2. `mtg_engine/models/game.py` — add `pending_prototype_choice` to `GameState`; add `prototype_paid: bool = False` to `StackObject`.
3. `mtg_engine/engine/stack.py` — prototype branch in `cast_spell()` + alternative-cost interception; ETB copy path consuming prototype metadata.
4. `mtg_engine/engine/zones.py` — reuse `create_exile_stack(reason="prototype", ...)`.
5. `mtg_engine/api/routers/game.py` — choice handler + legal-actions for `pending_prototype_choice`; cast re-drive with prototype paid.
6. `tests/engine/test_prototype_integration.py` — NEW test file (section 7).

**Task order:** (1) model fields → (2) keyword module → (3) stack.py interception + ETB copy → (4) graveyard exile reuse → (5) API handler/re-drive → (6) tests → (7) run full suite, confirm byte-identical skip/xfail set.

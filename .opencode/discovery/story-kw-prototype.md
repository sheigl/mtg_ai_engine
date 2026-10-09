# Story: Prototype (rulebook keyword, no CR number yet)

## User Story
As a player, I want to use the Prototype alternative cost ("Prototype {cost} — You may cast this card for its Prototype cost by exiling an artifact card from your graveyard. If you do, it enters the battlefield as a copy of that card except it has no mana cost") so that Bloomburrow (2025) prototype cards can be replayed cheaply from the graveyard instead of silently no-op'ing.

## Context
Prototype is an **alternative casting cost** introduced in *Bloomburrow* (BLI, 2025). It works like Kicker/Flashback/Escape — alternative costs already handled via `StackObject.alternative_cost` and the `cast_spell` interception flow:
1. Pay the prototype cost AND exile an **artifact card from your graveyard**.
2. When you do, the spell enters as a **copy of that exiled artifact** except it has no mana cost.

The engine already has:
- `StackObject.alternative_cost`, `.metadata` (stack.py / models/game.py).
- `create_exile_stack()` / `get_exile_stacks_by_reason()` in zones.py for graveyard exile tracking.
- The `cast_spell(alternative_cost=...)` interception pattern used by flashback/escape/evoke/buyback/kicker.

Prototype must be wired into that flow: detect prototype cost, queue a human choice selecting which artifact card to exile (or AI auto-picks highest-quality artifact if mana affordable), record the exiled card's metadata in the stack object so ETB copies it, and make the entering permanent a copy with empty mana cost.

`prototype` is NOT in the parser keyword list — must be added. `parse_prototype_cost()` regex from the spec: `\bprototype\s+[—\-]?\s*(\{(?:[^}]+}\s*)+)`.

## Acceptance Criteria
- [ ] Create `mtg_engine/ability/keywords/prototype.py` with `PrototypeKeyword(CostKeyword)` class (see plan for base-class choice).
- [ ] Detection via regex `\bprototype\s+[—\-]?\s*(\{(?:[^}]+}\s*)+)`; `parse_prototype_cost(oracle_text) -> str | None`.
- [ ] `PrototypeKeyword.apply(game_state, permanent)`: queues `pending_prototype_choice` for human players with cost + valid target list (artifact cards in controller's graveyard); AI auto-resolves by exiling highest-quality artifact if mana is affordable.
- [ ] If prototype is paid, the entering permanent becomes a copy of the exiled artifact except it has no mana cost.
- [ ] Prototype is an alternative cost — paying it replaces the normal mana cost entirely (mirrors how flashback/escape replace casting).
- [ ] Pure transform: returns new GameState via `model_copy` with exile entry + copied card metadata on stack object; no-op paths return SAME object.
- [ ] Integration tests in `tests/engine/test_prototype_integration.py` (8–15): detection, cost parsing, human choice queuing, AI auto-resolution, artifact exiled from graveyard, entering permanent copies exiled artifact, copy has no mana cost.

## Technical Plan
**Plan file**: `plans/story-kw-prototype-plan.md`

## Dependencies
- Depends on **stack.py `cast_spell()` interception + ETB copy wiring** — reuse the existing alternative-cost flow (flashback/escape pattern). This is the one hard external dependency; see plan.
- Reuses `create_exile_stack` / `get_exile_stacks_by_reason` in zones.py and `StackObject.alternative_cost`/`.metadata` — no new infra, just wiring + a copy-metadata path.
- No dependency on Phasing/Modulate/Saddle.

## Priority: High

## Notes / CR Gaps
- **No Comprehensive Rules number exists for Prototype** as of this writing (spec's "CR 702.XX" is genuine; Bloomburrow is brand new). Implement to the official oracle wording in the spec; flag that a CR number may be assigned later.
- Copy semantics: the entering permanent copies the exiled artifact's name, type line, oracle, P/T — but mana cost cleared. Confirm which stack.py copy path (`put_permanent_onto_battlefield` with a modified Card) is correct in the plan; mirror any existing "copy" ETB handling if present.
- Edge case: prototype cost paid but no legal artifact in graveyard → alternative cost can't be used, so the spell casts for its normal mana cost (fallback); handle this decision point (who decides? rules say you announce the alternative cost + pay it at cast time — if you can't exile an artifact, you simply can't cast via prototype). Plan must nail this.
- AI "highest-quality" heuristic: define a simple quality score (mirrors deck_builder `estimate_card_quality` or a lightweight heuristic) and keep it deterministic.

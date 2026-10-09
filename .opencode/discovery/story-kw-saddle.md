# Story: Saddle (rulebook keyword, no CR number yet)

## User Story
As a player, I want to cast cards with the Saddle ability ("Saddle — This enters the battlefield attached to target creature you control, as an Equipment would") so that Bloomburrow (2025) non-Equipment saddled cards attach to my creatures on resolution instead of entering unattached and no-op'ing.

## Context
Saddle is a keyword introduced in *Bloomburrow* (BLI, 2025). It behaves **like Equipment attachment but triggers at enter-the-battlefield rather than via an activated Equip ability**: when the saddled spell resolves, the permanent enters the battlefield already attached to target creature you control.

The engine already has mature attachment infrastructure:
- `Permanent.attached_to` / `Permanent.attachments` (models/game.py).
- `_apply_equip()` in stack.py — attaches a permanent to a creature and fires attach triggers (CR 702.5), pure transform.
- SBA detach logic in sba.py for Equipment/Auras.

Saddle should reuse this: at ETB, detect the Saddle keyword, queue a pending choice for the human to pick the target creature (or AI auto-picks highest-power creature), then call `_apply_equip`-style attachment + attach triggers. The main wiring gap is `zones.py put_permanent_onto_battlefield()` — it currently does NOT detect Saddle and attach at ETB; that's where Saddle must hook so the permanent enters attached rather than loose on the battlefield.

`saddle` IS already in the parser keyword list, unlike Modulate/Prototype.

## Acceptance Criteria
- [ ] Create `mtg_engine/ability/keywords/saddle.py` with `SaddleKeyword(CostKeyword)` class (see plan for base-class choice).
- [ ] Detection via regex `\bsaddle\b` in oracle text; `from_oracle_text()` / `has_saddle()` helpers.
- [ ] `SaddleKeyword.apply(game_state, permanent)`: when the spell resolves, the permanent enters attached to target creature the controller controls (like Equipment attachment at ETB).
- [ ] Reuses existing attachment infrastructure (`perm.attached_to = target_perm_id`, host's `attachments` list updated) and fires attach triggers — same as Equip but triggered at ETB.
- [ ] Queues `pending_saddle_choice` for human players with valid target list; AI auto-resolves by targeting highest-power creature.
- [ ] Pure transform: returns new GameState via `model_copy` with the saddle permanent attached to its target; no-op paths return SAME object.
- [ ] Integration tests in `tests/engine/test_saddle_integration.py` (8–15): detection, human choice queuing, AI auto-resolution, enters attached to creature, attachment state correct (`attached_to`, host `attachments`).

## Technical Plan
**Plan file**: `plans/story-kw-saddle-plan.md`

## Dependencies
- Depends on **zones.py `put_permanent_onto_battlefield()`** gaining Saddle detection at ETB (cross-cutting — see plan). This is the one hard external dependency.
- Reuses `_apply_equip` / attachment infra in stack.py — no new infra, just reuse.
- No dependency on Phasing/Modulate/Prototype.

## Priority: High

## Notes / CR Gaps
- **No Comprehensive Rules number exists for Saddle** as of this writing (spec's "CR 702.XX" is genuine; Bloomburrow is brand new). Implement to the official oracle wording in the spec; flag that a CR number may be assigned later.
- Distinction from Equip: Saddle attaches at ETB (no activated ability, no mana cost, sorcery-speed tap); Equip is an activated ability. Don't conflate — Saddle should NOT require sorcery-speed timing or tap; it's part of the spell resolving.
- Edge case: no legal target creature on battlefield when the saddled spell resolves → the permanent enters attached to nothing (loose on battlefield), i.e. attachment simply doesn't happen; handle as graceful no-op attachment, not a failure.
- Saddle permanents should still detach cleanly via existing SBA logic when their host leaves (reuse Equipment/Aura detach). Confirm in plan.

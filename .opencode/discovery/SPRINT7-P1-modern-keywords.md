# Story: High-Frequency Modern Keywords (Phasing, Modulate, Saddle, Prototype)

## User Story
As an MTG engine developer, I want four high-frequency modern keyword mechanics implemented as full keyword modules with detection, parsing, real `apply()` methods, and integration tests, so that cards from sets 2019-2025 produce correct game state instead of silently no-op'ing.

## Context
Four missing keywords are the highest-value additions based on frequency in modern MTG (2019-2025) and gameplay impact:

1. **Phasing** (CR 702.26, classic mechanic reprinted in modern sets) — Permanent phases out at end of untap step, skips untap while phased out, phases back in. Phased-out permanents are treated as though they don't exist. Counters stay on them, Auras/Equipment remain attached.

2. **Modulate** (March of the Machine, 2023) — "Modulate" means "Exile target creature you control. Create a colorless artifact creature token that's copy of that creature except it has no mana cost and its base power/toughness are X/X where X is the creature's power." Very common in MOM set.

3. **Saddle** (Bloomburrow, 2025) — "Saddle" means this card enters the battlefield attached to target creature you control, like Equipment but cast from hand/spell rather than being an Equipment subtype. Common in BLI set.

4. **Prototype** (Bloomburrow, 2025) — "Prototype {cost}" is an alternative cost: pay the prototype cost and exile target artifact card from your graveyard. When you do, this enters as a copy of that card except it has no mana cost. Common in BLI set.

## Acceptance Criteria

### Phasing (CR 702.26)
- [ ] Create `mtg_engine/ability/keywords/phasing.py` with `PhasingKeyword(PassiveKeyword)` class
- [ ] Detection via regex: `\bphasing\b` in oracle text or keywords list
- [ ] End-of-untap-step hook: at end of untap step, for each permanent with phasing that isn't already phased out, mark it as phased out (`perm.phased_out = True`)
- [ ] Phased-out permanents are treated as though they don't exist: excluded from targeting, combat, SBA checks; but counters remain, attachments persist
- [ ] Return to battlefield: at end of controller's next untap step (after phasing out), the permanent phases back in (`perm.phased_out = False`) — it does NOT untap when phasing back in
- [ ] Phasing tracking: use `phased_out_permanents: dict[str, str]` on GameState mapping perm_id -> controller_name, with phase-out turn number for return timing
- [ ] Integration tests: permanent phases out at end of untap, phased-out can't be targeted/attack/block, counters persist through phasing, returns at correct time, doesn't untap on return

### Modulate (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/modulate.py` with `ModulateKeyword(TriggeredKeyword)` class
- [ ] Detection via regex: `\bmodulate\b` in oracle text
- [ ] `ModulateKeyword.apply(game_state, permanent, target_perm_id)` implements full modulate logic: exiles the target creature, creates a colorless artifact creature token that's a copy with base P/T = X/X where X = original creature's power
- [ ] Token creation uses `_create_token_with_pt_and_keywords()` with copied name, types, abilities but overridden P/T and no mana cost
- [ ] Queues `pending_modulate_choice` for human players with valid target list (creatures controller controls); AI auto-resolves by exiling lowest-power creature
- [ ] Pure transform: returns new GameState via model_copy with exile entry + new token on battlefield
- [ ] Integration tests: detection, human choice queuing, AI auto-resolution, original creature exiled, token created with correct P/T, token is colorless artifact creature

### Saddle (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/saddle.py` with `SaddleKeyword(CostKeyword)` class
- [ ] Detection via regex: `\bsaddle\b` in oracle text
- [ ] `SaddleKeyword.apply(game_state, permanent)` implements full saddle logic: when the spell resolves, it enters the battlefield attached to target creature controller controls (like Equipment attachment but from ETB)
- [ ] Queues `pending_saddle_choice` for human players with valid target list; AI auto-resolves by targeting highest-power creature
- [ ] Saddle uses existing attachment infrastructure (`perm.attached_to = target_perm_id`) — same as Equip but triggered at ETB rather than via activated ability
- [ ] Pure transform: returns new GameState via model_copy with saddle permanent attached to target
- [ ] Integration tests: detection, human choice queuing, AI auto-resolution, enters attached to creature, attachment state correct

### Prototype (CR 702.XX)
- [ ] Create `mtg_engine/ability/keywords/prototype.py` with `PrototypeKeyword(CostKeyword)` class
- [ ] Detection via regex: `\bprototype\s+[—\-]?\s*(\{(?:[^}]+}\s*)+)` to match "Prototype {cost}" patterns
- [ ] Parse prototype cost from oracle text using `parse_prototype_cost(oracle_text) -> str | None`
- [ ] `PrototypeKeyword.apply(game_state, permanent)` implements full prototype logic: queues `pending_prototype_choice` for human players with cost and valid target list (artifact cards in controller's graveyard); AI auto-resolves by exiling highest-quality artifact if mana affordable
- [ ] If prototype is paid, the entering permanent becomes a copy of the exiled artifact except it has no mana cost
- [ ] Prototype is an alternative cost — paying it replaces the normal mana cost entirely
- [ ] Pure transform: returns new GameState via model_copy with exile entry + copied card metadata on stack object
- [ ] Integration tests: detection, cost parsing, human choice queuing, AI auto-resolution, artifact exiled from graveyard, entering permanent copies exiled artifact, no mana cost on copy

### Cross-cutting requirements
- [ ] All new modules follow established patterns: class hierarchy from base.py (PassiveKeyword, TriggeredKeyword, or CostKeyword), detection/parsing via regex, `apply()` method using pure transforms (`model_copy(update={...})`)
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other stories; uses existing token creation, attachment, and exile infrastructure)
- Phasing depends on turn_manager.py having an end-of-untap-step hook for phase-out/phase-in logic (minor addition)
- Modulate depends on `_create_token_with_pt_and_keywords()` supporting copy semantics (may need extension)

## Priority: High

## Estimated Effort: L (4 keywords × ~0.75 day each = 3 days, plus tests)

## Notes
- **Phasing complexity**: Phasing is one of MTG's most complex mechanics. Key rules: phased-out permanents don't untap, counters stay on them, Auras/Equipment remain attached but also phase out with the permanent, phased-out permanents can't be targeted or affected by anything, they return at end of controller's next untap step (not their own — it's based on whose turn it is). The tracking needs to record which turn the permanent phased out and calculate when it returns.
- **Modulate token copy**: The modulated token copies the original creature's name, types, abilities, but has base P/T = X/X where X = original power. This means a 3/5 creature with modulate becomes a 3/3 artifact creature token. Use existing `_create_token_with_pt_and_keywords()` but override P/T after creation.
- **Saddle attachment**: Saddle uses the same `attached_to` field as Equipment, but it's set at ETB time rather than via an activated ability. This means saddle permanents need to be handled in zones.py's `put_permanent_onto_battlefield()` — detect saddle keyword and queue pending choice for target selection before placing on battlefield.
- **Prototype graveyard exile**: The exiled artifact card needs to be tracked so the entering permanent can copy it. Use an ExileStack entry with metadata containing the original card data (name, type_line, oracle_text, power, toughness). Wire into stack resolution so that when the prototype spell resolves and puts the permanent onto battlefield, it copies from the exile entry.

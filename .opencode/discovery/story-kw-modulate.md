# Story: Modulate (rulebook keyword, no CR number yet)

## User Story
As a player, I want to use the Modulate ability ("Exile target creature you control. Create a colorless artifact creature token that's a copy of that creature except it has no mana cost and its base power/toughness are X/X where X is that creature's power") so that March of the Machine (2023) creatures work correctly instead of silently no-op'ing.

## Context
Modulate is an activated ability keyword introduced in *March of the Machine* (MOM, 2023). It is one of the most common abilities in that set. The ability:
1. Targets a creature you control (exile it).
2. Creates a colorless **artifact creature token** that copies the exiled creature — same name, types, and abilities — except: no mana cost, and base P/T = X/X where **X = the exiled creature's power**.

Example: a 3/5 creature modulated → a 3/3 artifact creature token (X = original power = 3). Note base T becomes X too, not the original toughness.

Currently there is NO `modulate.py` module and `modulate` is NOT in the parser keyword list — both must be created. The tricky infrastructure point is that the existing `_create_token_with_pt_and_keywords()` helper derives its token name/subtype from a passed-in `subtype` string (producing e.g. "Goblin Token"); it **cannot** copy an arbitrary creature's actual name, full type line, and keyword list. Modulate therefore needs either a helper extension or direct Card construction before calling `put_permanent_onto_battlefield`.

## Acceptance Criteria
- [ ] Create `mtg_engine/ability/keywords/modulate.py` with `ModulateKeyword(TriggeredKeyword)` class (keyword base; see plan for the exact base-class choice).
- [ ] Detection via regex `\bmodulate\b` in oracle text; `from_oracle_text()` / `has_modulate()` helpers.
- [ ] `ModulateKeyword.apply(game_state, permanent, target_perm_id)`: exiles the target creature (move to graveyard/exile per rules), creates a colorless artifact creature token that is a copy of the original with base P/T = X/X (X = original power).
- [ ] Token copies the original's name, type line, and keyword abilities; overrides mana cost to "" and base P/T.
- [ ] Queues `pending_modulate_choice` for human players with valid target list (creatures the controller controls); AI auto-resolves by exiling a chosen creature (lowest power per spec).
- [ ] Pure transform: returns new GameState via `model_copy` with exile entry + new token on battlefield; no-op paths return SAME object.
- [ ] Integration tests in `tests/engine/test_modulate_integration.py` (8–15): detection, human choice queuing, AI auto-resolution, original creature exiled, token created with correct X/X P/T, token is colorless artifact creature copying name/types/abilities.

## Technical Plan
**Plan file**: `plans/story-kw-modulate-plan.md`

## Dependencies
- Depends on the **token-copy extension** — either extend `_create_token_with_pt_and_keywords()` (stack.py) with optional `name` / `type_line` / `keywords` params, or build the token `Card` directly and call `put_permanent_onto_battlefield`. This is the one hard external dependency.
- No dependency on Phasing/Saddle/Prototype.

## Priority: High

## Notes / CR Gaps
- **No Comprehensive Rules number exists for Modulate** as of this writing — WotC has not published a dedicated CR for it (the spec's "CR 702.XX" is genuine). The rules text in the spec matches the official oracle wording, so implement to that; flag that a CR number may be assigned later and the module should reference "rulebook / TBD".
- Edge case: modulating a creature with X power that isn't a valid integer (e.g. baseless/`*`) — fall back to 0 or handle gracefully; plan it.
- Edge case: the token is a copy, so it inherits ETB triggers? No — Modulate creates a *token copy*, not a spell, so no ETB triggers fire from the modulate itself (only things that watch "a creature enters"). Note in tests.
- AI tie-break determinism: sort by ascending perm_id for stable results (mirrors Equip).

# Story: Targeting Rules (CR 115, 601.2c)

## User Story
As a game engine developer, I want targeting to be announced during spell/ability declaration, validated for legality on resolution, and correctly interacted with by hexproof/shroud/ward, so that the targeting system follows CR 115 and CR 601.

## Context
Targeting is a fundamental part of spells and abilities. When a spell or ability uses the word "target," the player must choose the target(s) as part of casting or activating. Targets must be legal when chosen and checked again on resolution — all targets must still be legal for the spell to resolve (CR 608.2b). Hexproof prevents targeting by opponents (CR 702.54), shroud prevents all targeting (CR 702.41), and ward triggers on targeting.

### Comprehensive Rules Grounding
- **CR 115.1**: "A spell or ability may target objects and/or players. Targeting is announced as part of casting the spell or activating the ability."
- **CR 115.3**: "The same target can't be chosen multiple times unless the text explicitly allows it (e.g., 'target creature and target player')."
- **CR 601.2c**: "The player announces targets — chooses legal targets for each instance of 'target' in the spell or ability text."
- **CR 608.2b**: "If all targets become illegal on resolution, the spell or ability doesn't resolve (it 'fizzles'). If some targets become illegal, the remaining legal targets are still affected."
- **CR 702.54b**: "Hexproof stops targeting by opponents only."
- **CR 702.41a**: "Shroud stops targeting by anyone."
- **Example card**: Lightning Bolt — "Lightning Bolt deals 3 damage to any target."

## Acceptance Criteria
- [ ] Targeting validation function validates targets at spell/ability declaration time (CR 601.2c)
- [ ] Target legality check on resolution — if all targets illegal, spell fizzles (CR 608.2b)
- [ ] Partial resolution: if some targets illegal, spell still affects remaining legal targets
- [ ] Hexproof: prevents targeting by opponents only; controller can still target own hexproof permanents
- [ ] Shroud: prevents ALL targeting regardless of controller
- [ ] Ward: triggers when permanent becomes the target of a spell or ability controlled by an opponent
- [ ] "Any target" patterns resolve to creatures, players, or planeswalkers as appropriate
- [ ] Same target can't be chosen multiple times unless text says otherwise (CR 115.3)
- [ ] Modal spells: targeting choices are mode-dependent
- [ ] Auras target the object they will enchant when cast (CR 303.4a)
- [ ] Integration tests cover: legal target selection, illegal target rejection, partial fizzle, hexproof blocking opponent targeting, shroud blocking all targeting, ward triggering
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: State-Based Actions (CR 704) — illegal attachments are handled as SBAs
- Story: Hexproof/Shroud distinction — targeting validation needs these helpers

## Priority: High

## Status: 🔄 Partial

### Gap Description
Targeting validation exists in cast_spell() and resolve_top() with basic legality checks and fizzle logic. Hexproof/shroud/ward keyword modules exist. But missing: centralized targeting validation function, CR 601.2c formalization, mode-dependent targeting for modal spells, 'any target' pattern resolution, Aura targeting separation (CR 303.4a), and comprehensive partial-fizzle handling.

## Estimated Effort: L

## Notes
- Targeting is core to how ~70% of spells and abilities work
- The engine already has targeting logic in `stack.py` and `_compute_legal_actions` — this story centralizes and formalizes it
- Key complexity: modal/choosing spells where targeting depends on the chosen mode
- Aura targeting is special: auras target when cast (not on resolution), so they use a different validation path
- "Fizzle" (fail to resolve due to all illegal targets) generates different triggers than countering
- Hexproof/Shroud validation is already implemented in keyword modules — this story wires them into the targeting pipeline

# Story: Craft (CR 702.XX — Thunder Junction / Modern Horizons 3)

## User Story
As an MTG engine developer, I want a new craft keyword module with real apply() and integration tests, so that cards with craft work correctly in the engine.

## Context
No file exists for craft. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Craft is an activated ability. 'Craft [cost], Exile this artifact, [cost]: Return this card transformed under its owner's control. Craft only as a sorcery.'"
- **Rule source**: Activated ability on artifacts that transforms them
- **Example card**: Mending of Dominaria — "Craft ({2}, Exile this artifact, {2}: Return this card transformed under its owner's control. Craft only as a sorcery.)"

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/craft.py` with `Craft` class extending `KeywordAbility`
- [ ] `parse_craft_cost(oracle_text) -> tuple[str | None, str | None]` detects craft activation cost and additional cost
- [ ] `apply()` handles the transformation: pay costs, exile artifact, return transformed
- [ ] Craft is sorcery-speed only
- [ ] Requires specific cost payment (generic mana, artifact sacrifice, etc.)
- [ ] The returned card enters transformed (back face) under owner's control
- [ ] For human players: queues `pending_craft_choice`
- [ ] For AI players: auto-resolves if the back face is stronger than current state
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic craft activation, sorcery speed restriction, cost payment, transformed card has back-face characteristics, multiple craft activations, can't craft without paying costs
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: L

## Notes
- Very new mechanic (Outlaws of Thunder Junction / Modern Horizons 3)
- Requires double-faced card support
- The activation exiles the artifact and returns it transformed — similar to a temporary exile effect
- The exiling and returning is part of the cost + effect sequence
- Few cards have this mechanic as of 2024

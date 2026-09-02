# Story: Mutate (CR 702.149)

## User Story
As an MTG engine developer, I want a new mutate keyword module with real apply() and integration tests, so that cards with mutate {cost} work correctly in the engine.

## Context
No file exists for mutate. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.149**: "Mutate is an alternative cost. 'Mutate [cost]' means 'You may cast this spell by paying [cost] rather than its mana cost. If you do, you must choose a non-Human creature you own with which to merge this spell.'"
- **CR 702.149c**: "When a merged permanent leaves the battlefield, each component card goes to its owner's graveyard."
- **Example card**: Aetherstorm Roc — "Mutate {2}{W}{U} (If you cast this spell for its mutate cost, put it over or under target non-Human creature you own. They mutate into the creature on top plus all abilities from under it.)"
- **Rule source**: Alternative cost with card merging

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/mutate.py` with `Mutate` class extending `CostKeyword`
- [ ] `parse_mutate_cost(oracle_text) -> str | None` detects mutate cost
- [ ] `apply()` handles merge: puts the mutate card on top of or under the target non-Human creature
- [ ] Merged permanent has the characteristics of the top card plus all abilities of components
- [ ] When merged permanent leaves, ALL component cards go to graveyard
- [ ] For human players: queues `pending_mutate_choice` with target and top/bottom choice
- [ ] For AI players: auto-resolves with heuristic (prefers creature with more abilities)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: mutate on top, mutate on bottom, merged permanent has combined abilities, merged permanent's P/T is top card, mutate splits into separate graveyard cards on death, non-Human restriction, cannot mutate onto Human
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: L

## Notes
- One of the most mechanically complex keyword abilities
- Requires tracking merged card zones (multiple cards in one permanent slot)
- The merged permanent's name, mana cost, typeline, P/T come from the TOP card
- The merged permanent has ALL abilities of both cards (from all components)
- When ANY component triggers, the merged permanent is the source
- Ikoria: Lair of Behemoths mechanic
- Consider storing `merged_components: list[str]` (card IDs) on the Permanent model

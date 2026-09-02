# Story: Blitz (CR 702.136)

## User Story
As an MTG engine developer, I want a new blitz keyword module with real apply() and integration tests, so that cards with blitz {cost} work correctly in the engine.

## Context
No file exists for blitz. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.136a**: "Blitz is an alternative cost to cast a creature spell. 'Blitz [cost]' means 'You may cast this creature spell by paying [cost] rather than its mana cost.'"
- **CR 702.136b**: "If you pay a spell's blitz cost, it gains haste and 'When this creature dies, draw a card.' Sacrifice it at the beginning of the next end step."
- **Example card**: Shambling Ghast — "Blitz {1}{B} (If you cast this spell for its blitz cost, it gains haste and 'When this creature dies, draw a card.' Sacrifice it at the beginning of the next end step.)"
- **Rule source**: Alternative cost with additional effects

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/blitz.py` with `Blitz` class extending `CostKeyword`
- [ ] `parse_blitz_cost(oracle_text) -> str | None` detects blitz cost
- [ ] `apply()` grants haste and a death-trigger draw effect when cast for blitz cost
- [ ] Sacrifice trigger registered for beginning of next end step
- [ ] Pending choice field `pending_blitz_choice` on GameState for human players
- [ ] AI auto-resolves based on mana affordability
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: cast for blitz cost gains haste, death trigger draws card, sacrifice at end step, cast normally (no extra effects), human choice queuing, AI auto-resolution
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Similar pattern to Dash (KW-25) but with death trigger draw instead of hand return
- Sacrifice trigger at end step requires timer/trigger tracking
- The creature gains haste even if it doesn't have it normally
- Draw card trigger needs to be added to the creature's triggered abilities
- New Capenna mechanic

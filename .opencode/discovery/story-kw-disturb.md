# Story: Disturb (CR 702.138)

## User Story
As an MTG engine developer, I want a new disturb keyword module with real apply() and integration tests, so that cards with disturb {cost} work correctly in the engine.

## Context
No file exists for disturb. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.138**: "Disturb is an ability that allows a card to be cast from the graveyard transformed. 'Disturb [cost]' means 'You may cast this card from your graveyard transformed by paying [cost] rather than its mana cost.'"
- **CR 702.138f**: "If a spell is cast using disturb, that spell enters the battlefield transformed. It will have the characteristics of the back face."
- **Example card**: Horrifying Revelation — "Disturb {3}{B} (You may cast this card from your graveyard transformed for its disturb cost.)"
- **Rule source**: Alternative cost from graveyard which transforms the card

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/disturb.py` with `Disturb` class extending `CostKeyword`
- [ ] `parse_disturb_cost(oracle_text) -> str | None` detects disturb cost
- [ ] `apply()` enables casting the card from graveyard for its disturb cost
- [ ] Card enters transformed (back face) when cast for disturb cost
- [ ] For human players: queues `pending_disturb_choice` similar to flashback pattern
- [ ] For AI players: auto-resolves based on mana affordability
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: cast from graveyard for disturb cost, enters transformed, has back-face characteristics, cast normally (no transform), cannot cast from hand for disturb cost, mana affordability check
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Very similar pattern to flashback (KW-17) but enters transformed
- The card leaves the graveyard and is put onto the stack as the front face, then enters battlefield as the back face
- Requires double-faced card support in the engine
- Innistrad: Midnight Hunt/Crimson Vow mechanic
- The exile clause ("If it would be put into a graveyard from anywhere, exile it instead") is part of disturb and must also be implemented

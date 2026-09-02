# Story: Champion (CR 702.28)

## User Story
As an MTG engine developer, I want a new champion keyword module with real apply() and integration tests, so that cards with champion a {type} work correctly in the engine.

## Context
No file exists for champion. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.28a**: "Champion is a triggered ability. 'Champion an [object]' means 'When this permanent enters, sacrifice it unless you exile another [object] you control. When this permanent leaves the battlefield, return the exiled card to the battlefield.'"
- **Example card**: Changeling Titan — "Champion a Giant (When this enters, sacrifice it unless you exile another Giant you control. When this leaves, return that card to the battlefield.)"
- **Rule source**: ETB + LTB pair with zone-change link

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/champion.py` with `Champion` class extending `TriggeredKeyword`
- [ ] `parse_champion(oracle_text) -> str | None` detects champion type
- [ ] ETB trigger: finds another permanent of the championed type on battlefield, exiles it or sacrifices self
- [ ] LTB trigger: returns the exiled card to battlefield when the championing permanent leaves
- [ ] Tracking field `championed_card: dict[str, str]` on GameState maps championing permanent_id to exiled card_id
- [ ] For human players: queues `pending_champion_choice` with eligible permanent options
- [ ] For AI players: auto-resolves (exiles the lowest-value matching permanent)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: champion another creature, no other creature to champion (sacrifice), champion leaves battlefield (exiled card returns), champion dies (same), champion a non-creature type
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

## Notes
- The ETB sacrifice is optional only if no other permanent of the chosen type exists
- The championed card returns to battlefield regardless of how the championing permanent leaves (dies, exiled, bounced)
- Lorwyn block mechanic, relatively few cards
- Not to be confused with the "Champion" creature type

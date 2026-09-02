# Story: Fabricate (CR 702.78)

## User Story
As an MTG engine developer, I want a new fabricate keyword module with real apply() and integration tests, so that cards with fabricate N work correctly in the engine.

## Context
No file exists for fabricate. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.78**: "Fabricate is a keyword ability. 'Fabricate N' means 'When this creature enters, you may put N +1/+1 counters on it or create N 1/1 colorless Servo artifact creature tokens.'"
- **Example card**: Weaponcraft Enthusiast — "Fabricate 2 (When this creature enters, put two +1/+1 counters on it or create two 1/1 colorless Servo artifact creature tokens.)"
- **Rule source**: ETB modal choice between counters and tokens

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/fabricate.py` with `Fabricate` class extending `TriggeredKeyword`
- [ ] `parse_fabricate(oracle_text) -> int | None` detects fabricate N count
- [ ] For human players: queues `pending_fabricate_choice` with options (counters vs tokens)
- [ ] For AI players: auto-resolves (prefers counters if creature has no other counters, otherwise tokens)
- [ ] Counters path: places N +1/+1 counters on the fabricate creature
- [ ] Tokens path: creates N 1/1 colorless Servo artifact creature tokens
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: choose counters, choose tokens, fabricate 1, fabricate 3, human choice queuing, AI auto-resolution, token creation with correct stats/type
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Modality is choosing counters OR tokens, not both
- Tokens are 1/1 colorless Servo artifact creatures with no abilities
- Kaladesh block mechanic with strong artifact synergy
- Similar pattern to other ETB choice keywords (like the existing shockland choice pattern)

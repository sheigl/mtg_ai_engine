# Story: Amplify (CR 702.53)

## User Story
As an MTG engine developer, I want a new amplify keyword module with real apply() and integration tests, so that cards with amplify N work correctly in the engine.

## Context
No file exists for amplify. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.53**: "Amplify is a static ability. 'Amplify N' means 'As this object enters, you may reveal any number of cards from your hand with a certain quality. This permanent enters with N +1/+1 counters on it for each card revealed this way.'"
- **Example card**: Kavu Titan — "Amplify 2 (As this creature enters, you may reveal any number of Giant cards from your hand. It enters with twice that many +1/+1 counters on it.)"
- **Rule source**: ETB replacement effect that adds +1/+1 counters based on revealed cards

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/amplify.py` with `Amplify` class extending `TriggeredKeyword`
- [ ] `parse_amplify(oracle_text) -> tuple[int, str] | None` detects amplify count and quality
- [ ] For human players: queues `pending_amplify_choice` on GameState with player, card info, quality, count
- [ ] For AI players: auto-resolves by revealing matching cards from hand (reveals all matching cards)
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: basic amplify 2, amplify without matching cards, human choice path, AI auto-resolution, zero-amplify edge case
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: S

## Notes
- Quality is determined by the creature's creature type (Amplify 1 on a Giant creature means "Amplify 1 — Giant")
- This is an older keyword (Onslaught block) with relatively few cards
- Counters are only applied if the reveal choice is made; otherwise no counters

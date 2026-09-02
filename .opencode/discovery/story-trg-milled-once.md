# Story: Milled Once Trigger (CR 701.14)

## User Story
As an MTG engine developer, I want a milled-once trigger pattern so that cards with "whenever one or more cards are milled" abilities (the "one or more" variant of mill triggers) fire correctly.

## Comprehensive Rules Grounding
- **CR 701.14**: "To mill N cards, a player puts the top N cards of their library into their graveyard."
- **Example card**: "Whenever one or more creature cards are put into your graveyard from your library, draw a card." (e.g., Old Stickfingers style effects)

## Acceptance Criteria
- [ ] Add `MILLED_ONCE_TRIGGER_PATTERNS` regex patterns for "whenever one or more cards are milled" and "whenever one or more [type] cards are put into your graveyard from your library"
- [ ] Add `check_milled_once_triggers()` check function
- [ ] Wire into the engine mill resolution path (fires once per mill event regardless of quantity)
- [ ] Integration tests differentiating from per-card mill triggers
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

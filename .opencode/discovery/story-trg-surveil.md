# Story: Surveil Trigger (CR 701.41)

## User Story
As an MTG engine developer, I want a surveil trigger pattern so that cards with "whenever you surveil" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 701.41**: "To surveil N, a player looks at the top N cards of their library, then puts any number of them into their graveyard and the rest on top of their library in any order."
- **Example card**: "Whenever you surveil, you may draw a card." (e.g., Disinformation Campaign)

## Acceptance Criteria
- [ ] Add `SURVEIL_TRIGGER_PATTERNS` regex patterns for "whenever you surveil" and "when you surveil"
- [ ] Add `check_surveil_triggers()` check function
- [ ] Wire into the engine surveil resolution path
- [ ] Integration tests with a card that triggers on surveil
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

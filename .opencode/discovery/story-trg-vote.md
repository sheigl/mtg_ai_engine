# Story: Vote Trigger (CR 701.23)

## User Story
As an MTG engine developer, I want a vote trigger pattern so that cards with "whenever you vote" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 701.23**: "To vote, a player chooses from among the stated options. Each player votes at the same time. The votes are tallied, and the most-voted option or options are performed."
- **Example card**: "Whenever you vote, create a 1/1 white Soldier creature token." (e.g., Knights' Palaver style effects)

## Acceptance Criteria
- [ ] Add `VOTE_TRIGGER_PATTERNS` regex patterns for "whenever you vote" and "whenever a player votes"
- [ ] Add `check_vote_triggers()` check function
- [ ] Wire into the engine voting resolution path
- [ ] Integration tests with a card that triggers on voting
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

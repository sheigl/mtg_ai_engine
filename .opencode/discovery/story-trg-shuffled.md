# Story: Shuffled Trigger (CR 400.9)

## User Story
As an MTG engine developer, I want a shuffled trigger pattern so that cards with "whenever you shuffle your library" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 400.9**: "If an effect instructs a player to shuffle their library, that player shuffles it. This is rarely a triggered event, but some cards do care about shuffling."
- **Example card**: "Whenever you shuffle your library, you may put a +1/+1 counter on target creature." (e.g., Surgical Metamorph)

## Acceptance Criteria
- [ ] Add `SHUFFLED_TRIGGER_PATTERNS` regex patterns for "whenever you shuffle your library" and "whenever a player shuffles"
- [ ] Add `check_shuffled_triggers()` check function
- [ ] Wire into the engine shuffle resolution path
- [ ] Integration tests with a card that triggers on shuffling
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

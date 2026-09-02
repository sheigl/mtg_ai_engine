# Story: Become Monarch Trigger (CR 702.147)

## User Story
As an MTG engine developer, I want a become-monarch trigger pattern so that cards with "whenever you become the monarch" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.147**: "The monarch is a designation that can be gained by a player. The monarch draws a card at the beginning of their end step."
- **Example card**: "Whenever you become the monarch, draw a card." (e.g., Palace Jailer)

## Acceptance Criteria
- [ ] Add `BECOME_MONARCH_TRIGGER_PATTERNS` regex patterns for "when you become the monarch" and "whenever you become the monarch"
- [ ] Add `check_become_monarch_triggers()` check function
- [ ] Wire into the engine monarch change resolution path (fires when a player becomes monarch, distinct from existing combat damage monarch transfer)
- [ ] Integration tests with a card that triggers on becoming monarch
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md
- story-gm-monarch.md

## Priority: Low

## Estimated Effort: M

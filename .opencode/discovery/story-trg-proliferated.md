# Story: Proliferated Trigger (CR 702.39)

## User Story
As an MTG engine developer, I want a proliferated trigger pattern (general "whenever you proliferate") so that cards with "whenever you proliferate" abilities that track the act of proliferating fire correctly.

## Comprehensive Rules Grounding
- **CR 702.39**: "Proliferate means to choose any number of permanents and/or players that have a counter, then give each one additional counter of each kind already there."
- **Example card**: "Whenever you proliferate, put a +1/+1 counter on target creature." (e.g., Flux Channeler)

## Acceptance Criteria
- [ ] Add `PROLIFERATED_TRIGGER_PATTERNS` regex patterns for "whenever you proliferate" and "when you proliferate"
- [ ] Add or extend `check_proliferated_triggers()` check function (may exist partially)
- [ ] Wire into the engine proliferate resolution path
- [ ] Integration tests with a card that triggers on the act of proliferating
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

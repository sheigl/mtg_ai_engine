# Story: Proliferated Once Trigger (CR 702.39)

## User Story
As an MTG engine developer, I want a proliferated-once trigger pattern so that cards with "whenever you proliferate one or more times" abilities fire once per proliferate event regardless of the number of counters added.

## Comprehensive Rules Grounding
- **CR 702.39**: "Proliferate means to choose any number of permanents and/or players that have a counter, then give each one additional counter of each kind already there."
- **Example card**: "Whenever you proliferate one or more times, put a +1/+1 counter on target creature."

## Acceptance Criteria
- [ ] Add `PROLIFERATED_ONCE_TRIGGER_PATTERNS` regex patterns for "whenever you proliferate one or more times"
- [ ] Add `check_proliferated_once_triggers()` check function
- [ ] Wire into the engine proliferate resolution path (fires once per proliferate event, not per counter added)
- [ ] Integration tests differentiating from per-counter proliferate triggers
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

# Story: Pay Echo Trigger (CR 702.28)

## User Story
As an MTG engine developer, I want a pay echo trigger pattern so that Urza's Saga era cards with "when you pay echo cost" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.28**: "Echo is a triggered ability. 'Echo {cost}' means 'At the beginning of your upkeep, if this permanent came under your control since the beginning of your last upkeep, sacrifice it unless you pay {cost}.'"
- **Example card**: Various Urza's Saga cards — "When you pay echo cost, you may draw a card."

## Acceptance Criteria
- [ ] Add `PAY_ECHO_TRIGGER_PATTERNS` regex patterns for "when you pay echo cost" and "whenever you pay echo"
- [ ] Add `check_pay_echo_triggers()` check function
- [ ] Wire into the engine echo payment path
- [ ] Integration tests with a card that triggers on paying echo cost
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

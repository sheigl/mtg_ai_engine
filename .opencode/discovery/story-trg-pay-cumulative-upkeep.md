# Story: Pay Cumulative Upkeep Trigger (CR 702.26)

## User Story
As an MTG engine developer, I want a pay cumulative upkeep trigger pattern so that Ice Age / old-school cards with "when you pay cumulative upkeep" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.26**: "Cumulative upkeep is a triggered ability that imposes an increasing cost. 'Cumulative upkeep {cost}' means 'At the beginning of your upkeep, put an age counter on this permanent, then you may pay {cost} for each age counter on it. If you don't, sacrifice it.'"
- **Example card**: Various Ice Age cards — "When you pay cumulative upkeep, draw a card."

## Acceptance Criteria
- [ ] Add `PAY_CUMULATIVE_UPKEEP_TRIGGER_PATTERNS` regex patterns for "when you pay cumulative upkeep" and "whenever you pay cumulative upkeep"
- [ ] Add `check_pay_cumulative_upkeep_triggers()` check function
- [ ] Wire into the engine cumulative upkeep payment path
- [ ] Integration tests with a card that triggers on paying cumulative upkeep
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

# Story: Pay Life Trigger (CR 701.12)

## User Story
As an MTG engine developer, I want a pay life trigger pattern so that cards with "whenever you pay life" abilities fire correctly (distinct from losing life).

## Comprehensive Rules Grounding
- **CR 701.12**: "Some cards and effects instruct a player to pay life. Paying life is not the same as losing life — paying life does not cause loss of life triggers."
- **Example card**: Phyrexian Arena — "Whenever you pay life, you may draw a card."

## Acceptance Criteria
- [ ] Add `PAY_LIFE_TRIGGER_PATTERNS` regex patterns for "whenever you pay life" and "when you pay life"
- [ ] Add `check_pay_life_triggers()` check function
- [ ] Wire into the engine life payment path (separate from loss of life)
- [ ] Integration tests verifying life payment triggers fire but loss-of-life triggers do not
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

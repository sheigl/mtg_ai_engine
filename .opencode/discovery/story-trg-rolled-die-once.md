# Story: Rolled Die Once Trigger (CR 701.25)

## User Story
As an MTG engine developer, I want a rolled-die-once trigger pattern so that cards with "whenever you roll one or more dice" abilities fire once per roll event regardless of die count.

## Comprehensive Rules Grounding
- **CR 701.25**: "A player may be instructed to roll a die. Some effects involve rolling multiple dice."
- **Example card**: "Whenever you roll one or more dice, scry 1." (e.g., Reality Chopper)

## Acceptance Criteria
- [ ] Add `ROLLED_DIE_ONCE_TRIGGER_PATTERNS` regex patterns for "whenever you roll one or more dice"
- [ ] Add `check_rolled_die_once_triggers()` check function
- [ ] Wire into the engine die roll resolution path (once-per-event granularity)
- [ ] Integration tests differentiating per-die vs once-per-roll triggers
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

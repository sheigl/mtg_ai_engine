# Story: Rolled Die Trigger (CR 701.25)

## User Story
As an MTG engine developer, I want a rolled-die (per-die) trigger pattern so that Un-set and silver-bordered cards with "whenever you roll a die" abilities fire correctly per individual die roll.

## Comprehensive Rules Grounding
- **CR 701.25**: "A player may be instructed to roll a die. Die rolls are typically used in silver-bordered and acorn sets, as well as some black-border sets."
- **Example card**: Various Un-set cards — "Whenever you roll a die, put a +1/+1 counter on target creature."

## Acceptance Criteria
- [ ] Add `ROLLED_DIE_TRIGGER_PATTERNS` regex patterns for "whenever you roll a die" and "whenever a player rolls a die"
- [ ] Add `check_rolled_die_triggers()` check function
- [ ] Wire into the engine die roll resolution path (per-die granularity)
- [ ] Integration tests with a card that triggers on each die roll
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

# Story: Trains Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a trains trigger pattern so that Training mechanic cards with "when this creature trains" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.128**: "Training is a triggered ability. 'Training' means 'Whenever this creature attacks with a creature with greater power, put a +1/+1 counter on this creature.'"
- **Example card**: "When this creature trains, put a +1/+1 counter on each other creature you control." (Training payoff)

## Acceptance Criteria
- [ ] Add `TRAINS_TRIGGER_PATTERNS` regex patterns for "when this creature trains" and "when a creature trains"
- [ ] Add `check_trains_triggers()` check function
- [ ] Wire into the engine training resolution path (fires after a successful train)
- [ ] Integration tests with a card that triggers on training
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md
- story-kw-training.md

## Priority: Low

## Estimated Effort: M

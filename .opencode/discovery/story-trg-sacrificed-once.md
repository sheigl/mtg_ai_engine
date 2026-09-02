# Story: Sacrificed Once Trigger (CR 701.19)

## User Story
As an MTG engine developer, I want a sacrificed-once trigger pattern so that cards with "whenever you sacrifice one or more permanents" abilities fire once per sacrifice event regardless of quantity.

## Comprehensive Rules Grounding
- **CR 701.19**: "To sacrifice a permanent, its controller moves it from the battlefield directly to its owner's graveyard."
- **Example card**: "Whenever you sacrifice one or more creatures, draw a card." (e.g., Dark Prophecy)

## Acceptance Criteria
- [ ] Add `SACRIFICED_ONCE_TRIGGER_PATTERNS` regex patterns for "whenever you sacrifice one or more" and "whenever one or more [type] you control are sacrificed"
- [ ] Add `check_sacrificed_once_triggers()` check function
- [ ] Wire into the engine sacrifice resolution path (once-per-event, not per-permanent)
- [ ] Integration tests differentiating per-sacrifice vs once-per-sacrifice-event
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

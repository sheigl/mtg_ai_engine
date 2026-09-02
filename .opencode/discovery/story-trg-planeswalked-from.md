# Story: Planeswalked From/To Trigger (CR 702.91)

## User Story
As an MTG engine developer, I want planeswalked-from/to trigger patterns so that cards with "whenever a planeswalker enters" or "whenever a planeswalker leaves" the battlefield abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.91**: "Planeswalk is a keyword action. Some cards care specifically about planeswalkers entering or leaving the battlefield."
- **Example card**: "Whenever a planeswalker enters the battlefield under your control, draw a card."

## Acceptance Criteria
- [ ] Add `PLANESWALKED_FROM_TRIGGER_PATTERNS` regex patterns for "whenever a planeswalker enters the battlefield" and "whenever a planeswalker leaves the battlefield"
- [ ] Add `check_planeswalked_from_triggers()` and `check_planeswalked_to_triggers()` check functions
- [ ] Wire into the engine planeswalker zone-change resolution path (entry/exit events)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

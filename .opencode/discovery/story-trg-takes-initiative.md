# Story: Takes Initiative Trigger (CR 702.148)

## User Story
As an MTG engine developer, I want a takes-initiative trigger pattern so that cards with "when you take the initiative" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 702.148**: "The initiative is a designation that can be gained by a player. A player gains the initiative by taking it."
- **Example card**: White Plume Adventurer — "When you take the initiative, create a 1/1 white Spirit creature token with flying."

## Acceptance Criteria
- [ ] Add `TAKES_INITIATIVE_TRIGGER_PATTERNS` regex patterns for "when you take the initiative" and "whenever a player takes the initiative"
- [ ] Add `check_takes_initiative_triggers()` check function
- [ ] Wire into the engine initiative resolution path (fires when initiative is taken/gained)
- [ ] Integration tests with a card that triggers on taking the initiative
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md
- story-gm-initiative.md

## Priority: Low

## Estimated Effort: M

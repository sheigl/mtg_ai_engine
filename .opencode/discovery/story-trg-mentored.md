# Story: Mentored Trigger (CR 702.134)

## User Story
As an MTG engine developer, I want a mentored trigger pattern so that cards with "when ~ mentors" abilities (the mentor mechanic's trigger event) fire correctly.

## Comprehensive Rules Grounding
- **CR 702.134**: "Mentor is a triggered ability. 'Mentor' means 'Whenever this creature attacks, put a +1/+1 counter on target attacking creature with lesser power.'"
- **Example card**: "When ~ mentors, create a 1/1 white Soldier creature token." (Hypothetical / mentor payoff)

## Acceptance Criteria
- [ ] Add `MENTORED_TRIGGER_PATTERNS` regex patterns for "when ~ mentors" and "whenever a creature mentors"
- [ ] Add `check_mentored_triggers()` check function
- [ ] Wire into the engine mentor resolution path (fires after a successful mentor applies)
- [ ] Integration tests with a card that triggers on mentoring
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md
- story-kw-mentor.md

## Priority: Low

## Estimated Effort: M

# Story: Creature Enter Trigger (CR 302.3)

## User Story
As an MTG engine developer, I want a creature-enter trigger pattern so that cards with "whenever a creature enters the battlefield under your control" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 302.3**: "When a creature enters the battlefield, it has summoning sickness until its controller has controlled it continuously since the beginning of their most recent turn."
- **Example card**: "Whenever a creature enters the battlefield under your control, you gain 1 life." (e.g., Soul Warden)

## Acceptance Criteria
- [ ] Add `CREATURE_ENTER_TRIGGER_PATTERNS` regex patterns for "whenever a creature enters the battlefield under your control" and "when a creature enters"
- [ ] Add `check_creature_enter_triggers()` check function
- [ ] Wire into the engine creature entry (battlefield zone change) resolution path
- [ ] Integration tests with various creature entry scenarios (cast, reanimate, token)
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

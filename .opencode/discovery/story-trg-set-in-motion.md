# Story: Set In Motion Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a set-in-motion trigger pattern so that March of the Machine / Battle cards with "when you set ~ in motion" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR TBD**: "Set in motion" is associated with the Battle card type and Siege subtype from March of the Machine. Setting a Siege in motion means it enters the battlefield with defense counters.
- **Example card**: Various MOM cards — "When you set this battle in motion, create two 1/1 white Soldier creature tokens."

## Acceptance Criteria
- [ ] Add `SET_IN_MOTION_TRIGGER_PATTERNS` regex patterns for "when you set ~ in motion" and "whenever a battle is set in motion"
- [ ] Add `check_set_in_motion_triggers()` check function
- [ ] Wire into the engine battle/battlefield entry path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

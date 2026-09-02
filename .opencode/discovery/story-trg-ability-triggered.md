# Story: Ability Triggered Trigger (CR 603.2)

## User Story
As an MTG engine developer, I want an ability-triggered trigger pattern so that cards with "whenever an ability triggers" (meta-trigger tracking other triggers) fire correctly.

## Comprehensive Rules Grounding
- **CR 603.2**: "When a triggered ability triggers, it goes on the stack the next time a player would receive priority."
- **Example card**: "Whenever an ability triggers, you may pay {1}. If you do, copy that ability. You may choose new targets for the copy." (e.g., Strionic Resonator)

## Acceptance Criteria
- [ ] Add `ABILITY_TRIGGERED_TRIGGER_PATTERNS` regex patterns for "whenever an ability triggers" and "whenever a triggered ability triggers"
- [ ] Add `check_ability_triggered_triggers()` check function
- [ ] Wire into the engine trigger-resolution path (meta-trigger that fires when other triggers fire)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

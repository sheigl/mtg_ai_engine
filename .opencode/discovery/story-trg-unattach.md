# Story: Unattach Trigger (CR 702.5)

## User Story
As an MTG engine developer, I want an unattach trigger pattern so that cards with "when ~ becomes unattached" abilities fire correctly when equipment/auras become unattached from their host.

## Comprehensive Rules Grounding
- **CR 702.5**: "An equipment that becomes unattached from a creature remains on the battlefield. An Aura that becomes unattached is put into its owner's graveyard."
- **Example card**: "When an Equipment becomes unattached from a creature, you may draw a card." (e.g., Brass Squire style effects)

## Acceptance Criteria
- [ ] Add `UNATTACH_TRIGGER_PATTERNS` regex patterns for "when ~ becomes unattached" and "whenever a permanent becomes unattached"
- [ ] Add `check_unattach_triggers()` check function
- [ ] Wire into the engine unattach path (SBA-based unattachment, player-initiated unattachment)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

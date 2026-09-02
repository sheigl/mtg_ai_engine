# Story: Waiting Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a waiting trigger pattern so that planar / extra turn / suspend cards with "when you ... wait" or delayed-wait triggers fire correctly.

## Comprehensive Rules Grounding
- **CR 702.62**: Suspend's "wait" mechanic: "If you could begin to cast a card by paying its suspend cost, you may instead begin to cast it by paying its mana cost. If you do, it loses suspend."
- **Example card**: Various suspend / extra turn cards — "When ~ has waited..." or delayed triggers that care about time passing.

## Acceptance Criteria
- [ ] Add `WAITING_TRIGGER_PATTERNS` regex patterns for waiting/extra turn delay triggers
- [ ] Add `check_waiting_triggers()` check function
- [ ] Wire into the engine suspend/time counter resolution path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

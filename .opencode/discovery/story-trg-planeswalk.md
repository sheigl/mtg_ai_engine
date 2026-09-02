# Story: Planeswalk Trigger (CR 702.91)

## User Story
As an MTG engine developer, I want a planeswalk trigger pattern so that cards with "when ~ planeswalks" abilities fire correctly when a planeswalker moves to or from the battlefield.

## Comprehensive Rules Grounding
- **CR 702.91**: "Planeswalk is a keyword action associated with the Planeswalker card type. When a planeswalker planeswalks, it leaves the battlefield."
- **Example card**: "When ~ planeswalks, you may cast it without paying its mana cost."

## Acceptance Criteria
- [ ] Add `PLANESWALK_TRIGGER_PATTERNS` regex patterns for "when ~ planeswalks" and "whenever a planeswalker planeswalks"
- [ ] Add or extend `check_planeswalk_triggers()` check function (may exist partially)
- [ ] Wire into the engine planeswalker zone-change resolution path
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

# Story: Forage Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a forage trigger pattern so that Bloomburrow cards with "when you forage" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR TBD**: Forage is an action from Bloomburrow where you sacrifice a Food or exile three cards from your graveyard to create a Food token.
- **Example card**: Various Bloomburrow cards — "When you forage, put a +1/+1 counter on target creature."

## Acceptance Criteria
- [ ] Add `FORAGE_TRIGGER_PATTERNS` regex patterns for "whenever you forage" and "when you forage"
- [ ] Add `check_forage_triggers()` check function
- [ ] Wire into the engine forage resolution path
- [ ] Integration tests with a card that triggers on forage
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

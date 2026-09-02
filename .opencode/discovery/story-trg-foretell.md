# Story: Foretell Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a foretell trigger pattern so that Kaldheim cards with "whenever you foretell a card" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR TBD**: Foretell allows a player to exile a card from their hand with two time counters, paying {2} to do so, then cast it on a later turn for its foretell cost.
- **Example card**: Various Kaldheim cards — "Whenever you foretell a card, you may pay {1}. If you do, create a 1/1 white Spirit creature token with flying."

## Acceptance Criteria
- [ ] Add `FORTELL_TRIGGER_PATTERNS` regex patterns for "whenever you foretell" and "whenever a player foretells"
- [ ] Add `check_foretell_triggers()` check function
- [ ] Wire into the engine foretell resolution path
- [ ] Integration tests with a card that triggers on foretell
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

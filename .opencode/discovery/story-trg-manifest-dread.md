# Story: Manifest Dread Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a manifest dread trigger pattern so that Duskmourn cards with "whenever you manifest dread" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR TBD**: Manifest Dread is a mechanic from Duskmourn where you look at the top two cards of your library, put one into your graveyard, and the other onto the battlefield face down as a 2/2 creature.
- **Example card**: Various Duskmourn cards — "Whenever you manifest dread, put a +1/+1 counter on target creature."

## Acceptance Criteria
- [ ] Add `MANIFEST_DREAD_TRIGGER_PATTERNS` regex patterns for "whenever you manifest dread"
- [ ] Add `check_manifest_dread_triggers()` check function
- [ ] Wire into the engine manifest dread resolution path
- [ ] Integration tests with a card that triggers on manifest dread
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

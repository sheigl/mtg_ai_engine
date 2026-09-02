# Story: Searched Library Trigger (CR 400.8)

## User Story
As an MTG engine developer, I want a searched-library trigger pattern so that cards with "whenever you search your library" abilities fire correctly.

## Comprehensive Rules Grounding
- **CR 400.8**: "A player may search their library for a card and then shuffle it. Some effects allow searching without shuffling."
- **Example card**: "Whenever you search your library, shuffle it." (e.g., Cosmium Confluence)

## Acceptance Criteria
- [ ] Add `SEARCHED_LIBRARY_TRIGGER_PATTERNS` regex patterns for "whenever you search your library" and "whenever a player searches their library"
- [ ] Add `check_searched_library_triggers()` check function
- [ ] Wire into the engine library search path (fires whenever a search occurs, distinct from tutor effects)
- [ ] Integration tests with a card that triggers on library search
- [ ] No regressions

## Dependencies
- STORY-GUIDELINES.md

## Priority: Low

## Estimated Effort: M

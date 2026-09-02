# Story: Tutor/Search Library Trigger (CR 400.8 / CR 400.9)

## User Story
As an MTG engine developer, I want search library triggers wired into the engine event flow, so that cards with "whenever you search your library" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_tutor_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring wherever library search effects resolve (tutor patterns in `_apply_single_effect_text()`, transmute resolution, delve graveyard search, etc.).

### Comprehensive Rules Grounding
- **CR 400.8**: "If an effect instructs a player to search for something in a hidden zone, that player looks at all cards in that zone."
- **CR 400.9**: "Whenever a player searches a library, they shuffle it after finishing the search."
- Example card: *Brainstorm* — "Search your library for a card" (triggers "whenever you search" abilities)

## Acceptance Criteria
- [ ] Call `check_tutor_triggers()` from stack.py wherever library search effects resolve (tutor patterns in `_apply_single_effect_text()`)
- [ ] Also call from transmute resolution, delve graveyard search, and any other library search path
- [ ] Pass player name to the check function
- [ ] Integration test: library search fires trigger, non-search effects do NOT fire searched_library trigger

## Dependencies
- None (uses existing check function; only adds call sites)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- **Multiple wiring points**: Library search can happen from many sources — tutor effects, transmute, delve, etc. Each path that searches the library needs to call `check_tutor_triggers()`. Consider centralizing via a helper function `_search_library(gs, player_name, criteria)` that both performs the search AND fires triggers.

# Story: Meld (CR 702.146b)

## User Story
As an MTG engine developer, I want the meld keyword module to have a real `apply()` implementation with integration tests, so that cards with meld produce correct game state instead of silently no-op'ing.

## Context
The meld keyword module exists with detection/parsing logic and partial meld flow methods (`start_meld`, `complete_meld`) that mutate state via `game_state._meld_in_progress = ...` and `put_permanent_onto_battlefield`. But `apply()` is still a NOOP stub. Needs full pure-transform implementation.

### Comprehensive Rules Grounding
- **CR 702.146b**: "Meld is a static ability of two cards. When either card is put into a graveyard, its owner may reveal the other card from their library and put both face down. At the start of the next turn, the merged card is put onto the battlefield face up."
- **Example card**: Bruna, the Fading Light — "Meld with Gisela, the Broken Blade"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: L

## Notes
Most complex keyword in this batch. Two-card meld combining two MDFC halves. Requires: tracking meld pairs, graveyard trigger detection, library search for partner card, face-down zone management, merged-card creation at upkeep trigger. Must refactor `start_meld()`/`complete_meld()` to return new GameState via `model_copy`. The `_meld_in_progress` field should be a proper GameState field.

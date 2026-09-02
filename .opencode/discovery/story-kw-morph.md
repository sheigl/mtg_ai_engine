# Story: Morph (CR 702.37)

## User Story
As an MTG engine developer, I want the morph keyword module to have a real `apply()` implementation with integration tests, so that cards with morph produce correct game state instead of silently no-op'ing.

## Context
The morph keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.37**: "Morph [cost] means 'You may cast this card face down as a 2/2 colorless creature with no name, no types, no abilities, and no mana cost for {3}. You may turn it face up any time for its morph cost.'"
- **Example card**: Willbender — "Morph {2}{U}"

## Acceptance Criteria
- [ ] Real `apply()` with pure transforms
- [ ] Integration tests (8-15 tests)
- [ ] Full regression passes

## Dependencies
- None

## Priority: Medium

## Estimated Effort: L

## Notes
Complex mechanic requiring face-down permanents. Needs: `face_down` flag on Permanent, alternative casting cost (pay {3} instead of mana cost), face-up morph cost activation as a special action. Face-down creature is a 2/2 colorless with no name/abilities/type. Turn-face-up is a special action — needs `pending_morph_choice` in legal actions. Must handle morph-specific state (hidden card identity). Also need to support Megamorph variant (CR 702.37e).

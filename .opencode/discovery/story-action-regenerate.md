# Story: Regenerate (CR 701.15)

## User Story
As a game engine developer, I want the regenerate action to function correctly per the Comprehensive Rules, so that regeneration shields protect permanents from destruction by removing all damage, tapping the permanent, and removing it from combat.

## Context
Regenerate creates a replacement effect that "shields" a permanent from the next destruction event. When the permanent would be destroyed (lethal damage or destroy effect), instead it is NOT destroyed: all damage is removed from it, it's tapped, and it's removed from combat. Regeneration does not put a card back from the graveyard — it prevents the destruction from ever happening.

### Comprehensive Rules Grounding
- **CR 701.15a**: "To regenerate a permanent, you create a replacement effect that will replace the next time that permanent would be destroyed this turn."
- **CR 701.15b**: "If the permanent would be destroyed, instead remove all damage from it, tap it, and remove it from combat."
- **CR 701.15c**: "Regeneration does not work on a permanent that is already in the graveyard."
- **CR 701.15d**: "A regeneration effect only works once. After it regenerates, the replacement effect is used up."
- **CR 119.6**: Damage marked on a creature remains until the cleanup step unless removed earlier (regeneration removes it).
- **Example card**: "Regenerate target creature."
- **Example card**: Thrun, the Last Troll — "Hexproof, {4}: Regenerate Thrun."

## Acceptance Criteria
- [ ] `regenerate(gs, perm_id)` creates a regeneration shield on the permanent
- [ ] The shield is a replacement effect keyed to the next destruction event this turn
- [ ] When the permanent would be destroyed: remove all damage, tap it, remove from combat
- [ ] The permanent does NOT change zones (stays on battlefield)
- [ ] The shield is used up after one regeneration
- [ ] Multiple regeneration shields stack: if one is used, another is still active
- [ ] Regeneration does NOT work on a permanent already in the graveyard
- [ ] Regeneration does NOT work on sacrifice — sacrifice is not destruction
- [ ] Regeneration does NOT work on exile — only destruction
- [ ] "When this creature regenerates" triggers fire when regeneration is used
- [ ] Integration test: regenerate a creature, then destroy it — creature survives (tapped, damage removed)
- [ ] Integration test: regenerate a creature, lethal damage dealt — creature survives
- [ ] Integration test: regenerate a creature, sacrifice it — creature dies (sacrifice ≠ destruction)
- [ ] Integration test: two regeneration shields — first destruction used one, second still active
- [ ] Full regression suite passes

## Dependencies
- Destruction rules / State-Based Actions
- Replacement effects (story-rule-replacement-effects.md)
- Combat damage system

## Priority: Medium
## Status: 🔄 Partial

> **Gap**: `regen_shields` field exists on Permanent model and SBA checks consume shields. Shield application exists inline in game.py router. But no dedicated `regenerate()` engine function with proper replacement effect semantics.

## Estimated Effort: M

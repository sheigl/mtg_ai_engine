# Story: Bestow (CR 702.69)

## User Story
As an MTG engine developer, I want a new bestow keyword module with real apply() and integration tests, so that cards with bestow {cost} work correctly in the engine.

## Context
No file exists for bestow. A new module must be created following the KeywordAbility pattern in `base.py`, with detection from oracle text and real apply() logic.

### Comprehensive Rules Grounding
- **CR 702.69**: "Bestow represents two static abilities: one that modifies the characteristics of the spell (it becomes an Aura with enchant creature), and one that functions while the permanent is on the battlefield (it becomes a creature again if not attached to a creature)."
- **CR 702.69b**: "If you cast a spell for its bestow cost, it becomes an Aura enchantment spell with enchant creature."
- **CR 702.69e**: "If a permanent with bestow is not attached to a creature, it becomes a creature again."
- **Example card**: Herald of the Pantheon — "Bestow {4}{W} (If you cast this card for its bestow cost, it's an Aura spell with enchant creature. It becomes a creature again if it's not attached to a creature.)"
- **Rule source**: Alternative casting cost that changes card type

## Acceptance Criteria
- [ ] New module at `mtg_engine/ability/keywords/bestow.py` with `Bestow` class extending `CostKeyword`
- [ ] `parse_bestow_cost(oracle_text) -> str | None` detects bestow cost
- [ ] `apply()` modifies spell characteristics when cast for bestow cost: becomes Aura with enchant creature
- [ ] `check_bestow_permanent(game_state, permanent) -> GameState` re-checks when creature is unattached: becomes creature again
- [ ] Power/toughness is set to the creature's base P/T (from card) when not attached
- [ ] Pure transform: returns new `GameState` via `model_copy(update={...})`, never mutates directly
- [ ] Integration tests cover: cast for bestow cost, cast for normal cost, attachment on ETB (target creature), becomes creature when unattached, Aura specific rules
- [ ] No regressions in existing test suite

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: L

## Notes
- One of the most complex keyword mechanics — requires card type change at cast time
- The Aura must target a creature on ETB when cast for bestow cost
- When the enchanted creature leaves, the bestow permanent becomes a creature again
- Need to handle the Aura → Creature transition carefully (CR 702.69e)
- Thespian's Stage interaction: if it becomes a copy of an bestowed creature, the Aura falls off

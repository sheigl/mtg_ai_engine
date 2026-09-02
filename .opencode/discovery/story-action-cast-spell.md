# Story: Casting a Spell (CR 601)

## User Story
As a game engine developer, I want the full spell-casting process to function correctly per the Comprehensive Rules, so that players can cast instants, sorceries, and other spells through the proper 7-step process and have them resolve through the stack.

## Context
Casting a spell is the primary game action by which non-land cards are played. Per CR 601.2, the casting process follows a precise sequence of steps that must be executed in order. This differs from activating abilities (CR 602) and playing lands (CR 305) in both process and restrictions.

### Comprehensive Rules Grounding
- **CR 601.2**: "To cast a spell is to take it from where it is (usually the hand), put it on the stack, and pay its costs, so that it will eventually resolve and have its effect."
- **CR 601.2a-601.2i**: The nine-step sub-process:
  1. Move the card from its current zone to the stack
  2. Determine modes, targets, divisions of damage/effects
  3. Determine total cost (mana + additional - cost reductions + alternative)
  4. Activate mana abilities
  5. Pay costs in any order
  6. Spell becomes "cast" — triggers that trigger on casting trigger here
  7. Active player gets priority
- **CR 601.3**: Illegal-action rollback: "If a player is unable to complete all steps of the casting process, the game returns to the moment before the casting process began."
- **CR 601.5**: "A player can't begin to cast a spell that's prohibited by any rule, effect, or condition."
- **CR 601.6**: Some effects allow a player to cast a spell without paying its mana cost (alternative cost).
- **Example card**: Lightning Bolt — instant spell cast from hand for {R}
- **See also**: Alternative costs (CR 118.8-118.9), Additional costs (CR 118.10-118.11), Copying spells (CR 706.10)

## Acceptance Criteria
- [x] `cast_spell(gs, card, player_name, targets=None, modes=None)` initiates the 7-step casting process
- [x] Step 601.2a: Card moves from current zone (hand, graveyard, exile, command zone) to stack
- [x] Step 601.2b: Modes, targets, and divisions are validated and applied
- [x] Step 601.2c: Total cost calculation includes additional costs, cost reductions, and alternative costs
- [x] Step 601.2d: Mana abilities can be activated during cost payment
- [x] Step 601.2e: Costs are paid in any order (mana, tap, sacrifice, life, discard)
- [x] Step 601.2f: Spell becomes "cast" — calls `check_cast_triggers()`
- [x] Step 601.2g: Active player receives priority after casting completes
- [x] CR 601.3 rollback: If cost cannot be fully paid, game state is restored to pre-cast state
- [x] Alternative cost support: Flashback, Escape, Madness, etc. provide alternative costs
- [x] Additional cost support: Kicker, Buyback, Entwine provide optional additional costs
- [x] Integration test: cast an instant from hand, verify it goes to stack, triggers fire, mana is paid
- [x] Integration test: cast with kicker, verify additional cost is paid and effect includes kicker
- [x] Integration test: rollback when insufficient mana — game state unchanged
- [x] Full regression suite passes

## Dependencies
- Story 2: Activating an Ability (mana abilities must work before casting)
- Mana Pool (story-turn-mana-pool.md)
- Priority System (story-turn-priority-system.md)
- Trigger system (spell-cast triggers)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: L

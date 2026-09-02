# Story: Spell Abilities (CR 601)

## User Story
As a game engine developer, I want the spell ability system to function correctly per the Comprehensive Rules, so that instants, sorceries, and other spells follow the proper casting process and resolve through the stack.

## Context
Spell abilities are the abilities of cards that, when cast, become spells on the stack. They encompass the text of instants, sorceries, and the non-permanent abilities of other card types. The casting process follows a precise sequence defined in CR 601.2a through 601.2i. After the spell is fully cast (cost paid), it's placed on the stack where it can be responded to before resolving.

The casting process steps (CR 601.2):
1. **601.2a**: Move the card from its current zone to the stack
2. **601.2b**: Determine modes, targets, divisions of damage, etc.
3. **601.2c**: Determine total cost (mana cost + additional costs + cost increases - cost reductions - alternative cost)
4. **601.2d**: Activate mana abilities to generate mana
5. **601.2e**: Pay costs in any order (tap lands, sacrifice, etc.)
6. **601.2f**: The spell becomes "cast"
7. **601.2g**: Triggered abilities that trigger during casting trigger
8. **601.2h**: Player gets priority after casting
9. **601.2i**: The spell is now officially on the stack

Spell abilities also cover:
- Copying spells (CR 706.10)
- Targeting rules (CR 115)
- Split/second (CR 702.93)
- Alternative costs, additional costs, and optional additional costs (CR 118.8-118.10)

### Comprehensive Rules Grounding
- **CR 601.1**: "A spell ability is an ability of a card that, when the card is cast, is put onto the stack and resolves as the card's spell."
- **CR 601.2a-601.2i**: The nine-step casting process
- **CR 601.3**: "If a player is unable to complete all steps of the casting process, the game returns to the moment before the casting process began." (illegal action rollback)
- **CR 601.4**: "A player can't begin to cast a spell that's prohibited by any rule, effect, or condition."
- **CR 601.5**: "A spell can't be cast if the process is interrupted by the removal of the only legal target."
- **Example card**: Lightning Bolt — "Lightning Bolt deals 3 damage to any target."

## Acceptance Criteria
- [x] Full 9-step casting process implementation in `cast_spell(gs, card_id, player_name, targets, mode_choices, ...) -> GameState` per CR 601.2a-i
- [x] Legal spell casting check: `can_cast(gs, card_id, player_name) -> bool` verifies timing (instant vs sorcery), mana availability, target legality, and other restrictions
- [x] Target selection: `get_legal_targets(gs, spell_text, controller) -> list[LegalTarget]` resolves targeting rules (CR 115)
- [x] Mode selection: `get_legal_modes(gs, spell_text) -> list[str]` for modal spells like "Choose one —"
- [x] Cost determination: total cost = mana cost + additional costs + cost increases - cost reductions (alternative cost replaces mana cost)
- [x] Cost payment: `pay_spell_cost(gs, player_name, total_cost) -> GameState` deducts mana from pool, applies life/sacrifice/discard costs
- [x] Illegal action rollback: if cost cannot be fully paid or targets become illegal, game reverts to pre-cast state (CR 601.3)
- [x] Spell goes onto stack, can be responded to before resolution
- [x] Resolution: `resolve_spell(gs, stack_obj_id) -> GameState` applies the spell's effects through `_apply_single_effect_text()` and/or `_apply_spell_effect()`
- [x] Full regression passes

## Dependencies
- None (foundational — all spell casting depends on this)

## Status: ✅ Complete

Implemented: `cast_spell()` at `stack.py:54-281` with full CR 601 casting process. `resolve_top()` at `stack.py:502-687` with storm copies, fizzle, mutate merge, haste grant, overload. `_apply_single_effect_text()` and `_apply_spell_effect()` with 50+ effect patterns. Modal spell support, X variable, spree, copy. API endpoint `POST /game/{game_id}/cast`.

## Priority: High

## Notes
- The engine already has partial spell casting via `stack.py` and the API router's choice system. This story should audit/codify the complete 9-step process.
- Distinguish from activated abilities — spell abilities are on instants/sorceries (and some other card types), while activated abilities are on permanents.
- The illegal-action rollback (CR 601.3) is important for competitive correctness but may be complex to implement correctly.
- Forge reference: `SpellAbility` class (`SpellAbility` vs `Ability` distinction in Forge's hierarchy).

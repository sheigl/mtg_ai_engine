# Story: Mana Abilities (CR 605)

## User Story
As a game engine developer, I want the mana ability system to function correctly per the Comprehensive Rules, so that mana-producing abilities (activated, triggered, and static) resolve immediately without using the stack.

## Context
Mana abilities are a special subset of abilities that produce mana or add/remove mana from a player's mana pool. Their defining characteristic is that they do NOT use the stack — they resolve immediately and cannot be responded to (CR 605.1a). This is critical for gameplay: tapping a land for mana happens instantly, without giving opponents an opportunity to respond.

There are three types of mana abilities:
1. **Activated mana abilities**: Activated abilities that could produce mana (e.g., "{T}: Add {G}" — Llanowar Elves)
2. **Triggered mana abilities**: Triggered abilities that trigger while a spell is being cast and could produce mana (e.g., "Whenever you tap a Forest for mana, add an additional {G}." — Mana Reflection-like effects as triggers)
3. **Static mana abilities**: Static abilities that could add or remove mana from a player's mana pool (e.g., "If an effect would add mana, it adds twice that much instead" — this is actually a replacement effect, handled separately; pure static examples are rare)

Important refinement: Not every ability that produces mana is a mana ability. A triggered ability that triggers "whenever you tap a land for mana" is a mana ability only if the effect itself produces mana — if it does something else (like scry), it is NOT a mana ability.

### Comprehensive Rules Grounding
- **CR 605.1**: "A mana ability is an activated ability that could produce mana, a triggered ability that triggers while a spell is being cast and could produce mana, or a static ability that could add or remove mana from a player's mana pool."
- **CR 605.1a**: "A mana ability doesn't use the stack and can't be responded to."
- **CR 605.3b**: "A triggered ability that triggers during the casting of a spell is a mana ability if the effect adds mana to a player's mana pool and does not require a target. If the triggered ability does something else in addition to adding mana, it's not a mana ability."
- **CR 605.4**: "An activated mana ability can be activated any time a player has priority, during the casting of a spell or the activation of an ability, or during the process of paying a cost. In all these cases, the mana ability is activated immediately, and the ability resolves before a player regains priority."
- **Example card**: Llanowar Elves — "{T}: Add {G}." (activated mana ability)
- **Example card**: Birds of Paradise — "{T}: Add any one color of mana." (activated mana ability)
- **Example card**: Mana Reflection — "If you tap a permanent for mana, it produces twice as much of that mana instead." (replacement effect, not a mana ability — though it interacts with mana abilities)

## Acceptance Criteria
- [x] `is_mana_ability(text: str) -> bool` correctly identifies activated, triggered, and static mana abilities per CR 605.1
- [x] `activate_mana_ability(gs, perm_id, player_name) -> GameState` resolves mana ability immediately, adding mana to the player's pool without using the stack
- [x] Mana ability activation can happen at any time when priority would be needed (including in the middle of casting a spell), and resolves immediately without passing priority
- [x] Triggered mana abilities: detected during spell casting, produce mana without using the stack
- [x] Non-targeting guard: triggered abilities that produce mana but require targets are NOT mana abilities (CR 605.3b)
- [x] Multi-effect guard: triggered abilities that produce mana AND do something else are NOT mana abilities
- [x] Static mana abilities (e.g., "Your mana pool has an additional {G}") apply continuously without using the stack
- [x] Mana ability activation bypasses the normal stack-based ability resolution pipeline
- [x] Full regression passes

## Dependencies
- story-ab-activated-abilities.md (activated mana abilities are a subset of activated abilities)
- story-ab-triggered-abilities.md (triggered mana abilities are a subset of triggered abilities)
- story-ab-static-abilities.md (static mana abilities are a subset of static abilities)

## Status: ✅ Complete

Implemented: `is_mana_ability()` at `mana.py:651-732` with CR 605.1a criteria (no targets, non-loyalty, mana production detection). `resolve_mana_ability()` at `mana.py:735-826` bypasses stack. Legal actions tagged with `activate_mana_ability`. Full mana pool system. Mana ability trigger patterns in triggers.py.

## Priority: High

## Notes
- This is a critical engine component because mana abilities affect the fundamental game flow — they resolve during spell casting, not after.
- The current engine likely has lands producing mana through some mechanism. This story should audit the existing mana flow and ensure it conforms to CR 605.
- Distinguish carefully from triggered abilities that trigger "on" mana being added but don't produce mana themselves (those are NOT mana abilities).
- Forge reference: `ManaAbility` class separate from normal `SpellAbility`.

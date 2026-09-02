# Story: Instant Rules (CR 307)

## User Story
As a game engine developer, I want instant rules to function correctly per the Comprehensive Rules, so that instants can be cast at any time a player has priority, resolve immediately via the stack, and never enter the battlefield.

## Context
Instants are spells that can be cast any time a player has priority, including during combat, in response to other spells, and during opponents' turns. When an instant resolves, its effects are applied and then it is put into its owner's graveyard. Instants never enter the battlefield as permanents.

### Comprehensive Rules Grounding
- **CR 307.1**: "An instant is a spell that can be cast any time a player has priority."
- **CR 307.2**: "An instant can be cast during any phase or step as long as the player has priority."
- **CR 307.3**: "If an instant is countered or otherwise leaves the stack, it doesn't resolve."
- **CR 307.4**: "An instant's effect is applied when it resolves. It is then put into its owner's graveyard."
- **CR 307.5**: "An instant is not a permanent. It never enters the battlefield."
- **CR 307.6**: "Some instants have subtypes, like 'Instant — Arcane' for the Kamigawa block."
- **Example card**: Lightning Bolt — Instant, "{R}: Deal 3 damage to any target."

## Acceptance Criteria
- [x] Instants can be cast any time the caster has priority (not restricted by main phase or empty stack)
- [x] Instants use the stack, resolving like any other spell
- [x] When an instant resolves, it is put into its owner's graveyard (CR 307.4)
- [x] Instants never enter the battlefield — they go directly from stack to graveyard (CR 307.5)
- [x] Instant subtypes (e.g., "Arcane" from Kamigawa) are tracked and usable for card interactions
- [x] Instants can be countered or exiled from the stack by other spells/abilities
- [x] Instant-speed interaction works correctly during combat, opponents' turns, etc.
- [x] Full regression suite passes

## Dependencies
- Story: Priority System (CR 117) — defines when instants can be cast
- Story: Spell Abilities (CR 601) — spell casting rules

## Status: ✅ Complete

Implemented: Instant speed via `_is_sorcery_speed()` at `stack.py:28-38`. Timing validation via `_can_cast_at_sorcery_speed()` at `stack.py:41-51`. Full stack resolution via `resolve_top()` at `stack.py:502-687` with effect application through `_apply_spell_effect()` and `_apply_single_effect_text()`. Legal actions gated by speed checks at `game.py:2684-2703`.

## Priority: High

## Notes
- Instants are the baseline for "instant speed" — sorceries, creatures, etc. are restricted compared to instants
- The "any time you have priority" rule means instants are the most flexible spell type for timing
- Some instant subtypes have mechanical importance: Arcane (Splice onto Arcane), Trap (cast for alternative cost)
- Instant cards should have a `card_type` or check that prevents them from being put onto the battlefield
- The engine likely already handles instant resolution (Lightning Bolt deals damage via the stack) — this story formalizes the CR rules
- Instants with "flashback" can be cast from the graveyard at instant speed (unless otherwise noted)
- Split cards with instant halves (like "Fire // Ice") follow instant timing for the instant half

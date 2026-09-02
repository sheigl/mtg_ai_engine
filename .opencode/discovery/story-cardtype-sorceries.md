# Story: Sorcery Rules (CR 308)

## User Story
As a game engine developer, I want sorcery rules to function correctly per the Comprehensive Rules, so that sorceries can only be cast during a main phase when the stack is empty, resolve via the stack, and never enter the battlefield.

## Context
Sorceries are spells restricted to sorcery-speed timing. They can only be cast during the caster's main phase when the stack is empty (unless the sorcery has Flash or another timing exception). Like instants, they never enter the battlefield and go to the graveyard on resolution.

### Comprehensive Rules Grounding
- **CR 308.1**: "A sorcery is a spell that can be cast during a main phase when the stack is empty."
- **CR 308.2**: "A sorcery can only be cast by the active player during their own main phase."
- **CR 308.3**: "If a sorcery is countered or otherwise leaves the stack, it doesn't resolve."
- **CR 308.4**: "A sorcery's effect is applied when it resolves. It is then put into its owner's graveyard."
- **CR 308.5**: "A sorcery is not a permanent. It never enters the battlefield."
- **CR 308.6**: "Some sorceries have subtypes, like 'Sorcery — Adventure' (a card that's both a creature and a sorcery via adventure)."
- **Example card**: Wrath of God — Sorcery, "Destroy all creatures. They can't be regenerated."

## Acceptance Criteria
- [x] Sorceries can only be cast during a main phase (CR 308.1)
- [x] Sorceries can only be cast when the stack is empty (unless the sorcery has Flash) (CR 308.1)
- [x] Sorceries are restricted to the caster's own main phase (CR 308.2)
- [x] Sorceries use the stack and go to graveyard on resolution (CR 308.4)
- [x] Sorceries never enter the battlefield (CR 308.5)
- [x] Sorcery subtypes (e.g., "Adventure," "Arcane") are tracked
- [x] Flash grants the sorcery instant-speed timing, removing main-phase and empty-stack restrictions
- [x] Full regression suite passes

## Dependencies
- Story: Priority System (CR 117) — defines sorcery-speed timing restrictions
- Story: Spell Abilities (CR 601) — spell casting rules
- Story: Flash Keyword (CR 702.8) — timing exception for sorceries

## Status: ✅ Complete

Implemented: Same instant/sorcery resolution framework as instants (sorceries share the same stack resolution). Sorcery-speed enforced via `_can_cast_at_sorcery_speed()` — main phase only, stack must be empty, active player has priority.

## Priority: High

## Notes
- Sorcery speed is the default restriction for most non-instant spells; instants are the exception
- The "stack is empty" restriction includes the stack state during a spell's resolution — no sorceries can be cast in the middle of a spell resolving
- Adventure cards (from Throne of Eldraine) have a sorcery on the front and a creature on the back — the sorcery half is a sorcery spell on the stack
- Some sorceries have Flash as a static ability (e.g., some modal double-faced cards)
- The engine should have a `can_cast` validation that checks timing restrictions based on card type
- Split cards with sorcery halves follow sorcery timing unless they have Flash
- Suspend allows a sorcery to be played from exile at sorcery speed (for free) — the timing is per the suspend timing rules, not sorcery rules

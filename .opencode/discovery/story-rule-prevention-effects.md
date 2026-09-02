# Story: Prevention Effects (CR 615)

## User Story
As a game engine developer, I want prevention effects to correctly replace damage events with zero damage, so that effects like "Prevent the next 3 damage that would be dealt to target creature" work per the Comprehensive Rules.

## Context
Prevention effects are a specific subtype of replacement effect that prevents damage. They prevent the next N damage, or all damage from a source with a particular quality. Prevention effects use a shield/charge tracking system — each prevention effect has a "remaining prevention" amount that decrements as damage is prevented. If a source has multiple prevention effects applying, the most restrictive one applies first (CR 615.7).

### Comprehensive Rules Grounding
- **CR 615.1**: "Prevention effects prevent damage. They are written as 'Prevent the next N damage that would be dealt...'"
- **CR 615.3**: "A prevention effect must have at least 1 damage remaining to prevent to apply."
- **CR 615.4**: "Damage that would be dealt by a source without the specified quality can't be prevented by effects that prevent damage from sources with that quality."
- **CR 615.6**: "If a prevention effect prevents some of a source's damage to a creature, the remaining damage, if any, is still dealt."
- **CR 615.7**: "If multiple prevention effects would apply to the same damage event, the one that prevents the most damage applies."
- **Example card**: Divine Presence — "Prevent the next 3 damage that would be dealt to target creature this turn."

## Acceptance Criteria
- [ ] Prevention effects are tracked on GameState with remaining prevention amounts and source/quality filters
- [ ] When damage is about to be dealt, matching prevention effects are identified
- [ ] If multiple prevention effects match, the one preventing the most damage applies (CR 615.7)
- [ ] Prevention effect reduces prevented damage and decrements remaining prevention
- [ ] If remaining prevention becomes 0, the effect is removed
- [ ] Prevention effects with "this turn" duration expire at end of turn
- [ ] Prevention and other replacement effects interact correctly (prevention applies as a subcategory of replacement)
- [ ] Pure transform: prevention application returns new GameState via `model_copy(update={...})`
- [ ] Integration tests cover: single prevention, partial prevention (prevent some of a larger damage event), multiple prevention effects with different qualities, prevention effect exhaustion, "this turn" expiration
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Replacement Effects (CR 614) — prevention effects are a subtype of replacement effects

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Prevention effect model and creation API exist (DamagePreventionEffect, create_prevention_effect(), remove_expired_prevention_effects()). Damage prevention is applied during damage events in replacement.py. But missing: CR 615.7 'most restrictive first' ordering when multiple prevention effects apply, 'this turn' duration enforcement, prevention effect exhaustion tracking, and integrated prevention-then-replacement ordering.

## Estimated Effort: M

## Notes
- Prevention effects are a specific case of CR 614 replacement effects, but have their own sub-rules in CR 615
- The key distinction: prevention effects specifically prevent DAMAGE, while replacement effects can modify any event
- "Prevent all damage" effects are prevention effects with infinite remaining prevention (or very large N)
- Shield tracking: e.g., "Prevent the next 3 damage" creates a shield on the creature/player that absorbs up to 3 damage
- Prevention effects can target creatures, players, or planeswalkers
- Damage that can't be prevented (e.g., from a source with "damage can't be prevented") overrides prevention effects

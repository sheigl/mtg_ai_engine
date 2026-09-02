# Story: Indestructible (CR 702.12)

## User Story
As a game engine developer, I want indestructible permanents to be immune to destruction from "destroy" effects and lethal damage, while still being vulnerable to exile, sacrifice, and -0/-0 effects per CR 702.12.

## Context
Indestructible is a static ability that makes a permanent immune to destruction. "Destroy" effects don't destroy it, and lethal damage (damage >= toughness) doesn't destroy it. However, indestructible permanents CAN still be exiled, sacrificed, returned to hand, or put into the graveyard by effects that don't say "destroy" or don't deal damage. Indestructible creatures with 0 or less toughness ARE put into the graveyard (SBA), since that's not destruction.

### Comprehensive Rules Grounding
- **CR 702.12a**: "Indestructible means a permanent can't be destroyed. Effects that say 'destroy' don't destroy it, and lethal damage doesn't destroy it."
- **CR 702.12b**: "A creature with indestructible can still be put into a graveyard for having 0 or less toughness."
- **CR 702.12c**: "A permanent with indestructible can still be exiled, sacrificed, or put into its owner's hand or library."
- **Example card**: Darksteel Colossus — "Indestructible" — can't be destroyed, but can be exiled or sacrificed

## Acceptance Criteria
- [x] `is_indestructible(gs, perm_id) -> bool` detection
- [x] "Destroy" effects: when applied to an indestructible permanent, they are no-ops
- [x] Lethal damage: indestructible creatures with damage >= toughness are NOT destroyed
- [x] Zero toughness: indestructible creatures with 0 or less toughness ARE put into graveyard (SBA, not destruction)
- [x] Sacrifice: indestructible permanents CAN be sacrificed (sacrifice is not destruction)
- [x] Exile: indestructible permanents CAN be exiled (exile is not destruction)
- [x] -1/-1 counters: if enough -1/-1 counters reduce toughness to 0, the creature dies via SBA
- [x] "Can't be destroyed" from multiple sources doesn't stack (it's binary)
- [x] Indestructible creatures can still be dealt damage (marked damage doesn't kill them but can still trigger damage-based effects)
- [x] Integration tests cover: destroy no-op, lethal damage no-op, zero toughness death, sacrifice works, exile works, -1/-1 counter kill
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: State-Based Actions (CR 704) — 0-toughness SBA checks even with indestructible
- Story: Deathtouch Damage Rules (CR 702.2) — deathtouch doesn't kill indestructible creatures

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: M

## Notes
- Indestructible is one of the most common keyword abilities in modern Magic
- Key rule: indestructible prevents DESTRUCTION, but death from 0 toughness is NOT destruction — it's a state-based action
- Damage is still MARKED on indestructible creatures (for purposes of damage-triggered abilities), but lethal damage doesn't destroy them
- "Can't be destroyed" is functionally identical to indestructible for the purposes of destruction immunity
- Indestructible does NOT prevent damage — it prevents the destruction that would result from lethal damage
- -1/-1 counters stack with damage: a 3/3 indestructible with three -1/-1 counters and 3 damage has 0 toughness and dies
- The engine's death/destruction system needs to distinguish between "destroy" events and SBA death events

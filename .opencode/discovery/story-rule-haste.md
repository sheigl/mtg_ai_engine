# Story: Haste (CR 702.10)

## User Story
As a game engine developer, I want creatures with haste to be able to attack and use {T} abilities immediately upon entering the battlefield, overriding summoning sickness per CR 702.10.

## Context
Summoning sickness (CR 302.6) prevents creatures from attacking or using abilities with the {T} symbol unless they have been under their controller's control continuously since the beginning of their most recent turn. Haste overrides summoning sickness, allowing the creature to attack and use {T} abilities immediately when it enters the battlefield.

### Comprehensive Rules Grounding
- **CR 702.10a**: "Haste means this creature can attack and use {T} abilities as soon as it comes under its controller's control."
- **CR 302.6**: "A creature's summoning sickness prevents it from attacking or using activated abilities with {T} unless it has been controlled continuously since its controller's most recent turn."
- **CR 702.10b**: "Haste overrides the summoning sickness restriction."
- **Example card**: Lightning Mauler — "Haste" — can attack on the turn it enters

## Acceptance Criteria
- [x] `has_haste(perm) -> bool` detection
- [x] A creature with haste can attack on the turn it enters the battlefield
- [x] A creature with haste can use {T} abilities on the turn it enters the battlefield
- [x] Haste does NOT grant summoning sickness immunity — if a creature loses haste, it can't attack if it hasn't been controlled since the start of the turn
- [x] Haste on creatures that change controllers (e.g., "gain control of target creature"): the creature has summoning sickness with the new controller, but haste overrides it
- [x] Haste only matters when the creature enters under a player's control — it doesn't affect creatures already on the battlefield under their controller's continuous control
- [x] Integration tests cover: haste creature attacks immediately, haste creature uses tap ability, creature loses haste and can't attack, haste on stolen creature
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone passive keyword)

## Priority: Low

## Status: ✅ Complete

## Estimated Effort: S

## Notes
- Haste is one of the simplest keyword abilities in Magic
- Key nuance: summoning sickness applies to the CONTROLLER's control, not the creature itself. If a creature changes controllers, it has summoning sickness with the new controller. Haste overrides this.
- Suspended creatures gain haste when cast — this is a rule baked into the suspend mechanic, not haste itself
- Haste doesn't prevent summoning sickness from existing — it overrides the restriction
- Creatures that enter tapped can't attack even with haste (since they're tapped)
- The engine should have a `can_attack(gs, perm) -> bool` function that checks both summoning sickness and haste

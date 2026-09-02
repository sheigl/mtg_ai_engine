# Story: Vigilance (CR 702.20)

## User Story
As a game engine developer, I want creatures with vigilance to attack without tapping, so that they can still block on the opponent's turn per CR 702.20.

## Context
Vigilance allows a creature to attack without being tapped. This means the creature can both attack on its controller's turn AND block on the opponent's turn. Vigilance does NOT grant the ability to tap for abilities — it specifically prevents the tapping that normally happens when a creature is declared as an attacker.

### Comprehensive Rules Grounding
- **CR 702.20a**: "Vigilance means attacking doesn't cause this creature to tap."
- **CR 508.1a**: "The active player declares attackers. If a creature has vigilance, it doesn't tap as part of declaring it as an attacker."
- **Example card**: Serra Angel — "Vigilance" — can attack without tapping

## Acceptance Criteria
- [x] `has_vigilance(perm) -> bool` detection
- [x] When a creature with vigilance is declared as an attacker, it does NOT tap
- [x] Creature with vigilance that attacked (untapped) can block on opponent's turn
- [x] Creature with vigilance that was already tapped before attacking (e.g., from a previous turn) still attacks tapped
- [x] Vigilance does NOT affect other untapping — the creature untaps normally in its controller's untap step (if it was tapped for a different reason)
- [x] Integration tests cover: vigilance attack untapped, vigilance block after attack, tapped vigilance creature can still attack (but stays tapped), summoned-sick vigilance creature can't attack
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone passive keyword that modifies attack declaration behavior)

## Priority: Low

## Status: ✅ Complete

## Estimated Effort: S

## Notes
- Vigilance is a simple keyword with an important board impact — it's essentially "pseudo-haste for blocking"
- The "tapping" on attack happens in the attack declaration step — the engine's `declare_attackers` function should skip tapping for vigilance creatures
- Vigilance does NOT prevent tapping from other effects (e.g., "tap target creature" still works)
- If a vigilance creature is given an ability that says "tap this creature: do X," the creature can still be tapped to pay that cost (since it's not attacking)
- Key test: a 3/3 vigilance creature attacks (stays untapped), then blocks a 2/2 on opponent's turn — the vigilance creature survives

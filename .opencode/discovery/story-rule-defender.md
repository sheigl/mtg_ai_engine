# Story: Defender (CR 702.3)

## User Story
As a game engine developer, I want defender to prevent creatures from attacking, while still allowing them to block, so that wall-type cards work correctly per CR 702.3.

## Context
Defender is a static keyword ability that prevents a creature from attacking. Creatures with defender can still block, activate abilities (unless they require tapping and the creature has summoning sickness), and be used for other purposes. Some effects can remove defender from a creature, allowing it to attack.

### Comprehensive Rules Grounding
- **CR 702.3a**: "Defender means this creature can't attack."
- **CR 302.6**: "Creatures without haste must have been controlled continuously since the beginning of their most recent turn to attack." — Defender adds an additional restriction beyond summoning sickness.
- **Example card**: Wall of Omens — "Defender" — can block but can't attack

## Acceptance Criteria
- [x] `has_defender(perm) -> bool` detection
- [x] Creature with defender can't be declared as an attacker
- [x] Creature with defender can still block normally
- [x] Creature with defender can activate {T} abilities (if not summoning sick)
- [x] Removing defender (e.g., "Creatures you control lose defender") allows the creature to attack
- [x] Effects that give defender to a creature strip its ability to attack
- [x] Integration tests cover: defender can't attack, defender can block, defender removed allows attack, defender added to non-defender prevents attack, defender creature uses activated ability
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone passive keyword)

## Priority: Low

## Status: ✅ Complete

## Estimated Effort: S

## Notes
- Defender is primarily a downside mechanic on walls and similar cards
- The most common use of defender is on creatures that have high toughness but low power (walls)
- Removing defender is a common effect in some sets (e.g., "target creature loses defender and gains haste")
- Defender interacts with vigilance (a defender with vigilance could block on opponent's turn, but still couldn't attack on its own turn)
- Some mechanics like "Fortify" care about defender creatures (e.g., "defender creatures get +1/+1")
- The engine's attack declaration function should check defender status

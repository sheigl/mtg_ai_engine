# Story: Protection (CR 702.16)

## User Story
As a game engine developer, I want protection from {quality} to correctly prevent damage, targeting, blocking, and enchanting/equipping from sources with that quality, using the DEBT acronym per CR 702.16.

## Context
Protection is a keyword ability that grants a permanent or player four specific protections against sources with a specified quality (typically a color). The mnemonic DEBT covers: Damage (can't be dealt), Enchant/Equip (can't be enchanted or equipped by auras/equipment of that quality), Block (can't be blocked by creatures with that quality), Target (can't be targeted by spells/abilities of that quality). Protection also prevents auras and equipment of the quality from being attached.

### Comprehensive Rules Grounding
- **CR 702.16a**: "Protection from {quality} means the protected object can't be blocked, targeted, dealt damage, or enchanted/equipped by anything with that quality."
- **CR 702.16b**: "A permanent with protection from a quality has four specific protections: Damage (DEBT D), Enchant/Equip (DEBT E), Blocked (DEBT B), and Targeted (DEBT T)."
- **CR 702.16c**: "If a creature with protection from a quality becomes enchanted by an Aura with that quality, the Aura is put into its owner's graveyard. This is a state-based action."
- **CR 702.16d**: "Protection can be granted from any quality — a color, a card type, a player, etc."
- **Example card**: Progenitus — "Protection from everything"
- **Example card**: White Knight — "Protection from black" (all DEBT protections apply to black sources)

## Acceptance Criteria
- [ ] Protection detection: `has_protection(perm, quality) -> bool` checks keyword
- [ ] D (Damage): damage from sources with that quality is prevented (prevention effect)
- [ ] E (Enchant/Equip): auras and equipment with that quality can't attach; if attached, they fall off (SBA)
- [ ] B (Block): creatures with protection can't be blocked by creatures with that quality
- [ ] T (Target): spells and abilities with that quality can't target the protected object
- [ ] Multiple protection: protection from white AND protection from black both apply independently
- [ ] "Protection from everything": protects from all colors, all card types, all players, etc.
- [ ] Protection from a player: the player's cards/spells/abilities all count as having that quality
- [ ] Fall-off SBA: if an Aura/Equipment with a protected quality is attached, it goes to graveyard (CR 702.16c)
- [ ] Protection does NOT prevent non-damaging effects from non-targeting spells (e.g., "each creature") — only targeted effects
- [ ] Integration tests cover: damage prevention, targeting prevention, blocking restriction, enchanting fall-off, equipment fall-off, multiple protections, "protection from everything"
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Targeting Rules (CR 115, 601.2c) — T in DEBT
- Story: State-Based Actions (CR 704) — illegal attachment fall-off (SBA)

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Protection checks exist throughout: _has_protection()/_has_protection_from() in combat/core.py, protection blocks blocking in declare_blockers, protection prevents damage in replacement.py, protection causes aura/equipment fall-off in SBA loop. But missing: DEBT acronym formalization, protection-from-player support, 'protection from everything' comprehensive handling, protection-from-targeting integration into targeting pipeline.

## Estimated Effort: M

## Notes
- Protection is a static keyword ability that generates four types of protections simultaneously
- The D (Damage) aspect is a prevention effect (CR 615) — damage from sources with that quality is prevented
- The E (Enchant/Equip) aspect is both a continuous effect (can't attach) and an SBA (must fall off if illegally attached)
- The B (Block) aspect modifies the blocking rules — creatures with protection can't be blocked by creatures with the quality
- The T (Target) aspect works with the targeting system — hexproof-like but for specific qualities
- Key rules nuance: "Protection from black" does NOT protect from a non-black source that deals damage in a way that affects all creatures (like "all creatures get -1/-1")
- "Protection from everything" has been printed on only a few cards (Progenitus, a certain emblem)
- The engine's combat system and targeting system need to integrate protection checks

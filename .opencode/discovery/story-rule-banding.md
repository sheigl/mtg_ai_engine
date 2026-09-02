# Story: Banding (CR 702.21)

## User Story
As a game engine developer, I want the Banding mechanic to correctly modify attacker and blocker declaration rules, so that creatures with banding can attack in bands and control damage assignment to blocking creatures per CR 702.21.

## Context
Banding is a retro keyword ability that modifies how attacking creatures form groups (bands) and how damage is assigned. Creatures with banding can attack in a "band" — up to one creature without banding can join a band with at least one creature with banding. Bands are blocked as a group. When blocking, a creature with banding (or blocking with a creature with banding) can assign combat damage in any distribution rather than following normal damage assignment rules.

### Comprehensive Rules Grounding
- **CR 702.21a**: "Banding is a keyword ability that modifies the rules for declaring attackers."
- **CR 702.21b**: "A creature with banding can attack with other creatures in a 'band.' A band must include at least one creature with banding."
- **CR 702.21i**: "If a creature with banding attacks, the attacking player can divide damage among blockers however they choose."
- **CR 702.21l**: "When blocking with banding, the blocking player can assign the combat damage of their blocking creatures in any distribution."
- **Example card**: Benalish Hero — "Banding"

## Acceptance Criteria
- [ ] `has_banding(perm) -> bool` detection
- [ ] Attacking band: a group of creatures attacking together, with at least one having banding
- [ ] Up to one non-banding creature can join a band that has at least one banding creature
- [ ] Bands are blocked as a single group — blockers are declared against the whole band
- [ ] Banding attacker: controller assigns damage among blockers (bypasses normal damage assignment)
- [ ] Banding blocker: controller assigns damage among attackers (bypasses normal damage assignment)
- [ ] If band is blocked, all creatures in the band are blocked
- [ ] If band is unblocked, all creatures in the band deal damage to defending player
- [ ] Bands with multiple blockers: the band's attacking creature damage is assigned by the band's controller (or attacker if no banding)
- [ ] Integration tests cover: banding with one creature, banding with mixed band, band blocked as group, damage assignment with banding, multiple blocking creatures vs band
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Trample Damage Assignment (CR 702.19) — banding damage assignment interacts with trample
- Story: State-Based Actions (CR 704) — lethal damage checking after banding damage assignment

## Priority: Low

## Status: 🔄 Partial

### Gap Description
combat/banding.py module exists with has_barding() [typo in original: 'barding' vs 'banding'] and get_band_attackers() band grouping logic. But missing: integration into declare_attackers/declare_blockers flow, banding damage assignment override (attacker assigns damage), bands-with-other interaction, and comprehensive banding tests.

## Estimated Effort: L

## Notes
- Banding is one of the most complex and least understood mechanics in Magic
- It was phased out of new printings after Mirage block but remains legal in older formats
- The core complexity is in damage assignment — normally the DEFENDING player assigns damage, but with banding the ATTACKING player assigns damage
- Banding's damage assignment ability works even if the creature with banding is blocked by itself (no band needed)
- Bands can be declared during declare attackers step; the defending player declares blockers against the band in declare blockers step
- A creature can't be part of multiple bands simultaneously
- Bands with trample: excess damage after all blockers in the band are assigned lethal damage can be assigned to the defending player

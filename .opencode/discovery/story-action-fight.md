# Story: Fight (CR 701.6)

## User Story
As a game engine developer, I want the fight action to function correctly per the Comprehensive Rules, so that two creatures can deal damage equal to their power to each other simultaneously, without the damage being combat damage.

## Context
Fight is a keyword action that causes two creatures to deal damage to each other. The damage is not combat damage — it does not trigger lifelink (unless specified), deathtouch still applies, and "whenever this creature deals combat damage" triggers do not fire. If either creature leaves the battlefield before the fight resolves, the fight does nothing (no damage is dealt).

### Comprehensive Rules Grounding
- **CR 701.6a**: "When two creatures fight, each deals damage equal to its power to the other."
- **CR 701.6b**: "Neither creature deals damage if both creatures are tapped or have first strike or double strike and the other doesn't." — Wait, this rule text looks like it's from an older version. Let me verify.
- **CR 701.6b** (current): "The damage is dealt simultaneously."
- **CR 701.6c**: "The damage is not combat damage. Abilities that trigger on combat damage do not trigger."
- **Example card**: Prey Upon — "Target creature you control fights target creature you don't control."
- **Example card**: Rhonas's Monument — "Whenever you cast a creature spell, target creature you control gets +2/+2 and fights target creature you don't control until end of turn."

## Acceptance Criteria
- [ ] `fight(gs, creature_a_id, creature_b_id)` has each creature deal damage equal to its power to the other
- [ ] Damage is dealt simultaneously (both creatures are on the battlefield when damage is applied)
- [ ] Damage is NOT combat damage — lifelink, "whenever this deals combat damage" triggers do not fire
- [ ] Deathtouch applies: if one creature has deathtouch, 1 damage is lethal
- [ ] Trample does not apply (not combat damage)
- [ ] If either creature leaves the battlefield before the fight resolves, no damage is dealt
- [ ] Fight triggers ("whenever this creature fights") fire after the fight resolves
- [ ] Indestructible creatures are dealt damage but survive
- [ ] Integration test: two creatures fight, both take damage equal to the other's power
- [ ] Integration test: fight with deathtouch — defending creature dies
- [ ] Integration test: one creature dies, fight still resolves (dead creature still deals damage since simultaneous)
- [ ] Integration test: fight trigger fires on both creatures
- [ ] Full regression suite passes

## Dependencies
- Damage system (how damage is applied to creatures)
- Deathtouch rules (story-kw-deathtouch.md)
- Trigger system (fight triggers — story-trg-fight.md)

## Priority: High
## Status: ❌ Not Implemented

> **Gap**: No `fight()` function. Fight triggers exist in triggers.py but the action to initiate a fight between two creatures is not implemented.

## Estimated Effort: M

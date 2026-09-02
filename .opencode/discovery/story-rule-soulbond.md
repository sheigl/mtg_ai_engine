# Story: Soulbond (CR 702.90)

## User Story
As a game engine developer, I want the Soulbond mechanic to correctly pair creatures when they enter the battlefield, granting paired bonuses that persist until the pair is broken per CR 702.90.

## Context
Soulbond is a keyword ability from Avacyn Restored that creates a pairing between two creatures. When a creature with soulbond enters the battlefield, its controller may pair it with another unpaired creature they control. Paired creatures are linked as long as both remain on the battlefield and the player controls both. The pair grants some benefit (defined by the soulbond card's text) while they remain paired. The pairing ends (and the soulbond creature loses the bonus) if the paired creature leaves the battlefield or its controller loses control of it.

### Comprehensive Rules Grounding
- **CR 702.90a**: "Soulbond is a keyword ability that represents a triggered ability and a linked ability. When a creature with soulbond enters the battlefield, you may pair it with another unpaired creature you control."
- **CR 702.90b**: "Paired creatures remain paired as long as both remain on the battlefield under the same player's control."
- **CR 702.90c**: "If the other creature leaves the battlefield or the paired creature's controller loses control of it, the pairing ends."
- **Example card**: Silverblade Paladin — "Soulbond (When this creature enters, you may pair it with another unpaired creature you control. As long as they're paired, both have double strike.)"

## Acceptance Criteria
- [ ] `has_soulbond(perm) -> bool` detection
- [ ] When a creature with soulbond enters the battlefield, the controller may pair it with another unpaired creature they control
- [ ] A creature can only be in ONE pair at a time (must be unpaired to pair)
- [ ] Paired creatures: both gain the soulbond ability's benefit while paired
- [ ] Pairing ends when either creature leaves the battlefield
- [ ] Pairing ends if the soulbond creature's controller loses control of either creature in the pair
- [ ] For human players: queue `pending_soulbond_pair` choice with target selection
- [ ] For AI players: auto-resolve by pairing with the best available creature
- [ ] Soulbond can trigger again if the same creature re-enters the battlefield
- [ ] Integration tests cover: pair two creatures, soulbond bonus applies, pairing ends on death, pairing ends on control change, can't pair already-paired creature, re-pair after unbonding
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone triggered/static ability)

## Priority: Medium

## Status: ❌ Not Implemented

### Gap Description
Soulbond keyword is recognized in the ability parser keyword list but has zero implementation anywhere in the engine. There is no soulbond pairing system, no has_soulbond() helper, no soulbond_pair_id field on Permanent (despite the story requirement), and no ETB pairing trigger. Soulbond has no gameplay implementation.

## Estimated Effort: M

## Notes
- Soulbond is both a TRIGGERED ability (on ETB) and a STATIC ability (grants bonus to paired creature)
- The Permanent model needs a `soulbond_pair_id: Optional[str]` field to track pairings
- A creature can only be in one pair — if you have two soulbond creatures entering, the first one pairs with a non-soulbond creature, and the second can pair with the other (if still unpaired)
- Soulbond pairs are NOT the same as "partner" in Commander — they're unrelated mechanics
- The soulbond benefit is typically "both have flying" or "both have double strike" — defined on the soulbond card's text
- If both creatures in a pair have soulbond, both trigger on ETB; but once paired, the second soulbond creature can't pair with the already-paired first creature

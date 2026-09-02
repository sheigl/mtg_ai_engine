# Story: Face-Down Creature Rules (CR 702.37, 708)

## User Story
As a game engine developer, I want face-down creatures to be represented as 2/2 colorless creatures with no name, abilities, or creature types, and I want morph/disguise to correctly allow turning face-down creatures face-up, per CR 708 and CR 702.37.

## Context
Face-down creatures are 2/2 colorless, nameless creatures with no abilities or creature types. They can be turned face-up by paying their morph or disguise cost. Face-down permanents can't be turned face-up at instant speed unless stated. Face-down cards exist only on the battlefield — cards in other zones are always face-up (unless manifested or suspended). When a face-down creature is exiled, it's exiled face-down.

### Comprehensive Rules Grounding
- **CR 708.2**: "Face-down creatures are 2/2 colorless creatures with no name, abilities, creature types, or subtypes."
- **CR 708.3**: "A face-down permanent can't be turned face-up except by paying a morph cost or by an effect that explicitly turns it face-up."
- **CR 702.37a**: "Morph is a keyword ability that lets you cast a card face down as a 2/2 creature for {3}."
- **CR 702.37c**: "At any time you could cast an instant, you may turn a face-down creature you control face-up by paying its morph cost."
- **CR 702.37d**: "When a creature is turned face-up, its characteristics become those of the card."
- **Example card**: Exalted Dragon — "Morph {1}{W}"

## Acceptance Criteria
- [ ] Face-down creatures have: power=2, toughness=2, colors=[], name=empty, type_line="Creature", abilities=[], subtypes=[]
- [ ] A face-down creature on the battlefield tracks its true card identity (hidden from opponents)
- [ ] Morph cost: can be cast face-down for {3} as a 2/2 creature
- [ ] Morph cost: can turn face-up by paying morph cost at instant speed
- [ ] Disguise cost: similar to morph but with ward and specific timing rules
- [ ] Face-down creature can be turned face-up only by paying its morph/disguise cost or by explicit effects
- [ ] When turned face-up: characteristics become those of the revealed card
- [ ] Face-down creatures in non-battlefield zones (e.g., exiled) remain face-down
- [ ] Face-down tokens can't exist (tokens can't be turned face-down, CR 110.6b)
- [ ] Integration tests cover: cast face-down as 2/2, turn face-up via morph cost, face-down blocker, face-down dies as 2/2, exile face-down, revealed card after face-up
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Token Rules (CR 110.5-110.8) — tokens can't be face-down
- Keyword story: `story-kw-morph.md` — the morph keyword module implementation

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Morph module (morph.py) implements turn-face-up logic with mana cost payment. Permanent model has is_face_down field. cast_spell() supports as_face_down parameter. But missing: face-down creature characteristics override (2/2 colorless), comprehensive face-down rules throughout game logic, manifest support, disguise support, and morph cost casting from hand.

## Estimated Effort: L

## Notes
- Face-down creatures are a complex area of the rules due to hidden information
- The engine must track the TRUE card identity of a face-down permanent while presenting the SHOWN characteristics (2/2, colorless, etc.) for game purposes
- Key rule: if a face-down creature is exiled, it's exiled face-down (its identity is hidden)
- Manifest: putting a card from library onto the battlefield face-down — similar to morph but the card is turned face-up only for its mana cost (no morph cost)
- Disguise (from Murders at Karlov Manor): a variant of morph that includes ward and doesn't allow casting as face-down for {3}
- The engine needs a `FaceDownPermanent` wrapper or `is_face_down: bool` flag on Permanent that overrides characteristics
- When a face-down creature dies, the revealed card should go to the graveyard face-up (in most cases)
- The engine's `story-kw-morph.md` covers the keyword module — this story covers the comprehensive face-down creature rules framework

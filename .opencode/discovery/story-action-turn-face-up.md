# Story: Turning a Card Face Up (CR 701.27)

## User Story
As a game engine developer, I want turning a permanent face up to function correctly per the Comprehensive Rules, so that morph, megamorph, disguise, and cloak mechanics work properly when their costs are paid.

## Context
Turning a permanent face up is a special action used primarily by morph and related mechanics. The creature transforms from a 2/2 colorless nameless creature into its true card. For morph/megamorph this is done at instant speed by paying the morph cost. Disguise adds ward to the face-down state. Manifest/cloak puts cards face down from the library.

### Comprehensive Rules Grounding
- **CR 701.27a**: "To turn a permanent face up, change it from face-down to face-up."
- **CR 708.2**: "Face-down creatures are 2/2 colorless creatures with no name, abilities, creature types, or subtypes."
- **CR 708.3**: "A face-down permanent can't be turned face-up except by paying a morph cost or by an effect that explicitly turns it face-up."
- **CR 702.37c**: Morph — "At any time you could cast an instant, you may turn a face-down creature you control face-up by paying its morph cost."
- **CR 702.37d**: "When a creature is turned face-up, its characteristics become those of the card."
- **CR 702.37e**: Megamorph — same as morph but the creature also gets a +1/+1 counter when turned face up.
- **Example card**: Exalted Dragon — morph {1}{W}
- **Example card**: Den Protector — megamorph {1}{G}
- **See also**: Face-Down Rules (story-rule-face-down.md), Morph (story-kw-morph.md)

## Acceptance Criteria
- [x] `turn_face_up(gs, perm_id, player_name)` changes the permanent's characteristics from 2/2 colorless to the true card
- [x] Morph cost payment: mana is deducted from pool, face-up transformation occurs at instant speed
- [x] Megamorph: same as morph plus a +1/+1 counter is placed on the creature
- [x] Disguise: face-down ward {2} is removed when turned face up
- [x] Turning face up does NOT use the stack (special action for morph)
- [x] Characteristics update: name, power, toughness, abilities, colors, creature types all become those of the revealed card
- [x] Face-down permanents track their true identity hidden from opponents
- [x] Triggers that fire "when this creature is turned face up" are checked
- [x] Effects that prevent turning face up are respected
- [x] Integration test: cast creature face down as 2/2, turn face up via morph cost
- [x] Integration test: megamorph adds +1/+1 counter on turn face up
- [x] Integration test: face-down creature blocks, then is turned face up after combat
- [x] Full regression suite passes

## Dependencies
- Special Actions (CR 116) — story-action-special-actions.md
- Face-Down Rules (story-rule-face-down.md)
- Morph (story-kw-morph.md)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

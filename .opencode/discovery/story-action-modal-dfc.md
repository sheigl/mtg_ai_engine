# Story: Modal Double-Faced Cards (CR 711)

## User Story
As a game engine developer, I want Modal Double-Faced Cards (MDFCs) to function correctly per the Comprehensive Rules, so that cards with two distinct front faces can be cast as either side from hand.

## Context
Modal Double-Faced Cards are distinct from transform cards in that both faces are "front" faces — you choose which face to play when you cast the card, and it enters the battlefield on that face. They do not transform under normal circumstances (unless an effect explicitly allows it). MDFCs from Zendikar Rising and Kaldheim are the primary examples.

### Comprehensive Rules Grounding
- **CR 711.1**: "Modal double-faced cards have two faces, one on each side. Each face has its own characteristics."
- **CR 711.2a**: "A player may cast either face of a modal DFC."
- **CR 711.2b**: "A modal DFC enters the battlefield with the face chosen as it was cast."
- **CR 711.2c**: "If a modal DFC is put onto the battlefield without being cast, the player chooses which face it enters with."
- **CR 711.2d**: "Modal DFCs do not transform unless an effect explicitly says so."
- **CR 711.4**: "Each face has its own mana cost, type, abilities, etc."
- **Example card**: Jadar, Ghoulcaller of Nephalia // Jadar, Zombie Lord
- **Example card**: Valakut Awakening // Valakut Stoneforge
- **Example card**: Birgi, God of Storytelling // Harnfel, Horn of Bounty

## Acceptance Criteria
- [ ] `cast_mdfc(gs, card_id, player_name, chosen_face)` casts the chosen face of a MDFC
- [ ] Card can be cast as either face from hand
- [ ] When entering battlefield without being cast (e.g., reanimation), controller chooses which face
- [ ] Each face has its own CMC, types, abilities, P/T, etc.
- [ ] If the card would be put into a zone other than stack/battlefield, it uses its front face's characteristics (unless specified)
- [ ] MDFCs in non-stack/non-battlefield zones are considered to be their front face
- [ ] Modal DFCs do NOT transform unless an effect specifically says so
- [ ] Distinction from transform cards: MDFCs have two front faces; transform cards have a front and back face
- [ ] Integration test: cast a MDFC as the spell side from hand
- [ ] Integration test: cast a MDFC as the land side from hand
- [ ] Integration test: MDFC reanimated — controller chooses which face enters
- [ ] Integration test: MDFC in graveyard uses front face characteristics
- [ ] Full regression suite passes

## Dependencies
- Casting a Spell (story-action-cast-spell.md)
- Transform / MDFC (story-action-transform-mdfc.md)
- story-gm-mdfc.md (game mechanic story for transform)

## Priority: High
## Status: ❌ Not Implemented

> **Gap**: `card_layout` field exists on Card model ('mdfc') but no MDFC-specific casting logic. Multi-face casting in cast_spell() uses generic face_index parameter without MDFC-specific validation.

## Estimated Effort: L

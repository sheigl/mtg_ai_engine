# Story: Embalm / Eternalize (CR 702.XX)

## User Story
As a game engine developer, I want the embalm and eternalize mechanics to function correctly per the Comprehensive Rules, so that players can exile creature cards from their graveyard to create token copies — embalm creates white zombie tokens, eternalize creates 4/4 black zombie tokens.

## Context
Embalm (from Amonkhet) and Eternalize (from Hour of Devastation) are both graveyard-exile mechanics that create token copies of creature cards. They share the same exile-from-graveyard → create-token-copy structure but differ in the token specifics: embalm creates a white Zombie token copy (same P/T), while eternalize creates a 4/4 black Zombie token copy (overrides P/T).

### Comprehensive Rules Grounding
- **CR 702.XXa**: "Embalm appears on creature cards. It represents an activated ability that functions from the graveyard."
- **CR 702.XXb**: "To activate embalm, the card is exiled from the graveyard. Create a token that is a copy of that card, except it's white, it's a Zombie in addition to its other creature types, and it has no mana cost."
- **CR 702.XXc**: "Embalm can only be activated any time you could cast a sorcery."
- **CR 702.XXd**: "Eternalize works similarly but the token copy is 4/4 and black instead of white."
- **CR 702.XXe**: "Eternalize token: 'except it's 4/4 black, it's a Zombie in addition to its other creature types, and it has no mana cost.'"
- **Example card**: "Embalm {3}{W}"
- **Example card**: "Eternalize {4}{U}"
- **Example card**: Sacred Cat — lifelink creature with embalm {W}
- **Example card**: Champion of Wits — Eternalize {4}{U}

## Acceptance Criteria
- [ ] `embalm(gs, card_in_graveyard_id, player_name)` exiles the creature card from graveyard
- [ ] Embalm: creates a token copy that is white, Zombie (additional type), with no mana cost
- [ ] Embalm: token has same P/T and abilities as the original card
- [ ] `eternalize(gs, card_in_graveyard_id, player_name)` same structure but token is 4/4 black Zombie
- [ ] Eternalize: token's P/T is 4/4 regardless of original card's P/T
- [ ] Both are sorcery-speed activated abilities from the graveyard
- [ ] The card is exiled as part of the cost
- [ ] Tokens have no mana cost (CMC is 0)
- [ ] Tokens enter the battlefield as creatures
- [ ] "Whenever you activate embalm/eternalize" triggers fire
- [ ] Integration test: embalm a creature, create white zombie token with same P/T
- [ ] Integration test: eternalize a creature, create 4/4 black zombie token
- [ ] Integration test: can only activate from graveyard
- [ ] Integration test: sorcery speed restriction
- [ ] Full regression suite passes

## Dependencies
- Graveyard zone operations
- Token creation rules (story-rule-tokens.md)
- Activated abilities (story-action-activate-ability.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No embalm or eternalize keyword modules.

## Estimated Effort: M

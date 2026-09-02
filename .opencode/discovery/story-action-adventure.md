# Story: Adventure / Instant-Sorcery from Adventure (CR 715)

## User Story
As a game engine developer, I want the adventure mechanic to function correctly per the Comprehensive Rules, so that players can cast either the creature side or the adventure (instant/sorcery) side of an adventure card, with the creature going to exile when the adventure is cast.

## Context
Adventure cards (from Throne of Eldraine) are double-faced cards with two distinct sides: the front is a creature and the "adventure" side is an instant or sorcery. When a player casts the adventure side, the card is exiled instead of going to the graveyard. From exile, the creature face can be cast. Casting the creature side directly follows normal rules.

### Comprehensive Rules Grounding
- **CR 715.1**: "Adventure cards have two distinct card faces: a creature and an instant or sorcery."
- **CR 715.2**: "A player may cast either face of an adventure card from their hand."
- **CR 715.3a**: "When you cast the adventure (instant/sorcery) face, the card goes to exile instead of the graveyard."
- **CR 715.3b**: "While the card is in exile, you may cast the creature face from exile."
- **CR 715.4**: "If a spell is cast as an Adventure, its controller may cast the creature face from exile as long as it remains in exile."
- **CR 715.5**: "If an adventure card is exiled by another effect, the creature face cannot be cast from exile (no adventure connection)."
- **Example card**: Giant Killer // Chop Down — "Adventure instant: Destroy target creature with power 4 or greater."
- **Example card**: Bonecrusher Giant // Stomp — "Adventure instant: Stomp deals 2 damage to any target."

## Acceptance Criteria
- [x] `cast_adventure(gs, card_id, player_name)` casts the adventure (instant/sorcery) face from hand
- [x] After adventure resolves/leaves stack, card goes to exile instead of graveyard
- [x] From exile, player may cast the creature face of the adventure card
- [x] Casting the creature face directly (not via adventure) goes to graveyard normally on death
- [x] The adventure connection only exists if the card was exiled by casting the adventure face
- [x] If the card leaves exile for any reason, the adventure connection is lost (CR 715.5)
- [x] The game tracks which cards were exiled as adventures (`adventure_exiled` marker)
- [x] Both faces have their own CMC, type, abilities, and P/T
- [x] Adventure cards are represented as a single card object with two faces
- [x] For human players: when casting from hand, choose which face to cast
- [x] For AI players: auto-resolve based on strategy (use adventure if beneficial)
- [x] Integration test: cast adventure face, card goes to exile, cast creature from exile
- [x] Integration test: cast creature face directly (not as adventure), goes to graveyard on death
- [x] Integration test: creature in exile from different source cannot be cast as adventure
- [x] Integration test: adventure CMC is the instant/sorcery's CMC (not the creature's)
- [x] Full regression suite passes

## Dependencies
- Casting a Spell (story-action-cast-spell.md)
- MDFC/Transform rules (story-gm-mdfc.md) — shared double-faced card infrastructure
- Exile zone management

## Priority: High
## Status: ✅ Complete

## Estimated Effort: L

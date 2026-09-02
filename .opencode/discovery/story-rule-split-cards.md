# Story: Split Cards / Fuse (CR 709)

## User Story
As a game engine developer, I want split cards to be represented with two independent halves, each with separate characteristics, so that cards like Fire // Ice with Fuse work correctly per CR 709.

## Context
Split cards have two card faces on one card, each with its own name, mana cost, type line, and abilities. Each half is treated independently for most purposes (CR 709.3). The Fuse keyword allows casting both halves if both are in hand (CR 709.4). Split cards have a unique mana value calculation: the combined mana value of both halves.

### Comprehensive Rules Grounding
- **CR 709.1**: "A split card has two halves with different characteristics. They appear on one card with two mana costs."
- **CR 709.3**: "Each half of a split card has separate characteristics. When not on the stack, each half is considered independently for mana value, color, etc."
- **CR 709.4**: "Fuse is a keyword ability that allows a player to cast both halves of a split card from their hand."
- **CR 709.5**: "The mana value of a split card in any zone other than the stack is the total of both halves' mana values."
- **Example card**: Fire // Ice — "Fire deals 2 damage to any target. / Ice, tap target permanent."

## Acceptance Criteria
- [ ] SplitCard model extends Card with `left_half: Card`, `right_half: Card` fields
- [ ] Each half has its own name, mana_cost, type_line, oracle_text, colors, cmc
- [ ] In non-stack zones: mana value = left_cmc + right_cmc (CR 709.5)
- [ ] On the stack: mana value = only the cast half's mana value
- [ ] Casting a split card: player chooses which half (or both if Fuse) to cast
- [ ] Fuse: both halves are cast as one spell with combined effects; targeting is combined
- [ ] Each half's characteristics (color, type, etc.) are independent
- [ ] Cards that search for CMC/color check both halves (in non-stack zones)
- [ ] Integration tests cover: cast left half, cast right half, fuse both halves, mana value in hand vs stack, color identity for both halves
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Targeting Rules (CR 115, 601.2c) — each half may target separately
- Story: Modal Spells (CR 700.2) — casting a fuse card is similar to modal spells

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Multi-face card support exists (Card.faces list, face_index field, _apply_face_to_card(), _fuse_split_card() in stack.py for fuse). But missing: dedicated SplitCard model, CR 709.5 zone-dependent mana value calculation (combined in non-stack zones, half-only on stack), color identity from both halves, aftermath card support, and comprehensive split/fuse integration tests.

## Estimated Effort: M

## Notes
- Split cards have complex interactions with other rules — e.g., "target card in graveyard" with a split card can target either half
- Devoid and color identity: each half's color identity is considered independently, but in Commander, the total color identity includes both halves
- Fuse target selection: if both halves target, you choose all targets at once (can't choose the same target unless text allows)
- Aftermath cards (e.g., "Sorcery // Sorcery" with aftermath) are a variant of split cards with different casting restrictions
- The Card model likely needs a `split_half` field or `card_type = "split"` for identification
- When a split card is countered, both halves are countered (it's one spell on the stack)

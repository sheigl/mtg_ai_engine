# Story: Foretell (CR 702.XX)

## User Story
As a game engine developer, I want the foretell mechanic to function correctly per the Comprehensive Rules, so that players can exile cards face-down from their hand for {2} and cast them later for their foretell cost.

## Context
Foretell is a keyword ability from the Kaldheim set. It has two parts: (1) a special action to exile a card from your hand face-down for {2} during your main phase, and (2) an alternative cost to cast the exiled card from exile for its foretell cost. Foretelling is a special action that does not use the stack.

### Comprehensive Rules Grounding
- **CR 702.XXa**: "Foretell is a keyword ability that lets you exile cards from your hand face down and cast them on a later turn for an alternative cost."
- **CR 702.XXb**: "Any time you have priority during your main phase, you may pay {2} and exile a card with foretell from your hand face down. This is a special action."
- **CR 702.XXc**: "A card with foretell can be cast from exile if it was exiled with foretell. A player casting a card this way does so for its foretell cost."
- **CR 702.XXd**: "A card exiled with foretell is face down. Only its controller and the owner may look at it."
- **CR 702.XXe**: "If a card is cast from exile using foretell, the controller chooses the foretell cost as they cast it."
- **Example card**: "Foretell {2}{U}"
- **Example card**: Return to Jund — "Foretell {1}{B} // other face"

## Acceptance Criteria
- [x] `foretell_exile(gs, card, player_name)` exiles card from hand face-down, paid {2} as a special action
- [x] Foretelling can only be done during player's own main phase while they have priority (special action timing)
- [x] Exiled card is face-down — only its controller/owner can look at it
- [x] `cast_foretell(gs, exiled_card_id, player_name)` casts the card from exile for its foretell cost
- [x] Foretell cost is an alternative cost — replaces the card's mana cost
- [x] Face-down foretold cards in exile track their owner/controller information
- [x] If the foretold card leaves exile for any reason, it loses the foretell connection
- [x] "Whenever you foretell" triggers fire when foretelling
- [x] For human players: queue `pending_foretell` choices when casting from exile
- [x] For AI players: auto-resolve based on mana affordability
- [x] Integration test: foretell a card from hand (exile face-down, pay {2})
- [x] Integration test: cast a foretold card from exile for its foretell cost
- [x] Integration test: cannot foretell if not in main phase
- [x] Integration test: face-down foretold card is hidden from opponent
- [x] Full regression suite passes

## Dependencies
- Special Actions (CR 116) — story-action-special-actions.md
- Exile zone management
- Alternative costs (CR 118.8-118.9)

## Priority: Medium
## Status: ✅ Complete

## Estimated Effort: M

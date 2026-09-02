# Story: Cycle/Cycling (CR 702.28)

## User Story
As an MTG engine developer, I want the Cycling keyword module to have a real `apply()` implementation with integration tests, so that cards with Cycling can be discarded from hand for a cost to draw replacement cards.

## Context
The Cycling keyword module exists with partial Type Cycling logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.28a**: "Cycling is an activated ability. 'Cycling {cost}' means '{cost}, Discard this card: Draw a card.'"
- **CR 702.28b**: "Type cycling is a variation. 'Type cycling {cost}' means '{cost}, Discard this card: Draw X cards, where X is the number of card types of this card.'"
- **Example card**: Street Wraith — "Swampcycling {2}" (pay {2}, discard Street Wraith, search library for a Swamp and put it into your hand)

## Acceptance Criteria
- [ ] `CyclingKeyword.apply(game_state, card, player_name)` implements full cycling logic: validates card is in hand; queues `pending_cycling_choice` for human players with cost
- [ ] AI auto-resolves by paying cost if mana affordable
- [ ] Cycling {cost}: pay cost from mana pool, discard this card (hand -> graveyard), draw a card
- [ ] Type cycling variant: "{cost}, Discard this card: Draw X cards" where X = number of card types
- [ ] Basic land cycling, swampcycling, islandcycling etc. variants: search for basic land type and put into hand
- [ ] Cycling is activated at instant speed — can be activated any time player has priority
- [ ] Integration tests in `tests/engine/test_cycling_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **Cycling vs Type Cycling**: The existing `cycle.py` module conflates these. Regular cycling is "{cost}, Discard this card: Draw a card." Type cycling is "{cost}, Discard this card: Draw X cards" where X = number of types. Both should be supported in the same module with separate detection patterns.
- **Cycled trigger**: When a card is cycled, it may fire "whenever you cycle a card" triggers. Use `reason="cycle"` in zone change events to distinguish from other discard.
- **Type cycling**: The existing `TypeCyclingKeyword.get_card_type_count()` counts supertypes, types, and subtypes from the type_line. Reuse this for the type cycling variant.
- **Pending choice**: A `pending_cycling_choice` field should be added to GameState for human player interaction.

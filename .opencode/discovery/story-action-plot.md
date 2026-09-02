# Story: Plot (CR 702.XX)

## User Story
As a game engine developer, I want the plot mechanic to function correctly per the Comprehensive Rules, so that players can exile cards from their hand face up and cast them later from exile for their plot cost.

## Context
Plot is a keyword ability from the Outlaws of Thunder Junction set, similar to foretell but with key differences: plotted cards are exiled face-up (not face-down), and the timing/process differs. Plotting is a special action that does not use the stack.

### Comprehensive Rules Grounding
- **CR 702.XXa**: "Plot is a keyword ability that lets you exile cards from your hand face up and cast them on a later turn."
- **CR 702.XXb**: "Any time you have priority during your main phase, you may exile a card with plot from your hand face up. This is a special action."
- **CR 702.XXc**: "A card with plot can be cast from exile if it was exiled using plot. A player casting a card this way does so for its plot cost."
- **CR 702.XXd**: "Unlike foretell, plotted cards are face-up. All players may see the plotted card."
- **CR 702.XXe**: "A plotted card may be cast any time the player could cast it normally."
- **Example card**: "Plot {2}{B}"
- **Example card**: Freestrider Lookout — "Plot {1}{G}"

## Acceptance Criteria
- [ ] `plot_exile(gs, card, player_name)` exiles card from hand face-up as a special action
- [ ] Plotting can only be done during player's own main phase while they have priority
- [ ] Exiled card is face-up — all players can see it
- [ ] `cast_plot(gs, exiled_card_id, player_name)` casts the card from exile for its plot cost
- [ ] Plot cost is an alternative cost — replaces card's mana cost
- [ ] If the plotted card leaves exile, it loses the plot connection
- [ ] "Whenever you plot" triggers fire when plotting
- [ ] For human players: queue `pending_plot` choices when casting from exile
- [ ] For AI players: auto-resolve based on mana affordability and strategy
- [ ] Integration test: plot a card from hand (exile face-up)
- [ ] Integration test: cast a plotted card from exile for its plot cost
- [ ] Integration test: plotted card is visible to all players (unlike foretell)
- [ ] Full regression suite passes

## Dependencies
- Special Actions (CR 116) — story-action-special-actions.md
- Exile zone management
- Alternative costs (CR 118.8-118.9)
- Foretell (story-action-foretell.md) — similar mechanic with differences

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No plot implementation. Only appears in ability_parser.py keyword lists.

## Estimated Effort: M

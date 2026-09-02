# Story: Milled / Cards Put Into Graveyard From Library Trigger (CR 701.14)

## User Story
As an MTG engine developer, I want a "milled" trigger pattern with check function and engine wiring, so that cards with "whenever one or more cards are put into your graveyard from your library" triggered abilities fire correctly.

## Context
No mill trigger pattern exists in triggers.py. Mill effects (putting cards from library directly into graveyard) are distinct from discard (hand→graveyard) and death (battlefield→graveyard). Several cards have triggered abilities that respond to milling.

### Comprehensive Rules Grounding
- **CR 701.14**: "To mill N cards, a player puts the top N cards of their library into their graveyard. Some effects put cards from a player's library into a graveyard."
- **Game event**: One or more cards move from the top of a library directly to the graveyard
- **Example card**: *Dakmor Salvage* — "When ~ is put into your graveyard from your library, draw a card."

## Acceptance Criteria
- [ ] Create `MILLED_TRIGGER_PATTERNS` list with regexes matching: "whenever (?:a|an|one or more) card[s]? (?:is|are) put into your graveyard from your library", "whenever you mill", "when (?:this|~) is put into your graveyard from your library"
- [ ] Create `check_milled_triggers(game_state, player_name: str, milled_card_ids: list[str])` that queues PendingTriggers
- [ ] Wire into the mill/dredge resolution handler in stack.py (where cards move from library to graveyard)
- [ ] Integration tests: milling fires trigger, discarding does NOT fire, self-referential ("when this is milled") guard
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- Mill is specifically library→graveyard, not hand→graveyard (discard)
- "Whenever one or more cards" implies a single trigger event for the whole mill action
- Self-referential: "When ~ is put into your graveyard from your library" must check the card being milled
- Forge's trigger: `MilledTrigger`

# Story: Cycled Trigger (CR 702.28)

## User Story
As an MTG engine developer, I want a "cycled" trigger pattern with check function and engine wiring, so that cards with "when you cycle ~" triggered abilities fire correctly, distinct from generic discard triggers.

## Context
No cycled-specific trigger pattern exists in triggers.py. While `DISCARD_TRIGGER_PATTERNS` captures generic discard, cycling (CR 702.28) is a specific keyword action — discarding a card with cycling to draw a new card. Cards like [[Decree of Justice]] and [[Astral Slide]] have triggered abilities that fire specifically "when you cycle" a card.

### Comprehensive Rules Grounding
- **CR 702.28a**: "Cycling is an activated ability that functions only while the card with cycling is in a player's hand. 'Cycling [cost]' means '[Cost], Discard this card: Draw a card.'"
- **CR 702.28d**: "Some cards have triggered abilities that trigger 'when you cycle' or 'whenever you cycle.'"
- **Game event**: A player activates a cycling ability, discarding the card and drawing
- **Example card**: *Decree of Justice* — "When you cycle ~, you may pay {2}{W}. If you do, create a 4/4 white Angel creature token."

## Acceptance Criteria
- [ ] Create `CYCLED_TRIGGER_PATTERNS` list with regexes matching: "when you cycle", "whenever you cycle (?:a|an) (.*?)", "when you cycle ~"
- [ ] Create `check_cycled_triggers(game_state, cycled_card, player_name: str)` that queues PendingTriggers
- [ ] Wire into the cycling resolution handler (where cycling cost is paid and draw effect resolves)
- [ ] Integration tests: cycling a card fires trigger, generic discard without cycling does NOT fire
- [ ] No regressions

## Dependencies
- None (new trigger pattern)

## Priority: Medium

## Estimated Effort: M

## Notes
- Cycling IS a discard, but cycling triggers are distinct from generic discard triggers (CR 702.28d)
- The cycled card goes to the graveyard as part of the cycling cost
- Forge's trigger: `CycledTrigger`, `CycledDescendTrigger`

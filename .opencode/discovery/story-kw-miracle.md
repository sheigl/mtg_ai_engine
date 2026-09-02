# Story: Miracle (CR 702.93)

## User Story
As an MTG engine developer, I want the Miracle keyword module to have a real `apply()` implementation with integration tests, so that Miracle cards can be cast for their miracle cost when drawn as the first card of a turn.

## Context
The Miracle keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.93a**: "Miracle is a static ability. 'Miracle {cost}' means 'You may reveal this card as you draw it if it's the first card you've drawn this turn. If you do, you may cast it by paying {cost} rather than its mana cost.'"
- **CR 702.93b**: "A player can cast a spell with miracle only if they cast it from the library while the miracle trigger is on the stack."
- **Example card**: Terminus — "Miracle {W}" (if drawn first this turn, reveal and cast for {W} instead of {4}{W}{W})

## Acceptance Criteria
- [ ] `MiracleKeyword.apply(game_state, card, player_name)` implements full miracle logic: detects miracle on card drawn; checks if it's the first card drawn this turn by the player; queues `pending_miracle_choice` for human players
- [ ] AI auto-resolves by casting if it can afford the miracle cost (heuristic: always cast if affordable, beneficial spell)
- [ ] Miracle is an alternative cost — replaces mana cost entirely; uses alternative_cost field on StackObject
- [ ] First-card-drawn tracking: uses a `cards_drawn_this_turn: dict[str, int]` counter to determine if drawn card is the first
- [ ] Miracle cast from library — the card is moved from library to stack, not from hand
- [ ] Integration tests in `tests/engine/test_miracle_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
- **First-draw detection**: The engine needs to track how many cards each player has drawn each turn. Use an existing counter or add `cards_drawn_this_turn: dict[str, int]` to GameState. Reset at the beginning of each turn.
- **Miracle timing window**: The miracle trigger goes on the stack when the card is drawn. Players respond to the trigger, and the card remains revealed in the library until the trigger resolves. If they choose to cast it, it goes on the stack from the library.
- **Triggered ability**: Miracle is a static ability that creates a trigger when drawn. The trigger resolution offers the choice to cast for miracle cost. Follow the PendingTrigger pattern used by other triggered keywords.

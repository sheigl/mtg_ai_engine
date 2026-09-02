# Story: Scry (CR 701.19)

## User Story
As an MTG engine developer, I want the Scry keyword module to have a real `apply()` implementation with integration tests, so that card effects with Scry allow players to look at top library cards and reorder them.

## Context
The Scry keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 701.19a**: "To scry N, a player looks at the top N cards of their library, then puts any number of them on top of the library in any order and the rest on the bottom of the library in any order."
- **CR 701.19b**: "If there aren't enough cards in the library to scry this way, the player looks at as many as possible."
- **Example card**: Serum Visions — "Scry 2, then draw a card"

## Acceptance Criteria
- [ ] `Scry.apply(game_state, player_name, n)` implements full scry logic: looks at top N cards of player's library; for human players queues `pending_scry_choice` with card list and reorder options
- [ ] AI auto-resolves by putting worst estimated cards on bottom (heuristic: high-CMC nonlands on top, low-value lands on bottom)
- [ ] Scry respects library size: if fewer than N cards in library, scry all remaining
- [ ] Pure transform: returns new GameState via model_copy with updated library order
- [ ] Integration tests in `tests/engine/test_scry_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **GS-350**: `pending_scry_choice: Optional[dict]` already exists on GameState (line 350) with format `{"player": str, "cards": [Card], "n": int}` — reuse this field for human scry choices.
- **Scry AI heuristic**: For AI auto-resolution, look at CMC and type to estimate card quality. Put high-CMC nonlands on top, low-value lands on bottom. This matches the pattern used by other AI choice resolvers.
- **Scry trigger**: Scry effects may fire "whenever you scry" triggers. The scry implementation should not directly trigger these — instead, scry is an action keyword that should be detected by the trigger system separately.

# Story: Discard Trigger (CR 701.18)

## User Story
As an MTG engine developer, I want discard triggers wired into the engine event flow, so that cards with "whenever you discard a card" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_discard_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into all paths where cards are discarded (cycling, madness, forced discard effects) per CR 701.18.

### Comprehensive Rules Grounding
- **CR 701.18a**: "To discard a card, a player moves a card from their hand to their graveyard."
- **CR 701.18b**: "A player may discard a card to pay a cost, or an effect may cause a player to discard cards."
- **Game event**: Card moves from hand to graveyard via discard action (not via combat damage, sacrifice, or other zone changes)
- **Example card**: *Archfiend of Ifnir* — "Whenever you cycle or discard another card, put a -1/-1 counter on each creature your opponents control."

## Acceptance Criteria
- [ ] Call `check_discard_triggers(gs, player_name)` from stack.py's `_discard_cards()` helper after cards are moved from hand to graveyard
- [ ] Also wire into cycling resolution (`_apply_cycle()`) when cycling causes a card to be discarded
- [ ] Pass the player name to the check function
- [ ] Capture return value (`gs = check_discard_triggers(gs, player_name)`)
- [ ] Integration test: discarding fires trigger, non-discard zone changes (mill, sacrifice) do NOT fire, multiple discards each fire independently

## Dependencies
- None

## Priority: High

## Estimated Effort: S

## Notes
- **Multiple discard paths**: Discard can happen via spell effects ("Target player discards a card"), cycling costs, madness costs, and other game actions. Each path should call `check_discard_triggers()`.
- **Centralization**: Consider adding a helper function `_discard_card(gs, player_name, card_id)` that both moves the card to graveyard AND fires discard triggers, to avoid scattered wiring.
- **Distinct from sacrifice**: Discard is from hand→graveyard, while sacrifice is from battlefield→graveyard. These are separate trigger types.
- **Existing tests**: The function is tested in `tests/engine/test_new_trigger_types.py` and `tests/engine/test_triggers_expanded.py` — these should continue passing after wiring.

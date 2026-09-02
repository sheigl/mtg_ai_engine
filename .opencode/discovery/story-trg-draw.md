# Story: Draw Trigger (CR 701.16)

## User Story
As an MTG engine developer, I want draw triggers wired into the engine event flow, so that cards with "whenever you draw a card" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_draw_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into zones.py's `draw_card()` after a card moves from library to hand per CR 701.16.

### Comprehensive Rules Grounding
- **CR 701.16**: "To draw a card, a player reveals the top card of their library and puts it into their hand."
- **Game event**: Card moves from library to hand via draw action (not via tutor/search or other zone changes)
- **Example card**: *Chasm Skulker* — "Whenever you draw a card, put a +1/+1 counter on Chasm Skulker."

## Acceptance Criteria
- [ ] Call `check_draw_triggers(gs, player_name)` from zones.py's `draw_card()` after the card is moved from library to hand
- [ ] Pass the player name to the check function
- [ ] Capture return value (`gs = check_draw_triggers(gs, player_name)`)
- [ ] Integration test: drawing a card fires the trigger, initial draw (opening hand) does NOT fire (or fires context-appropriately), library-search effects do NOT fire draw trigger

## Dependencies
- None

## Priority: High

## Estimated Effort: S

## Notes
- **Scope of draw**: Only fire for actual draw actions (card draw via effect like "Draw a card" or the normal draw step). Library search effects ("Search your library for a card") move cards to hand but are NOT draws — they should fire `check_tutor_triggers()` instead.
- **Initial hand vs gameplay draw**: The opening hand draw happens before GameState setup and does not go through `draw_card()` — no wiring needed there.
- **Existing tests**: The function is tested in `tests/engine/test_new_trigger_types.py` and `tests/engine/test_triggers_expanded.py` — these should continue passing after wiring.

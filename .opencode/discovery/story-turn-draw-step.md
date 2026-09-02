# Story: Draw Step (CR 504)

## User Story
As a game engine developer, I want the draw step to function correctly per CR 504, so that the active player draws their normal card for the turn and alternative draws (like Dredge) are offered when applicable.

## Context
The draw step is the third and final step of the beginning phase. The active player draws one card from their library. If the player has cards with Dredge in graveyard, they may replace the normal draw with returning a dredge card to hand and milling instead. The "first card drawn this turn" tracking is done here for Miracle keyword support. The current engine has draw logic in `begin_step()` at `turn_manager.py` line 320-351, which checks for dredgeable cards and either queues a pending dredge choice or performs the normal draw via `draw_card()`.

### Comprehensive Rules Grounding
- **CR 504.1**: "The draw step is the third step of the beginning phase. The active player draws a card."
- **CR 504.2**: "First, the active player draws a card. Then any abilities that trigger on drawing a card trigger."
- **Purpose**: Provide the default card draw for each turn

## Acceptance Criteria
- [x] Active player draws exactly one card from library during draw step
- [x] If Dredgeable cards exist in graveyard, pending dredge choice is queued instead of normal draw
- [x] Dredge choice resolution either: returns dredge card to hand + mills N cards, or performs normal draw
- [x] Miracle first-card-of-turn tracking is set on the drawn card
- [x] "At the beginning of your draw step" triggers fire correctly
- [x] "Whenever you draw a card" triggers fire after the draw
- [x] Priority is granted to active player after draw completes
- [x] Full regression passes

## Dependencies
- story-turn-upkeep-step.md (Upkeep Step)
- story-kw-dredge.md (Dredge Keyword)

## Status: ✅ Complete

Implemented: `begin_step()` DRAW handler at `turn_manager.py:320-351` — checks for dredge first, falls back to `draw_card()` at `zones.py:774-800`. Empty library triggers SBA check. First-player turn-1 draw exception handled at game creation.

## Priority: High

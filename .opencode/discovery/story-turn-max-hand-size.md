# Story: Maximum Hand Size (CR 402.2)

## User Story
As a game engine developer, I want the maximum hand size rule to function correctly per CR 402.2, so that the active player discards down to their maximum hand size during the cleanup step.

## Context
Each player has a default maximum hand size of 7 cards. During the cleanup step of the ending phase, if the active player has more cards in hand than their maximum hand size, they must choose and discard cards until they have exactly that many cards in hand. Effects can modify a player's maximum hand size (e.g., "Your maximum hand size is equal to the number of cards in your hand" or "You have no maximum hand size"). The current engine has discard logic in `process_cleanup_step()` at `turn_manager.py` line 574-583.

### Comprehensive Rules Grounding
- **CR 402.2**: "Each player has a maximum hand size, which is normally 7. A player may have any number of cards in their hand. At the beginning of the cleanup step, a player discards down to their maximum hand size."
- **CR 402.3**: "Effects that modify a player's maximum hand size are applied during the cleanup step."
- **Purpose**: Prevent players from hoarding excessive cards; enforce strategic card management

## Acceptance Criteria
- [ ] Default maximum hand size is 7 cards for each player
- [ ] During cleanup step, active player with more than max hand size cards must discard down to max
- [ ] Discard is queued as a pending discard choice for the active player
- [ ] Effects that modify maximum hand size are respected (e.g., "your maximum hand size is 5")
- [ ] Effects granting "no maximum hand size" prevent the discard step entirely
- [ ] Non-active players do NOT discard during cleanup (only active player)
- [ ] Full regression passes

## Dependencies
- story-turn-cleanup-step.md (Cleanup Step)

## Status: 🔄 Partial

Implemented: `PlayerState.max_hand_size = 7` default at `models/game.py:213`. Discard-to-hand-size logic exists in `process_cleanup_step()` at `turn_manager.py:573-583`.

**Gap**: Since `process_cleanup_step()` is never called from the game loop, maximum hand size discard **never fires** during normal gameplay. This is blocked by the cleanup step wiring issue.

## Priority: High

# Story: Cleanup Step (CR 514)

## User Story
As a game engine developer, I want the cleanup step to function correctly per CR 514, so that discard to maximum hand size, damage removal, and "until end of turn" effect expiration occur at the correct time.

## Context
The cleanup step is the second and final step of the ending phase. During cleanup, the active player discards down to their maximum hand size (default 7). All damage is removed from permanents. "Until end of turn" effects expire (power/toughness bonuses, crewed status). State-based actions are checked, and if any triggered abilities result, the game loops back through cleanup with priority. The current engine has dedicated `process_cleanup_step()` at `turn_manager.py` line 555-630.

### Comprehensive Rules Grounding
- **CR 514.1**: "The cleanup step is the second step of the ending phase. The active player discards down to maximum hand size."
- **CR 514.2**: "After the active player discards, damage is removed from all permanents."
- **CR 514.3**: "After damage is removed, 'until end of turn' effects end."
- **CR 514.4**: "If any triggered abilities trigger during cleanup, the cleanup step continues and players receive priority."
- **Purpose**: Final housekeeping of the turn; ensure game state is clean for next turn

## Acceptance Criteria
- [ ] Active player discards cards down to maximum hand size (default 7)
- [ ] All damage marked on permanents is removed (`damage_marked = 0`)
- [ ] "Until end of turn" power/toughness bonuses are reset
- [ ] Creature type from crew effects is removed (`crewed_until_end_of_turn = False`)
- [ ] Mana pools are emptied
- [ ] State-based actions are checked after cleanup processing
- [ ] If any triggers fire during cleanup, players receive priority and cleanup loops back
- [ ] If no triggers fire, turn ends and next player's turn begins
- [ ] Full regression passes

## Dependencies
- story-turn-end-step.md (End Step)
- story-turn-max-hand-size.md (Maximum Hand Size)

## Status: 🔄 Partial

Implemented: `process_cleanup_step()` defined at `turn_manager.py:555-630` with discard-to-hand-size, damage removal, and end-of-turn effects expiry. However, this function is **never called** from the game loop — it only runs from test code. Cleanup actions never fire during normal gameplay.

**Gap**: Wire `process_cleanup_step()` into the CLEANUP step handler so that hand size discard, damage removal, and end-of-turn effects expire correctly.

## Priority: High

## Estimated Effort: S (wire existing function)

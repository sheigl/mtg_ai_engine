# Story: Completed Dungeon Trigger (CR 701.61)

## User Story
As an MTG engine developer, I want a completed-dungeon trigger pattern with check function and engine wiring, so that cards with "Whenever you complete a dungeon" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. Note: a `check_completed_dungeon_triggers()` function exists but is for a different trigger. This story is specifically for the "whenever you complete a dungeon" pattern that some cards use as a triggered ability (separate from the venture system's own completion handling).

### Comprehensive Rules Grounding
- **CR 701.61**: "To venture into the dungeon, the player moves their dungeon marker to the next room of the dungeon they're in. If that room is the last room of a dungeon, the player completes that dungeon."
- **Example card**: *Varis, Silverymoon Ranger* — "Whenever you complete a dungeon, create a 4/4 green Dragon creature token with flying."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into dungeon completion flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md
- Venture/Dungeon mechanic (story-gm-venture.md)

## Priority: Medium

## Estimated Effort: M

## Notes
- This trigger fires when any player completes a dungeon (reaches the last room).
- The dungeon completion event already has handling in the venture system; this trigger needs to hook into that event.
- Must not double-fire with existing dungeon completion handling.
- Example cards: *Varis, Silverymoon Ranger*, *Hama Pashar, Ruin Seeker*, *Nothic*, *Dungeon Delver*.

# Story: Entered Room Trigger (CR 701.61)

## User Story
As an MTG engine developer, I want an entered-room trigger pattern with check function and engine wiring, so that cards with "Whenever you enter a room" triggered abilities from dungeon-related cards fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. Some cards care about entering a specific room or any room in a dungeon.

### Comprehensive Rules Grounding
- **CR 701.61**: "To venture into the dungeon, the player moves their dungeon marker to the next room of the dungeon they're in."
- **Example card**: *Hama Pashar, Ruin Seeker* — "Whenever you enter a room, surveil 1."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into dungeon/venture flow when a player enters a room
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md
- Venture/Dungeon mechanic (story-gm-venture.md)

## Priority: Medium

## Estimated Effort: M

## Notes
- This trigger fires whenever any room in a dungeon is entered (including the first room).
- Distinguish from "when you complete a dungeon" — this is per-room, not per-dungeon.
- Example cards: *Hama Pashar, Ruin Seeker*, *Ninth Bridge Patrol*, *Dungeon Map*.
- Must be wired into the venture flow in dungeon.py when room advancement occurs.

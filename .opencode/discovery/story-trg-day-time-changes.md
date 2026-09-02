# Story: Day Time Changes Trigger (CR 702.148)

## User Story
As an MTG engine developer, I want a day-time-changes trigger pattern with check function and engine wiring, so that cards with "When day becomes night" or "When night becomes day" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. The day/night cycle is already implemented (DNG-01 story) but may not have triggers for when the transition occurs.

### Comprehensive Rules Grounding
- **CR 702.148**: "If it's not day and not night, as a turn begins, it becomes day. If it's day and it becomes night, as a turn begins, it becomes night. The reverse is also true."
- **Example card**: *Tovolar, Dire Overlord* — "Whenever it becomes day or night, you may draw a card."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py for day/night transitions
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into day/night transition flow in turn_manager.py
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md
- Day/Night Cycle mechanic (story-gm-day-night.md)

## Priority: Medium

## Estimated Effort: M

## Notes
- This trigger fires specifically on the transition from day to night or night to day, not on the state itself.
- Distinguish between "when day becomes night" vs "when night becomes day" vs "whenever day or night occurs" — both directions.
- The day/night cycle already has transition handling; this trigger hooks into that existing flow.
- Example cards: *Tovolar, Dire Overlord*, *Cemetery Gatekeeper*, *Mavinda, Students' Advocate*.

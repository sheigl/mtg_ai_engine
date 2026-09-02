# Story: Crew (CR 702.121a)

## User Story
As an MTG engine developer, I want the Crew keyword module to have a real `apply()` implementation with integration tests, so that Vehicle cards with Crew can be activated by tapping creatures to become artifact creatures until end of turn.

## Context
The Crew keyword module exists with detection/parsing logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.121a**: "Crew is an activated ability of Vehicle cards. 'Crew N' means 'Tap any number of untapped creatures you control with total power N or greater: This permanent becomes an artifact creature until end of turn.'"
- **Rule source**: Activated ability on Vehicle artifacts that temporarily animates them
- **Example card**: Smuggler's Copter — "Flying, Crew 1" (tap 1 total power worth of creatures to turn this into a 3/3 flying artifact creature)

## Acceptance Criteria
- [ ] `Crew.apply(game_state, permanent, target_creature_ids)` implements full crew logic: validates vehicle is on battlefield and untapped; queues `pending_crew_choice` for human players with crew value and available creature list
- [ ] AI auto-resolves by greedily tapping cheapest (lowest-power) creatures to meet power threshold
- [ ] Crewed vehicle becomes artifact creature until end of turn via `crewed_until_end_of_turn` flag on Permanent
- [ ] End-of-turn cleanup via `handle_crew_expiration(gs)` or existing DurationEffect infrastructure
- [ ] Power calculation sums tapped creatures' power; partial taps allowed (multiple creatures summed)
- [ ] Vehicle must be untapped to be crewed — already-tapped vehicles can't be crewed
- [ ] Integration tests in `tests/engine/test_crew_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **Crew tracking**: The Permanent model already has `crewed_until_end_of_turn: bool` field. Wire into turn_manager.py's end step cleanup, similar to the `dashed_creatures` pattern used by Dash keyword.
- **Power threshold validation**: When resolving crew, sum the power of all selected creatures and verify >= crew value. Reject if insufficient.
- **Vehicle already has a `crewed_until_end_of_turn` field on Permanent** — no new GameState field needed for the flag itself, but a pending choice field (`pending_crew_choice`) will be needed on GameState for human player interaction.

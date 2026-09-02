# Story: Vehicle Rules (CR 301.7)

## User Story
As a game engine developer, I want Vehicle rules to function correctly per the Comprehensive Rules, so that Vehicles are non-creature artifacts by default, become creatures when crewed by tapping creatures with total power meeting the crew cost, and stop being creatures at end of turn.

## Context
Vehicles are artifact subtypes that can become artifact creatures. A Vehicle is not inherently a creature — it becomes one when its Crew ability is activated. The Crew cost requires tapping any number of untapped creatures you control with total power equal to or greater than the crew value. The Vehicle remains a creature until end of turn.

### Comprehensive Rules Grounding
- **CR 301.7**: "A Vehicle is an artifact subtype that can become an artifact creature. It is represented by the crew ability."
- **CR 702.121a**: "Crew [N] — Tap any number of untapped creatures you control with total power [N] or more: This permanent becomes an artifact creature until end of turn."
- **CR 702.121b**: "A Vehicle's power and toughness are usually specified on the card (e.g., Smuggler's Copter is a 3/3)."
- **CR 702.121c**: "A Vehicle that's crewed becomes a creature until end of turn. It loses 'creature' as a type at the cleanup step."
- **CR 702.121d**: "A Vehicle's crew cost can be paid by tapping any number of creatures whose total power meets or exceeds the crew cost."
- **Example card**: Smuggler's Copter — Artifact — Vehicle, 3/3, "Crew 1", "Flying, Whenever Smuggler's Copter attacks or blocks, look at the top card of your library."

## Acceptance Criteria
- [x] Vehicles enter the battlefield as non-creature artifacts (not creatures)
- [x] Crew N ability: requires tapping untapped creatures with total power >= N (CR 702.121a)
- [x] Crewed Vehicle becomes an artifact creature until end of turn (CR 702.121c)
- [x] Vehicle has printed power and toughness that apply when it becomes a creature
- [x] Vehicle can attack/block when crewed (but not when uncrewed)
- [x] Vehicle reverts to non-creature at end of turn / cleanup step (CR 702.121c)
- [x] Vehicle that is crewed and then loses its crewers midway still remains a creature until end of turn (once it's crewed, it stays crewed)
- [x] Crewing a Vehicle doesn't use the stack (crew is a mana ability-like activation)
- [x] A Vehicle can be crewed multiple times (redundant, has no additional effect)
- [x] Vehicle with other types (e.g., "Artifact Creature — Vehicle" from an effect) already a creature
- [x] Full regression suite passes

## Dependencies
- Story: Crew Keyword (CR 702.121a) — detailed crew ability rules
- Story: Artifact Rules (CR 301) — parent card type rules

## Status: ✅ Complete

Implemented: Covers under Artifact story. Vehicle model (`models/artifact.py`), Crew keyword (`ability/keywords/crew.py`), `crewed_until_end_of_turn` on Permanent.

## Priority: High

## Notes
- The existing `mtg_engine/models/artifact.py` has a `VehicleModel` class
- `mtg_engine/models/card_type.py` has `ArtifactSubtype.VEHICLE` and `CardType.is_vehicle()` helper
- The engine likely has a `crewed_vehicles` or similar tracking on GameState to remember which vehicles are crewed until end of turn
- Crew is a mana ability (it doesn't use the stack) — this is important for timing: it can't be responded to
- The creatures used to crew the Vehicle don't have to be untapped for any other reason — tapping them is part of the cost
- Tapped creatures can't be used to crew (they must be untapped)
- The tapped creatures used for crewing don't need to share a creature type or have any other restriction
- When a Vehicle becomes a creature, it gains "artifact creature" and loses nothing else
- A Vehicle becoming a creature is subject to summoning sickness unless it's been under its controller's control since the start of turn
- Crew can be activated any time you could cast a sorcery (main phase, stack empty)
- Vehicles with "Crew 1" printed can be crewed by a single 1-power creature (like a 1/1 token)

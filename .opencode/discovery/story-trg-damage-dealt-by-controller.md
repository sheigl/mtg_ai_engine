# Story: Damage Dealt By Controller Trigger (CR 119.3)

## User Story
As an MTG engine developer, I want a damage-dealt-by-controller trigger pattern with check function and engine wiring, so that cards with "Whenever a source you control deals damage" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. This trigger fires when ANY source controlled by a player deals damage (as opposed to a specific permanent dealing damage).

### Comprehensive Rules Grounding
- **CR 119.3**: "Damage may be dealt as a result of combat or as a result of a spell or ability. Some effects deal damage directly."
- **Example card**: *Mechanized Production* — "Whenever a creature you control deals combat damage to a player, you may draw a card."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into damage-dealing flow (both combat and non-combat)
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- This trigger fires when a source controlled by the triggering player deals damage.
- Distinguish from "whenever ~ deals damage" (specific source) — this is "any source you control."
- Example cards: *Mechanized Production*, *Pyrohemia*, *Pestilence*, *Cryptolith Fragment*.
- Must coexist with specific damage triggers without double-firing the same event.

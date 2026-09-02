# Story: Planar Die (CR 901.5)

## User Story
As a game engine developer, I want the planar die to function correctly per the Comprehensive Rules, so that Planechase games can use the planar die to roll for planeswalk and chaos effects.

## Context
The planar die is a special six-sided die used exclusively in Planechase. It has six faces: one "Planeswalk" face (PW symbol), one "Chaos" face (C symbol), and four blank faces. Rolling the planar die is a special action players can take during Planechase games. The result determines whether the player planeswalks to a new plane or triggers the current plane's chaos ability.

### Comprehensive Rules Grounding
- **CR 901.5**: "The planar die is a special six-sided die used in Planechase games."
- **CR 901.5a**: "The planar die has six faces: one planeswalk (PW symbol), one chaos (C symbol), and four blank faces."
- **CR 901.5b**: "A player may roll the planar die as a special action during their main phase."
- **CR 901.5c**: "When a planeswalk result is rolled, the player planeswalks — the current plane is turned face down and a new plane is turned face up."
- **CR 901.5d**: "When a chaos result is rolled, the current plane's chaos ability triggers."
- **CR 901.5e**: "Blank faces have no effect."
- **CR 901.12**: "When a player rolls the planar die, any ability that triggers 'whenever you roll the planar die' triggers."
- **Example card**: Any plane card — e.g., The Aether Flues — chaos ability: "Target player sacrifices a creature."

## Acceptance Criteria
- [ ] `roll_planar_die(gs, player_name)` returns one of three results: planeswalk, chaos, or blank
- [ ] The die has 6 faces: 1 planeswalk, 1 chaos, 4 blank (1/6 chance each at face level)
- [ ] Rolling the die is a special action (doesn't use stack)
- [ ] Planeswalk result: current plane is turned face down, new plane is turned up
- [ ] Chaos result: the current plane's chaos ability is triggered
- [ ] Blank: no effect
- [ ] "Whenever you roll the planar die" triggers fire
- [ ] For human players: auto-roll (deterministic with seed)
- [ ] Integration test: roll planar die with known seed — verify result
- [ ] Integration test: planeswalk result changes the plane
- [ ] Integration test: chaos result fires trigger
- [ ] Full regression suite passes

## Dependencies
- Die rolling infrastructure (story-action-roll-die.md)
- Planechase variant rules
- Special Actions (story-action-special-actions.md)

## Priority: Low
## Status: ❌ Not Implemented

> **Gap**: No planar die implementation.

## Estimated Effort: S

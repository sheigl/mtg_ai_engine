# Story: Extra Turns (CR 502.3)

## User Story
As a game engine developer, I want extra turns to function correctly per the Comprehensive Rules, so that effects that grant extra turns (e.g., Time Warp, Emrakul's effect) insert the extra turn immediately after the current turn.

## Context
Extra turns are turns added to the turn order by spells or abilities. They are taken immediately after the current turn ends, before the next player's normal turn. Extra turns follow all normal turn structure rules (beginning, main, combat, ending phases).

### Comprehensive Rules Grounding
- **CR 502.3**: "Some effects give a player extra turns. They are taken after the current turn."
- **CR 502.3a**: "If multiple extra turns are created, they are taken in the order they were created (reverse chronological order of resolution for effects on the stack)."
- **CR 502.3b**: "Extra turns follow all normal turn rules (untap, upkeep, draw, etc.)."
- **CR 502.3c**: "A player can't skip an extra turn unless an effect explicitly says so."
- **CR 502.3d**: "Effects that say 'target player takes an extra turn' give that player the extra turn."
- **Example card**: Time Warp — "Target player takes an extra turn after this one."
- **Example card**: Emrakul, the Promised End — "You control target player during that player's next turn."
- **Example card**: Nexus of Fate — "Take an extra turn after this one."

## Acceptance Criteria
- [x] `grant_extra_turn(gs, player_name)` adds an extra turn to the turn order
- [x] The extra turn is taken immediately after the current turn ends
- [x] Multiple extra turns are tracked in order (FIFO for same-creation-time, reverse chronological for different)
- [x] The extra turn follows full turn structure (5 phases)
- [x] Normal turn order resumes after all extra turns are complete
- [x] Extra turns respect "skip your next turn" effects
- [x] "At the beginning of your extra turn" triggers fire
- [x] Extra turn counters (e.g., "take an extra turn, then skip your next turn") are tracked
- [x] Integration test: cast Time Warp, verify extra turn is taken after current turn
- [x] Integration test: two extra turns in a row — both are taken
- [x] Integration test: "skip your next turn" effect skips an extra turn
- [x] Full regression suite passes

## Dependencies
- Turn Structure stories (all phases/steps must work)
- Turn Manager (extra turn insertion logic)

## Priority: Medium
## Status: ✅ Complete

## Estimated Effort: M

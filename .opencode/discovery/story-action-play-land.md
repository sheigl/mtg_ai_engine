# Story: Playing a Land (CR 305)

## User Story
As a game engine developer, I want playing a land to function correctly per the Comprehensive Rules, so that players can play lands during their main phase when the stack is empty, limited to one land per turn, and without using the stack.

## Context
Playing a land is a special action (CR 116) that does not use the stack and cannot be responded to. It is limited to one land per turn unless an effect grants additional land plays. Lands can only be played during a player's own main phase when the stack is empty, unless an effect allows otherwise.

### Comprehensive Rules Grounding
- **CR 305.1**: "A player can play a land during their main phase when the stack is empty."
- **CR 305.2**: "A player can play only one land during their turn. Effects that allow additional land plays override this rule."
- **CR 305.3**: "A land can't be played if an effect prevents a player from playing lands."
- **CR 305.4**: "Effects that allow a player to 'play' additional lands allow the player to play lands as if they were in their main phase and the stack were empty."
- **CR 305.5**: "Playing a land is a special action (see CR 116). Special actions don't use the stack."
- **CR 116.3a**: "A player may play a land during their main phase when the stack is empty."
- **Example card**: Forest — basic land played from hand
- **See also**: Special Actions (CR 116), Turn Structure main phase (story-turn-main-phase.md)

## Acceptance Criteria
- [x] `play_land(gs, card, player_name)` moves land from hand to battlefield
- [x] Land enters untapped by default (some have ETB tapped effects)
- [x] One-land-per-turn limit is enforced (tracked by `lands_played_this_turn` counter)
- [x] Can only be played during own main phase with empty stack
- [x] `can_play_land(gs, player_name, card)` checks: turn phase, stack emptiness, land count, existing land plays
- [x] Effects that grant additional land plays increment the allowed count
- [x] Effects that prevent land plays block the action
- [x] Playing a land does NOT use the stack — no priority pass, no responses
- [x] Multiple land types (basic, snow, non-basic) all follow same rules
- [x] Integration test: play a land during main phase, verify it enters battlefield untapped
- [x] Integration test: attempting second land in same turn fails
- [x] Integration test: playing land does not give opponent priority in between
- [x] Integration test: land with ETB tapped effect works (e.g., shockland without paying)
- [x] Full regression suite passes

## Dependencies
- Special Actions (CR 116) — story-action-special-actions.md
- Turn Structure — main phase (story-turn-main-phase.md), priority system

## Priority: High
## Status: ✅ Complete

## Estimated Effort: M

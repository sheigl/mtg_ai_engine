# Story: Special Actions (CR 116)

## User Story
As a game engine developer, I want special actions to function correctly per the Comprehensive Rules, so that actions that don't use the stack (playing lands, foretelling, suspending, morphing, etc.) can be taken at the appropriate times.

## Context
Special actions are a category of game actions that do NOT use the stack and cannot be responded to. They form a critical part of the game's structure. Understanding which actions are special actions and when they can be taken is essential for correct game engine behavior.

### Comprehensive Rules Grounding
- **CR 116.1**: "Special actions are actions a player may take that don't use the stack."
- **CR 116.2**: "Special actions can be taken only when certain conditions are met."
- **CR 116.3**: "List of special actions:" 
  - **a**: Playing a land (during main phase, stack empty)
  - **b**: Turning a face-down creature face up (morph, disguise — any time you could cast an instant)
  - **c**: Exiling a card with suspend from your hand (during main phase, sorcery speed)
  - **d**: Exiling a card with foretell from your hand (during main phase, sorcery speed)
  - **e**: Exiling a card with plot from your hand (during main phase, sorcery speed)
  - **f**: Paying {3} to put a companion from sideboard into hand (any time you could cast an instant)
  - **g**: Designating a commander to go to command zone (zone replacement choice)
- **CR 116.4**: "Taking a special action doesn't use the stack. It can't be responded to."
- **CR 116.5**: "A player can take a special action only when they have priority or when the rules specify otherwise."
- **Example card**: Playing a Forest — special action (story-action-play-land.md)
- **Example card**: Morph — special action to turn creature face up

## Acceptance Criteria
- [ ] All special actions from CR 116.3 are implemented as stack-free operations
- [ ] `validate_special_action(gs, action_type, player_name)` checks timing/condition requirements
- [ ] `execute_special_action(gs, action_type, player_name, targets)` executes the action
- [ ] Special actions cannot be responded to (no priority passes between action and completion)
- [ ] Playing a land: only during main phase with empty stack
- [ ] Morph/disguise: any time player could cast an instant
- [ ] Foretell/suspend/plot: during main phase, sorcery speed
- [ ] Companion: any time player could cast an instant
- [ ] Integration test: play a land during main phase — no priority passes
- [ ] Integration test: morph during combat — opponent cannot respond
- [ ] Integration test: attempt special action at wrong time — rejected
- [ ] Full regression suite passes

## Dependencies
- All individual special actions (play-land, morph, foretell, suspend, plot, companion)
- Priority System (story-turn-priority-system.md)

## Priority: High
## Status: 🔄 Partial

> **Gap**: Individual special actions exist (play_land, morph turn_face_up, foretell, companion) but no unified `validate_special_action()` / `execute_special_action()` dispatcher.

## Estimated Effort: L

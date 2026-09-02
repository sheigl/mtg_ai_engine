# Story: State-Based Actions (CR 704)

## User Story
As a game engine developer, I want state-based actions to be checked after each time a player would receive priority, so that game state accurately reflects conditions like lethal damage, zero life, and the legend rule.

## Context
State-based actions (SBAs) are automatic game actions that the engine must check whenever a player would receive priority (CR 704.3). They include checking for players at 0 or less life, creatures with lethal damage, planeswalkers with 0 loyalty, legendary permanents violating the legend rule, tokens in non-battlefield zones, and more. SBAs are checked repeatedly in a loop until no more apply (CR 704.2).

### Comprehensive Rules Grounding
- **CR 704.1**: "State-based actions are game actions performed automatically whenever certain conditions are met, such as a creature's life total being 0 or less."
- **CR 704.2**: "State-based actions are checked continuously throughout the game. If any state-based action applies, it is performed and then checking resumes from the start."
- **CR 704.3**: "Whenever a player would receive priority, the game first performs all applicable state-based actions as a single event."
- **CR 704.5**: Lists all state-based actions including player loss (a-d), creatures with lethal damage (h), planeswalker loyalty (i), legend rule (j), tokens in non-battlefield zones (d), and more.
- **Example card**: Any creature with lethal damage marked on it

## Acceptance Criteria
- [x] SBA check function `check_state_based_actions(gs) -> GameState` is called at every priority grant
- [x] SBA loop continues until no more actions apply (CR 704.2 self-repeating loop)
- [x] Player with 0 or less life loses the game (CR 704.5a)
- [x] Creature with lethal damage (toughness <= damage) is destroyed (CR 704.5h)
- [x] Planeswalker with 0 loyalty is put into graveyard (CR 704.5i)
- [x] Legend rule: two+ same-name legendary permanents → owner keeps one, sacrifices rest (CR 704.5j)
- [x] Token in non-battlefield zone ceases to exist (CR 704.5d)
- [x] Aura attached to illegal permanent is put into graveyard (CR 704.5n)
- [x] Equipment/fortification attached to illegal permanent becomes unattached (CR 704.5p/q)
- [x] Creature with 0 or less toughness is put into graveyard (CR 704.5f)
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (fundamental game loop infrastructure)

## Priority: High

## Status: ✅ Complete

## Estimated Effort: L

## Notes
- This is the MOST CRITICAL engine subsystem — SBAs govern life loss, creature death, and many other fundamental game actions
- Currently the engine may have SBA checks scattered in various places; this story calls for a centralized SBA check loop
- The SBA loop must be efficient (O(n) per check) since it runs at every priority grant
- Certain SBAs create pending triggers (e.g., "when this creature dies") which must be queued during SBA resolution
- SBA loop runs: Priority Check → SBAs loop until stable → Priority granted
- The SBA loop must handle the case where resolving one SBA creates conditions for another SBA (e.g., Aura becomes illegally attached when its creature dies)

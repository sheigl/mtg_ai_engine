# Story: Toxic (CR 702.134)

## User Story
As an MTG engine developer, I want the Toxic keyword module to have a real `apply()` implementation with integration tests, so that creatures with Toxic give poison counters to players they deal combat damage to.

## Context
The Toxic keyword module exists with a partial `apply_toxic()` method but its main `apply()` is a NOOP stub. It needs a real implementation wired into the combat damage flow following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.134a**: "Toxic is a static ability. 'Toxic N' means 'Whenever this creature deals combat damage to a player, that player gets N poison counters.'"
- **CR 702.134b**: "A player who has ten or more poison counters loses the game." (CR 704.5i)
- **Example card**: Venom Connoisseur — "Toxic 1" (deals combat damage to a player → that player gets 1 poison counter)

## Acceptance Criteria
- [ ] `ToxicKeyword.apply(game_state, permanent)` refactored to call `apply_toxic()` from combat damage flow; wired into `combat/core.py` `assign_combat_damage()` alongside existing deathtouch/lifelink/infect calls
- [ ] Toxic triggers once per combat damage event (not per point of damage) — even 1 damage gives full N counters
- [ ] Player with 10+ poison counters loses the game (CR 704.5i) — checked via SBA after toxic resolves
- [ ] Pure transform: returns new GameState via model_copy with updated `poison_counters` on player
- [ ] Non-combat damage does NOT trigger toxic — only combat damage to players
- [ ] Integration tests in `tests/engine/test_toxic_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **Toxic combat wiring**: Toxic's `apply_toxic()` already exists but isn't called from combat. Wire it into `combat/core.py`'s damage assignment loop alongside existing deathtouch/lifelink/infect keyword calls (lines 605-735).
- **Poison counter tracking**: `poison_counters: int = 0` already exists on PlayerState (game.py line 209). Increment by N when toxic triggers. Check >= 10 via SBA after combat damage step.
- **Once per event**: Toxic fires once per combat damage event, regardless of how much damage is dealt. A 5/5 with Toxic 2 gives 2 poison counters whether it deals 1 or 5 damage.

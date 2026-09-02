# Story: Stub Keywords — Common Mechanics (Crew, Equip, Cycle/Cycling, Scry, Ward, Toxic)

## User Story
As an MTG engine developer, I want the six most common stub keyword modules to have real `apply()` implementations with integration tests, so that games using these keywords produce correct game state instead of silently no-op'ing.

## Context
Six keyword files exist in `mtg_engine/ability/keywords/` with detection/parsing but NOOP `apply()` methods:

1. **Crew** (`crew.py`) — Detection + parsing done, `apply()` returns `game_state`. Crew N means "Tap any number of untapped creatures you control with total power N or more: This permanent becomes an artifact creature until end of turn." (CR 702.147)
2. **Equip** (`equip.py`) — Detection + parsing done, `apply()` returns `game_state`. Equip {cost} means "Activate this ability only any time you could cast a sorcery: Attach this Equipment to target creature you control." (CR 702.5)
3. **Cycle/Cycling** (`cycle.py`) — Has TypeCyclingKeyword class with partial logic, but `apply()` returns `game_state`. Cycling {cost} means "{cost}, Discard this card: Draw a card." (CR 702.36). The existing module conflates cycling and type-cycling; needs both.
4. **Scry** (`scry.py`) — Detection + parsing done, `apply()` returns `game_state`. Scry N means "Look at the top N cards of your library, then put any number on bottom and rest on top in any order." (CR 701.20)
5. **Ward** (`ward.py`) — Detection + parsing done, `apply()` returns `game_state`. Ward {cost} means "Whenever this permanent becomes the target of a spell or ability, counter it unless that spell or ability's controller pays {cost}." (CR 702.145)
6. **Toxic** (`toxic.py`) — Has `apply_toxic()` helper but main `apply()` returns `game_state`. Toxic N means "Whenever this creature deals combat damage to a player, that player gets N poison counters." (CR 702.134). Partial logic exists but not wired into combat flow.

All six follow the established pattern: detection/parsing from oracle text, class hierarchy inheritance from base.py, and need real `apply()` methods using pure transforms (`model_copy(update={...})`).

## Acceptance Criteria

### Crew (CR 702.147)
- [ ] `Crew.apply(game_state, permanent)` implements full crew logic: validates vehicle is on battlefield, queues `pending_crew_choice` for human players with crew value and available creatures list; AI auto-resolves by greedily tapping cheapest creatures to meet power threshold
- [ ] Crewed vehicle becomes artifact creature until end of turn (adds "artifact" supertype and "creature" type)
- [ ] End-of-turn cleanup: vehicle loses creature status at end step via `handle_crew_expiration(gs)` in turn_manager.py or SBA check
- [ ] Power calculation sums tapped creatures' power; partial taps allowed (tap 3/3 + 2/2 to crew 5, not just single 5+/5+)
- [ ] Integration tests: detection, human choice queuing, AI auto-resolution, power threshold validation, end-of-turn expiration, vehicle type change

### Equip (CR 702.5)
- [ ] `Equip.apply(game_state, permanent)` implements full equip logic: validates equipment is on battlefield and controller has priority during sorcery timing; queues `pending_equip_choice` for human with equipment perm_id and valid target list; AI auto-resolves by equipping to highest-power creature
- [ ] Equipment attaches to target creature (updates `attached_to` field on permanent)
- [ ] Equipped creature gains static bonuses from equipment's oracle text (+N/+N patterns parsed at resolution time)
- [ ] Sorcery-speed timing: equip can only be activated during controller's main phase when stack is empty
- [ ] Integration tests: detection, cost parsing, human choice queuing, AI auto-resolution, attachment state change, sorcery-timing guard

### Cycling (CR 702.36)
- [ ] `CyclingKeyword.apply(game_state, card, player_name)` implements full cycling logic: validates card is in hand, queues `pending_cycling_choice` for human with cycling cost; AI auto-resolves by paying cost and discarding + drawing
- [ ] Cycling {cost}: pay cost, discard this card (hand -> graveyard), draw a card
- [ ] Type cycling variant also supported: "{X}, Discard this card: Draw X cards" where X = number of card types on the card
- [ ] Both regular cycling and type-cycling detection patterns work from oracle text
- [ ] Integration tests: regular cycling detection, cost parsing, human choice queuing, AI auto-resolution, discard + draw flow, type-cycling variant

### Scry (CR 701.20)
- [ ] `Scry.apply(game_state, permanent)` implements full scry logic: looks at top N cards of controller's library, for human players queues `pending_scry_choice` with card list and reorder options; AI auto-resolves by putting worst cards on bottom (heuristic-based)
- [ ] Scry respects library size: if fewer than N cards in library, scry all remaining
- [ ] Pure transform: returns new GameState via model_copy with updated library order
- [ ] Integration tests: detection, value parsing, human choice queuing, AI auto-resolution, small library edge case, pure transform verification

### Ward (CR 702.145)
- [ ] `Ward.apply(game_state, permanent)` implements full ward logic: when the permanent becomes a target of an opponent's spell/ability, counter that spell/ability unless its controller pays the ward cost; queues `pending_ward_choice` for human players
- [ ] Ward only triggers on targeting by opponents — self-targeting bypasses ward (CR 702.145b)
- [ ] Ward cost is paid by the spell/ability's controller, not the ward's controller
- [ ] Multiple wards on same permanent: each ward triggers independently; paying one doesn't pay others
- [ ] Integration tests: detection, cost parsing, opponent targeting triggers ward, self-targeting bypasses ward, human choice queuing, AI auto-resolution (pays if affordable), multiple wards

### Toxic (CR 702.134)
- [ ] `ToxicKeyword.apply_toxic(game_state, source_perm, damaged_player_name)` wired into combat damage flow in `combat/core.py` during `assign_combat_damage()`: when a toxic creature deals combat damage to a player, that player gets N poison counters
- [ ] Toxic triggers once per combat damage event (not per point of damage) — even 1 damage gives full N counters
- [ ] Player with 10+ poison counters loses the game (CR 704.5i) — checked via SBA after toxic resolves
- [ ] Pure transform: returns new GameState via model_copy with updated poison_counters on player
- [ ] Integration tests: detection, value parsing, combat damage triggers toxic, poison counter accumulation, loss at 10+ counters, non-combat damage does NOT trigger toxic

### Cross-cutting requirements
- [ ] All `apply()` methods follow pure transform pattern: return new GameState via `model_copy(update={...})`, never mutate directly
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other Sprint 7 stories; uses existing trigger/stack/combat infrastructure)

## Priority: High

## Estimated Effort: L (6 keywords × ~0.5 day each = 3 days)

## Notes
- **Crew complexity**: Crew requires tracking which creatures were tapped for crew and restoring them at end of turn. Consider a `crewed_vehicles` dict on GameState similar to `dashed_creatures` pattern used by Dash keyword.
- **Equip timing**: Equip is sorcery-speed only. The legal actions system needs to know when equip can be activated (main phase, stack empty). Reference how activated abilities are gated in `_compute_legal_actions`.
- **Cycling vs Type Cycling**: The existing `cycle.py` module conflates these. Regular cycling is "{cost}, Discard this card: Draw a card." Type cycling is "{X}, Discard this card: Draw X cards" where X = number of types. Both should be supported in the same module with separate detection patterns.
- **Scry AI heuristic**: For AI auto-resolution, use a simple heuristic: look at CMC and type to estimate card quality; put high-CMC nonlands on top, low-value lands on bottom. This matches the pattern used by other AI choice resolvers (e.g., ETB choices).
- **Ward targeting integration**: Ward needs to hook into the targeting validation flow. When a spell/ability targets a permanent with ward, check if the spell controller differs from the ward controller before triggering. Reference how hexproof/shroud integrate with targeting validation.
- **Toxic combat wiring**: Toxic's `apply_toxic()` already exists but isn't called from combat. Wire it into `combat/core.py`'s damage assignment loop alongside existing deathtouch/lifelink/infect keyword calls (lines 605-735).

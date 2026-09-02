# Story: Counter Placed Trigger (CR 122.1)

## User Story
As an MTG engine developer, I want counter-placed triggers wired into the engine event flow, so that cards with "whenever a counter is placed on a creature" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_counter_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring wherever counters are placed or removed via effect resolution per CR 122.1 — likely through stack.py's effect application patterns.

### Comprehensive Rules Grounding
- **CR 122.1**: "A counter is a marker placed on an object or player that modifies its characteristics and/or interacts with a number of abilities."
- **CR 122.6**: "If a spell or ability instructs a player to put counters on an object, that player puts that many counters on that object."
- **Game event**: One or more counters are placed on a permanent (or removed from a permanent) as the result of a spell or ability resolving
- **Example card**: *Reyhan, Last of the Abzan* — "Whenever a +1/+1 counter is put on a creature you control, you may move a +1/+1 counter from Reyhan onto that creature."

## Acceptance Criteria
- [ ] Call `check_counter_triggers(gs, perm_id, player_name)` from stack.py wherever counters are placed via effect resolution
- [ ] Consider creating a centralized `_place_counter(gs, perm_id, counter_type, amount)` helper that both places the counter AND fires the trigger
- [ ] Also consider negative cases (counter removal, -1/-1 counters)
- [ ] Capture return value (`gs = check_counter_triggers(gs, perm_id, player_name)`)
- [ ] Integration test: placing a +1/+1 counter fires trigger, removing a counter does NOT fire placed trigger (or fires a separate removal trigger), non-counter permanent changes do NOT fire

## Dependencies
- None

## Priority: High

## Estimated Effort: M

## Notes
- **Counter placement complexity**: Counters can be placed/removed from many different sources:
  - Effect resolution in `_apply_single_effect_text()` (e.g., "put a +1/+1 counter on target creature")
  - ETB effects (e.g., "enters the battlefield with X +1/+1 counters")
  - Combat damage with infect (creates -1/-1 counters via `_deal_damage()` in stack.py)
  - Keyword abilities like Sunburst (already wired via `apply_sunburst_counters()`)
  - Proliferate (already wired via `check_proliferated_triggers()` in `proliferate.py`)
- **Centralized helper recommended**: Create `_place_counter(gs, perm_id, counter_type, amount) -> GameState` in stack.py or a utilities module. All counter-placement code paths route through this single function, and the trigger call lives in one place.
- **Existing tests**: The function is tested in `tests/engine/test_new_trigger_types.py` and `tests/engine/test_triggers_expanded.py` — these should continue passing after wiring.

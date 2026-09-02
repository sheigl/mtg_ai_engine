# Story: Bloodthirst (CR 702.22)

## User Story
As an MTG engine developer, I want the Bloodthirst keyword module to have a real `apply()` implementation with integration tests, so that creatures with Bloodthirst enter the battlefield with +1/+1 counters when an opponent was dealt damage this turn.

## Context
The Bloodthirst keyword module exists with detection/parsing and trigger creation logic but its `apply()` method is a NOOP stub. It needs a real implementation following the pure transform pattern (`model_copy(update={...})`).

### Comprehensive Rules Grounding
- **CR 702.22a**: "Bloodthirst is a triggered ability. 'Bloodthirst N' means 'If an opponent was dealt damage this turn, this permanent enters the battlefield with N +1/+1 counters on it.'"
- **CR 702.22b**: "The damage may be combat damage or non-combat damage, and may have been dealt at any time this turn."
- **Example card**: Gore-House Chainwalker — "Bloodthirst 1" (if opponent was dealt any damage this turn, this enters with one +1/+1 counter)

## Acceptance Criteria
- [ ] `BloodthirstKeyword.apply(game_state, permanent)` implements full bloodthirst logic: checks if any opponent of the controller was dealt damage this turn; puts N +1/+1 counters on the creature if condition is met
- [ ] Bloodthirst triggers as an ETB effect — wired into `put_permanent_onto_battlefield()` in `zones.py`
- [ ] Pure transform: returns new GameState via model_copy with updated counters on the permanent
- [ ] Damage tracking: uses existing `damage_dealt_this_turn` tracking or inspects player/creature damage records
- [ ] Any damage source counts (combat, spell, ability) — not just combat damage
- [ ] Multiple bloodthirst instances each put their own set of counters
- [ ] Integration tests in `tests/engine/test_bloodthirst_integration.py` with 8-15 tests
- [ ] Full regression suite passes (2792+ tests, 0 failures)

## Dependencies
- None

## Priority: Medium

## Estimated Effort: S

## Notes
- **Damage tracking**: The engine needs a way to determine if an opponent was dealt damage this turn. Check GameState for any damage-dealing events recorded this turn, or add a `damage_dealt_this_turn_to_opponents: dict[str, bool]` tracking field to GameState.
- **ETB hook**: Bloodthirst fires when a creature enters the battlefield. Wire into `put_permanent_onto_battlefield()` in `zones.py`, similar to how Sunburst counters are applied there.
- **Triggered ability**: Bloodthirst is technically a triggered ability that doesn't use the stack — it's a static ability that modifies how the permanent enters the battlefield. Apply the +1/+1 counters as part of the ETB event, not as a separate stack trigger.

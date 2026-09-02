# Story: Becomes Target Trigger (CR 109.3)

## User Story
As an MTG engine developer, I want becomes-target triggers wired into the engine event flow, so that cards with "whenever this becomes the target of a spell or ability" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_becomes_target_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into stack.py's target validation when a spell/ability targets a permanent.

### Comprehensive Rules Grounding
- **CR 109.3**: "To target means to identify a legal object or player as the recipient of an action."
- Example card: *Spell Pierce* — "Whenever a spell targets you or a permanent you control, counter that spell unless its controller pays {1}."

## Acceptance Criteria
- [ ] Call `check_becomes_target_triggers()` from stack.py's target validation flow when a spell/ability targets a permanent
- [ ] Pass target perm ID and source controller to the check function
- [ ] Trigger fires BEFORE the spell resolves (during target selection) — goes on stack as a triggered ability
- [ ] Integration test: targeting fires trigger, non-targeting does NOT fire, multiple targets each fire independently

## Dependencies
- None (uses existing check function; only adds call site)

## Priority: High

## Estimated Effort: S (~0.25 day including tests)

## Notes
- **Becomes target integration**: This requires hooking into the targeting validation flow in stack.py. When `_validate_targets()` checks if a target is valid, also check for "becomes target" triggers and queue them. The trigger should fire BEFORE the spell resolves (during target selection).
- **Ward interaction**: Ward also hooks into this same flow — when a permanent with ward becomes targeted by an opponent's spell/ability. Ensure both ward and becomes-target triggers can coexist without conflicts.

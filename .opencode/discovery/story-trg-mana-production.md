# Story: Mana Production Trigger (CR 502.4)

## User Story
As an MTG engine developer, I want mana production triggers wired into the engine event flow, so that cards with "whenever you tap a land for mana" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_mana_production_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into mana.py's `add_mana()` flow after mana is added to the player's pool per CR 502.4.

### Comprehensive Rules Grounding
- **CR 502.4**: "The declare attackers step follows the beginning of combat step. During the declare attackers step, the active player declares attackers."
- **Relevant mana ability rule**: "Mana abilities are activated abilities that produce mana." When a permanent is tapped for mana, that mana enters the player's mana pool — this is the mana production event.
- **Game event**: Mana is added to a player's mana pool from a mana ability (usually tapping a land)
- **Example card**: *Fertile Ground* — "Whenever enchanted land is tapped for mana, its controller adds one mana of any color."

## Acceptance Criteria
- [ ] Call `check_mana_production_triggers(gs, source_permanent_id, controller, mana_symbols)` from mana.py's `add_mana()` flow after mana is added to the pool
- [ ] Pass the source permanent ID, controller name, and list of mana symbols produced to the check function
- [ ] Capture return value (`gs = check_mana_production_triggers(gs, ...)`)
- [ ] Integration test: tapping a land for mana fires trigger, adding mana via non-tap effect (e.g., "add {R}") fires trigger, spending mana does NOT fire mana production trigger

## Dependencies
- None

## Priority: High

## Estimated Effort: S

## Notes
- **Distinct from mana spent**: `check_mana_production_triggers()` fires when ENTERS the player's pool (tapping lands, mana abilities), while `check_mana_spent_triggers()` fires when mana LEAVES the pool (paying costs). These are wired at different points in mana.py's lifecycle.
- **Mana production patterns**: The function handles multiple trigger patterns: "whenever you tap a land for mana", "whenever a land produces mana", "whenever you add mana", and "whenever a source you control adds mana" (see `MANA_PRODUCTION_TRIGGER_PATTERNS` in triggers.py line 142).
- **Existing tests**: The function is tested in `tests/engine/test_mana_trigger.py`, `tests/engine/test_b1_missing_triggers.py`, and `tests/engine/test_triggers_expanded.py` — these should continue passing after wiring.

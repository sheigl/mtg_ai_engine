# Story: Mana Spent Trigger (CR 118.9)

## User Story
As an MTG engine developer, I want mana-spent triggers wired into the engine event flow, so that cards with "whenever you spend mana" abilities fire correctly instead of silently no-op'ing.

## Context
The `check_mana_spent_triggers()` function already exists in triggers.py but is NOT called from anywhere in the engine's event flow. This needs wiring into mana.py's `pay_cost()` flow after mana is deducted from the player's pool per CR 118.9.

### Comprehensive Rules Grounding
- **CR 118.9**: "Spending mana means removing that mana from a player's mana pool as part of paying a cost."
- **Game event**: Mana is removed from a player's mana pool to pay a cost (spell, ability, or other payment)
- **Example card**: *Kozilek's Passage* — "Whenever you spend {C} or {W}, you gain 1 life." (mana-spent triggers checking specific colors)

## Acceptance Criteria
- [ ] Call `check_mana_spent_triggers(gs, player_name)` from mana.py's `pay_cost()` flow after mana is deducted from the pool
- [ ] Pass the player name to the check function
- [ ] Capture return value (`gs = check_mana_spent_triggers(gs, player_name)`)
- [ ] Integration test: spending mana fires trigger, not spending does NOT fire, mana production (adding to pool) does NOT fire mana_spent

## Dependencies
- None

## Priority: High

## Estimated Effort: S

## Notes
- **Distinct from mana production**: `check_mana_spent_triggers()` fires when mana LEAVES the player's pool (paying costs), while `check_mana_production_triggers()` fires when mana ENTERS the pool (tapping lands). These are distinct events wired in separate locations in mana.py.
- **Existing wire review**: The `check_mana_spent_triggers()` function only takes `player_name` (does not currently pass mana symbols or amounts). Future enhancement could add mana color/type filtering for fine-grained triggers like "whenever you spend {W} or {U}".
- **Existing tests**: The function is tested in `tests/engine/test_b1_missing_triggers.py` and `tests/engine/test_triggers_expanded.py` — these should continue passing after wiring.

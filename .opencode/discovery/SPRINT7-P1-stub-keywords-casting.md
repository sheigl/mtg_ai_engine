# Story: Stub Keywords — Alternative Casting Costs (Buyback, Entwine, Overload, Miracle, Bloodthirst, Convoke)

## User Story
As an MTG engine developer, I want the six alternative-casting-cost stub keyword modules to have real `apply()` implementations with integration tests, so that spells with these keywords produce correct game state instead of silently no-op'ing.

## Context
Six keyword files exist in `mtg_engine/ability/keywords/` with detection/parsing but NOOP `apply()` methods:

1. **Buyback** (`buyback.py`) — Detection + parsing done, `apply()` returns `game_state`. Buyback {cost} is an additional cost on sorcery spells. If paid, the spell returns to its owner's hand instead of going to graveyard when it resolves. (CR 702.28)
2. **Entwine** (`entwine.py`) — Detection + parsing done, `apply()` returns `game_state`. Entwine {cost} is an additional cost on multimode spells. If paid, you choose all modes instead of just one. (CR 702.39)
3. **Overload** (`overload.py`) — Has standalone functions but no class-based apply(). Overload {cost} is an alternative cost that changes "target" to "all appropriate targets." (CR 702.91)
4. **Miracle** (`miracle.py`) — Detection + parsing done, `apply()` returns `game_state`. Miracle {cost} is an alternative cost available only when the card is drawn as the first card of the turn. (CR 702.41)
5. **Bloodthirst** (`bloodthirst.py`) — Has `create_trigger()` but `apply()` returns `game_state`. Bloodthirst N means "If an opponent was dealt combat damage this turn, this permanent enters with N +1/+1 counters." (CR 702.31)
6. **Convoke** (`convoke.py`) — Detection done, `apply()` returns `game_state`. Convoke allows tapping creatures to help pay mana costs. Each tapped creature pays {1} or one mana of its color. (CR 702.77)

All six need real `apply()` methods using pure transforms and integration into the casting/resolution flow.

## Acceptance Criteria

### Buyback (CR 702.28)
- [ ] `BuybackKeyword.apply(game_state, permanent)` implements full buyback logic: during sorcery spell casting, queues `pending_buyback_choice` for human players with buyback cost; AI auto-resolves based on mana affordability and strategic value
- [ ] If buyback is paid, when the spell resolves it returns to its owner's hand instead of going to graveyard (intercepts normal zone change)
- [ ] Buyback only applies to sorcery spells — silently no-op for other types
- [ ] Integration tests: detection, cost parsing, human choice queuing, AI auto-resolution, spell returns to hand on resolution, non-sorcery no-op

### Entwine (CR 702.39)
- [ ] `EntwineKeyword.apply(game_state, permanent)` implements full entwine logic: during multimode spell casting, queues `pending_entwine_choice` for human players with entwine cost and available modes; AI auto-resolves based on mana affordability
- [ ] If entwine is paid, all modes are chosen (not just one) — the stack object's metadata records `entwined=True` so resolution applies all mode effects
- [ ] Entwine only applies to multimode spells — silently no-op for single-mode or non-mode spells
- [ ] Integration tests: detection, cost parsing, human choice queuing, AI auto-resolution, all modes selected when entwined, single-mode spell no-op

### Overload (CR 702.91)
- [ ] `OverloadKeyword.apply(game_state, permanent)` implements full overload logic: during spell casting, queues `pending_overload_choice` for human players with overload cost; AI auto-resolves based on mana affordability and target count
- [ ] If overload is paid, the spell's targets change from "target" to "all appropriate permanents/players" — existing `get_overload_targets()` function in overload.py provides this logic
- [ ] Overload is an alternative cost (not additional) — paying it replaces the normal mana cost
- [ ] Integration tests: detection, cost parsing, human choice queuing, AI auto-resolution, all targets selected when overloaded, alternative cost behavior

### Miracle (CR 702.41)
- [ ] `MiracleKeyword.apply(game_state, card)` implements full miracle logic: when a card with miracle is drawn as the first card of the turn, queues `pending_miracle_choice` for human players; AI auto-resolves based on mana affordability and card quality
- [ ] Miracle is an alternative cost — paying it replaces the normal mana cost entirely
- [ ] First-card-of-turn tracking: use a new field `first_card_drawn_this_turn: Optional[Card]` on GameState, reset at turn start in turn_manager.py
- [ ] If miracle is not paid (or card wasn't first drawn), the card is cast normally with its mana cost
- [ ] Integration tests: detection, cost parsing, first-card-drawn tracking, human choice queuing, AI auto-resolution, non-first-card no-op, alternative cost behavior

### Bloodthirst (CR 702.31)
- [ ] `BloodthirstKeyword.apply(game_state, permanent)` implements full bloodthirst ETB logic: when the creature enters the battlefield, checks if any opponent was dealt combat damage this turn; if so, puts N +1/+1 counters on the entering creature
- [ ] Combat damage tracking: use existing `combat_damage_dealt_this_turn` field or add a new per-player flag to track whether each player dealt combat damage to an opponent this turn
- [ ] Bloodthirst triggers from ETB — wire into `_check_etb_triggers()` in triggers.py or zones.py's `put_permanent_onto_battlefield()`
- [ ] Integration tests: detection, amount parsing, ETB with combat damage gives counters, ETB without combat damage no-op, counter count matches bloodthirst value

### Convoke (CR 702.77)
- [ ] `Convoke.apply(game_state, permanent)` implements full convoke logic: during spell casting, queues `pending_convoke_choice` for human players with available creatures list; AI auto-resolves by tapping optimal creatures to cover colored and generic mana needs
- [ ] Each tapped creature reduces the total cost by {1} or one mana of that creature's color (colored mana matched first, then generic)
- [ ] Convoke is an additional cost modifier — it doesn't replace the mana cost, it supplements payment
- [ ] Integration tests: detection, human choice queuing, AI auto-resolution with colored/generic matching, tapped creatures recorded, remaining cost after convoke

### Cross-cutting requirements
- [ ] All `apply()` methods follow pure transform pattern: return new GameState via `model_copy(update={...})`, never mutate directly
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each keyword has a dedicated integration test file in `tests/engine/test_<keyword>_integration.py` with 8-15 tests covering detection, human path, AI path, edge cases, pure transform

## Dependencies
- None (independent of other Sprint 7 stories; uses existing casting/stack infrastructure)
- Miracle depends on turn_manager.py having a first-card-drawn tracking field (minor addition)

## Priority: Medium

## Estimated Effort: L (6 keywords × ~0.5 day each = 3 days)

## Notes
- **Buyback zone interception**: Buyback needs to intercept the normal spell resolution flow where the spell would go from stack -> graveyard. Reference how Escape's exile-on-leaving logic works — similar interception pattern needed at resolution time in `stack.py`.
- **Entwine mode selection**: The engine currently handles multimode spells via pending choices. Entwine modifies this by selecting ALL modes instead of one. Reference how cascade's keep/exile choice works for the pending choice pattern.
- **Overload target expansion**: Existing `get_overload_targets()` function in overload.py already provides logic to find all appropriate targets. Wire it into the casting flow so overloaded spells get expanded target lists before resolution.
- **Miracle first-card tracking**: Need a new GameState field: `first_card_drawn_this_turn: Optional[dict] = None` (card serialized as dict for Pydantic compatibility). Reset at turn start in `turn_manager.py`. Check during draw step to set this field, then check during casting to offer miracle option.
- **Bloodthirst combat damage tracking**: Need a per-player flag like `dealt_combat_damage_to_opponent_this_turn: bool` on PlayerState or GameState. Set during combat damage assignment in `combat/core.py`. Reset at turn end. Bloodthirst ETB checks this flag before applying counters.
- **Convoke mana matching**: Convoke's color matching is nuanced — each creature can pay {1} OR one of its colors. The AI should prioritize tapping creatures whose colors match unmet colored costs, then use remaining creatures for generic. Reference how `parse_mana_cost()` and `can_pay_cost()` work in `engine/mana.py`.

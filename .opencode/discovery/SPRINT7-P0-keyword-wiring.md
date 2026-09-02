# Story: Wire Trigger-Based Keyword Modules to Use Their Own apply() Methods (Sprint 7 P0)

## User Story
As an MTG engine developer, I want each keyword module to own its full logic via proper `apply()` methods instead of having inline implementations scattered across triggers.py, stack.py, zones.py, and turn_manager.py, so that the codebase follows a consistent architecture where keyword modules are self-contained and the engine calls into them rather than containing their logic.

## Context
Six keyword modules currently have NOOP `apply()` methods because their real logic lives inline in engine files or in separate engine helper modules:

1. **Afterlife** (`afterlife.py`) — death trigger queuing is in `_queue_death_triggers()` (triggers.py lines 357-369) + resolution in `_resolve_afterlife_trigger()` (stack.py lines 780-796)
2. **Undying** (`undying.py`) — same pattern: queuing in triggers.py lines 371-389, resolution in stack.py lines 799-846
3. **Persist** (`persist.py`) — same pattern: queuing in triggers.py lines 391+, resolution in stack.py lines 849-886
4. **Evoke** (`evoke.py` keyword module) — real logic lives in `engine/evoke.py` (`queue_evoke_sacrifice()`, `resolve_evoke_sacrifice()`), called from stack.py resolve_top() and turn_manager.py end step
5. **Morph** (`morph.py` keyword module) — real logic lives in `engine/morph.py` (`apply_morph_turn_face_up()`), used via zones.py face-down casting path
6. **Suspend** (`suspend.py` keyword module) — time counter removal and auto-cast live inline in turn_manager.py upkeep (lines 168-212) + helper functions in `engine/suspend.py`

This creates a split-brain architecture where the keyword modules have detection/parsing but no real behavior, while the engine files contain the actual game logic. The goal is to consolidate so each module owns its full lifecycle via `apply()` methods that follow the pure transform pattern (`model_copy(update={...})`).

## Acceptance Criteria

### Afterlife (CR 702.108)
- [ ] `AfterlifeKeyword.apply(game_state, stack_obj)` implements the full token creation logic currently in `_resolve_afterlife_trigger()` (stack.py lines 780-796): creates N 0/0 white Spirit tokens with afterlife 1 using `_create_token_with_pt_and_keywords()`
- [ ] `AfterlifeKeyword.queue_death_trigger(event, game_state)` implements the queuing logic currently in `_queue_death_triggers()` (triggers.py lines 357-369): parses count from oracle, creates PendingTrigger with trigger_data containing count
- [ ] triggers.py's `_queue_death_triggers()` calls `AfterlifeKeyword.queue_death_trigger()` instead of inline afterlife logic
- [ ] stack.py's `_resolve_triggered_effect()` dispatches to `AfterlifeKeyword().apply(game_state, stack_obj)` for trigger_type="afterlife"
- [ ] All 9 existing tests in `tests/engine/test_afterlife_integration.py` pass with zero regressions

### Undying (CR 702.51)
- [ ] `UndyingKeyword.apply(game_state, stack_obj)` implements the full graveyard-return + counter logic currently in `_resolve_undying_trigger()` (stack.py lines 799-846): finds card in graveyard, removes it, puts on battlefield with P+T +1/+1 counters
- [ ] `UndyingKeyword.queue_death_trigger(event, game_state)` implements the queuing logic currently in triggers.py lines 371-389: counter guard (no +1/+1), creates PendingTrigger with trigger_data containing power/toughness
- [ ] triggers.py's `_queue_death_triggers()` calls `UndyingKeyword.queue_death_trigger()` instead of inline undying logic
- [ ] stack.py's `_resolve_triggered_effect()` dispatches to `UndyingKeyword().apply(game_state, stack_obj)` for trigger_type="undying"
- [ ] All 16 existing tests in `tests/engine/test_undying_integration.py` pass with zero regressions

### Persist (CR 702.61)
- [ ] `PersistKeyword.apply(game_state, stack_obj)` implements the full graveyard-return + counter logic currently in `_resolve_persist_trigger()` (stack.py lines 849-886): finds card in graveyard, removes it, puts on battlefield with one -1/-1 counter
- [ ] `PersistKeyword.queue_death_trigger(event, game_state)` implements the queuing logic currently in triggers.py lines 391+: counter guard (no -1/-1), creates PendingTrigger
- [ ] triggers.py's `_queue_death_triggers()` calls `PersistKeyword.queue_death_trigger()` instead of inline persist logic
- [ ] stack.py's `_resolve_triggered_effect()` dispatches to `PersistKeyword().apply(game_state, stack_obj)` for trigger_type="persist"
- [ ] All 11 existing tests in `tests/engine/test_persist_integration.py` pass with zero regressions

### Evoke (CR 702.45)
- [ ] `EvokeKeyword.apply(game_state, permanent_id, player_name, card_name)` implements the queue-sacrifice logic currently in `engine/evoke.py::queue_evoke_sacrifice()`: sets `pending_evoke_sacrifice` on GameState
- [ ] `EvokeKeyword.resolve_sacrifice(game_state)` implements the sacrifice logic currently in `engine/evoke.py::resolve_evoke_sacrifice()`: moves permanent to graveyard, clears pending state
- [ ] stack.py's resolve_top() calls `EvokeKeyword.apply()` instead of importing from `engine/evoke.py`
- [ ] turn_manager.py's end step calls `EvokeKeyword.resolve_sacrifice()` instead of importing from `engine/evoke.py`
- [ ] `engine/evoke.py` is either deleted or reduced to thin re-export wrappers that delegate to the keyword module (to maintain backward compatibility)
- [ ] All existing tests in `tests/engine/test_evoke_integration.py` pass with zero regressions

### Morph (CR 702.37)
- [ ] `MorphKeyword.apply_turn_face_up(game_state, permanent_id)` implements the face-up logic currently in `engine/morph.py::apply_morph_turn_face_up()`: validates face-down state, parses morph cost, deducts mana from pool, clears is_face_down and resets P/T bonuses
- [ ] stack.py/zones.py casting path calls into `MorphKeyword` for face-down creation when morph alternative cost is used
- [ ] API router calls `MorphKeyword.apply_turn_face_up()` instead of importing from `engine/morph.py`
- [ ] `engine/morph.py` is either deleted or reduced to thin re-export wrappers that delegate to the keyword module (to maintain backward compatibility)
- [ ] All existing tests in `tests/engine/test_morph_integration.py` pass with zero regressions

### Suspend (CR 702.65)
- [ ] `SuspendKeyword.remove_time_counter(game_state, player_name)` implements the time counter removal logic currently split between turn_manager.py upkeep (lines 168-212) and `engine/suspend.py::remove_time_counter()`: decrements counters on suspended cards, marks ready-to-cast when last counter removed
- [ ] `SuspendKeyword.auto_cast_ready(game_state)` implements the auto-cast logic currently in turn_manager.py upkeep (lines 180-203): for each suspend_ready card, calls cast_spell with from_suspended=True, grants haste on creatures
- [ ] turn_manager.py's upkeep step calls `SuspendKeyword.remove_time_counter()` and `SuspendKeyword.auto_cast_ready()` instead of inline logic
- [ ] stack.py's cast_spell path uses `SuspendKeyword` for suspend-related metadata (from_suspended flag)
- [ ] `engine/suspend.py` is either deleted or reduced to thin re-export wrappers that delegate to the keyword module (to maintain backward compatibility)
- [ ] All existing tests in `tests/engine/test_suspend_integration.py` pass with zero regressions

### Cross-cutting requirements
- [ ] All `apply()` methods follow pure transform pattern: return new GameState via `model_copy(update={...})`, never mutate directly
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] No behavioral changes — this is a refactoring-only story. All existing integration tests pass unchanged
- [ ] Inline helper functions in triggers.py and stack.py (`_resolve_afterlife_trigger`, `_resolve_undying_trigger`, `_resolve_persist_trigger`) are removed or reduced to thin dispatchers that call into keyword modules

## Dependencies
- None (independent refactoring; no new features required)

## Priority: High

## Notes
- **Refactoring strategy**: For each module, the approach is: (1) move inline logic from engine files into the keyword module's `apply()` method, (2) update call sites in triggers.py/stack.py/zones.py/turn_manager.py to import and call the keyword module instead of inline code, (3) verify all existing tests pass, (4) remove or deprecate the old inline functions. Work on one module at a time to isolate regressions.
- **Afterlife/Undying/Persist shared pattern**: These three share the same architecture — death trigger queuing in triggers.py + stack resolution in stack.py. Consider extracting a common `DeathTriggerKeyword` base class or helper if the patterns converge, but this is optional and not required for this story.
- **Evoke/Morph/Suspend engine files**: `engine/evoke.py`, `engine/morph.py`, `engine/suspend.py` are standalone modules that duplicate functionality from their keyword module counterparts in `ability/keywords/`. The refactoring should consolidate into the keyword module as the single source of truth. If other parts of the codebase import from `engine/*.py`, those imports can be redirected via re-export wrappers to avoid breaking changes.
- **Suspend is most complex**: Suspend's logic spans turn_manager.py (upkeep time counter removal + auto-cast), engine/suspend.py (helper functions), and stack.py (from_suspended flag in cast_spell). The keyword module needs methods for: suspend a card from hand, remove time counters at upkeep, auto-cast when ready, and grant haste on suspended creatures.
- **Token guard for death triggers**: CR 704.5d token guard is currently in `_queue_death_triggers()` (triggers.py line 335). This guard must be preserved when moving logic into keyword modules — either keep the guard at the call site or have each keyword module's `queue_death_trigger()` accept an `is_token` parameter.

# Story: P0 Missing Triggers — Countered and Investigated

## User Story
As an MTG engine developer, I want the "countered" and "investigated" trigger patterns implemented with regex detection, check functions, and engine wiring, so that cards that respond to countered spells or investigate actions produce correct game state instead of silently no-op'ing.

## Context
Two trigger categories are completely missing from triggers.py (no regex patterns, no check functions) but are essential for modern gameplay:

1. **Countered** — "Whenever a spell you control is countered" / "Whenever a spell is countered" — Needed for any card that responds to counterspells. Examples: [[Dark Ritual]] with [[Spell Pierce]], [[Grapeshot]], [[Deflecting Swat]]. Without this, any interaction involving "whenever a spell is countered" silently fails.

2. **Investigated** — "Whenever you investigate" / "Whenever a land is investigated" — Needed for clue token triggers. Examples: [[Psychic Intrusion]], [[Investigate]] itself with follow-up effects, [[The Detective's Trail]]. Without this, entire clue-based archetypes (common in Modern/Legacy) are broken.

## Acceptance Criteria

### Countered Trigger
- [x] Add `COUNTERED_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever (?:a|an) spell .*? is countered", "whenever (?:this|~) is countered", "whenever a spell you control is countered" (triggers.py:228-237; idx2 broadened to also match the bare "a spell is countered")
- [x] Create `check_countered_triggers(game_state, countered_stack_obj)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="countered"` (idx1 explicit you-control filter, idx0 self-referential name guard)
- [x] Wire into stack.py's counter resolution: when a spell on the stack is countered (e.g., via `_apply_counter()` or counterspell effects), call `check_countered_triggers()` BEFORE removing the spell from the stack, so triggered abilities see it
- [x] Stack resolution: `_resolve_triggered_effect()` dispatches "countered" triggers through existing effect text resolution pipeline
- [x] Integration tests in `tests/engine/test_countered_trigger_integration.py`: countered spell fires trigger, non-counter removal does NOT fire countered trigger, self-referential guard ("whenever this is countered"), multiple permanents with countered triggers all fire (8 tests)

### Investigated Trigger
- [x] Add `INVESTIGATED_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever you investigate", "whenever a land is investigated", "whenever (?:a|an) clue token enters" (delivered with approved deltas: exactly 2 action patterns — token-ETB phrasings owned by the token-trigger category per the test-round-1 pattern-ownership split; "land is investigated" intentionally out of scope)
- [x] Create `check_investigated_triggers(game_state, player_name)` function that iterates battlefield permanents and queues matching PendingTriggers with `trigger_type="investigated"` (triggers.py:1548-1619; idx0 you filter)
- [x] Wire into token creation flow: when an artifact token representing a clue is created (via "investigate" action in stack.py's `_apply_single_effect_text()`), call `check_investigated_triggers()` after the token enters the battlefield (via the `_investigate()` helper, stack.py:1346-1388, reachable from both effect paths)
- [x] Stack resolution: `_resolve_triggered_effect()` dispatches "investigated" triggers through existing effect text resolution pipeline
- [x] Integration tests in `tests/engine/test_investigated_trigger_integration.py`: investigate fires trigger, non-investigate token creation does NOT fire, multiple permanents with investigated triggers all fire (10 tests, incl. exactly-once dedupe)

### Cross-cutting requirements
- [x] All new trigger patterns follow the existing pattern in triggers.py: regex list + dedicated check function that returns new GameState via `model_copy(update={"pending_triggers": ...})`
- [x] Both new trigger types are dispatched through `_resolve_triggered_effect()` in stack.py using the effect description text resolution pipeline
- [x] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected) (implementer-reported 2816/0/3/13 — basis for Test ✅, arithmetically verified in review r3; optional independent re-run documented in `.opencode/pipeline/status.md`)
- [x] Each trigger type has at least 4 integration tests covering: positive fire case, negative no-fire case, self-referential guard, multiple permanents (countered 8 + investigated 10)

## Dependencies
- None (independent of other stories; uses existing trigger infrastructure in triggers.py and stack.py)

## Priority: High

## Estimated Effort: M (~1 day for both triggers including wiring and tests)

## Notes
- **Countered trigger timing**: The countered event must fire BEFORE the spell is removed from the stack. Reference how death triggers work — zone change notification fires before the permanent is fully removed. Similarly, counter resolution should emit the triggered event, then remove the spell. This ensures "whenever this spell is countered" self-referential triggers can still access the source card's data.
- **Investigate token detection**: The investigate action creates an artifact token with type "Clue". Detection should check for both explicit "investigate" keyword in oracle text AND the creation of a Clue-type artifact token, as some cards create clue tokens without using the word "investigate".
- **Counter resolution integration**: Counter effects are currently handled via `_apply_counter()` in stack.py. The wiring point is after the counter effect takes place (spell marked for exile/removal) but before the spell object is actually removed from `game_state.stack`.

# Story: Missing Trigger Patterns (9 Highest-Value)

## User Story
As an MTG engine developer, I want the 9 highest-value missing trigger patterns added to `triggers.py`, so that cards with these triggered abilities fire correctly instead of silently no-op'ing.

## Context
The existing `triggers.py` has 50+ trigger pattern categories (cast, attack, block, upkeep, death, draw, damage, ETB, LTB, etc.), but ~104 of Forge's 159 trigger types are still missing. The 9 highest-value patterns based on card frequency and gameplay impact:

1. **sacrificed** — "Whenever a creature is sacrificed" / "Whenever you sacrifice a permanent"
2. **countered** — "Whenever a spell you control is countered"
3. **becomes_target** — "Whenever this becomes the target of a spell or ability"
4. **fight** — "Whenever this creature fights another creature"
5. **investigated** — "Whenever a land is investigated" (creates artifact token)
6. **searched_library** — "Whenever you search your library"
7. **tapped_for_mana** — "Whenever a land produces mana" / "Whenever {T} is paid"
8. **attached/unattach** — "Whenever this becomes attached to a creature" / "Whenever this unattaches"
9. **transformed** — "Whenever this transforms" (MDFC transform)

Each trigger needs: regex detection patterns in triggers.py, proper event queuing via `PendingTrigger`, and resolution hooks in stack.py's `_resolve_triggered_effect()`.

## Acceptance Criteria

### Sacrificed Trigger
- [ ] Add `SACRIFICE_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever (?:a|an) (.*?) is sacrificed", "whenever you sacrifice (?:a|an) .*?", "whenever (?:this|~) is sacrificed"
- [ ] Wire into `_on_zone_change()` in triggers.py: when a permanent moves from battlefield to graveyard via sacrifice action, check all battlefield permanents for sacrifice trigger patterns and queue matching `PendingTrigger`s with `trigger_type="sacrificed"`
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "sacrificed" triggers through existing effect text resolution pipeline
- [ ] Integration tests in `tests/engine/test_triggers_integration.py`: sacrifice fires trigger, non-sacrifice death does NOT fire sacrifice trigger, self-referential guard

### Countered Trigger
- [ ] Add `COUNTERED_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever (?:a|an) spell .*? is countered", "whenever (?:this|~) is countered"
- [ ] Wire into stack resolution: when a spell on the stack is countered, check all permanents for countered trigger patterns and queue matching `PendingTrigger`s with `trigger_type="countered"`
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "countered" triggers through existing effect text resolution pipeline
- [ ] Integration tests: countered spell fires trigger, non-counter removal does NOT fire countered trigger

### Becomes Target Trigger
- [ ] Add `BECOMES_TARGET_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever (?:this|~) becomes the target", "whenever (?:a|an) (.*?) becomes targeted"
- [ ] Wire into targeting flow: when a spell/ability targets a permanent, check if that permanent has "becomes target" trigger patterns and queue `PendingTrigger` with `trigger_type="becomes_target"` including source info
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "becomes_target" triggers through existing effect text resolution pipeline
- [ ] Integration tests: targeting fires trigger, non-targeting does NOT fire, multiple targets each fire independently

### Fight Trigger
- [ ] Add `FIGHT_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever (?:this|~) fights", "whenever a creature fights"
- [ ] Wire into fight resolution in stack.py's `_apply_fight()`: when two creatures fight, check both for fight trigger patterns and queue `PendingTrigger`s with `trigger_type="fight"` including the other creature as target data
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "fight" triggers through existing effect text resolution pipeline
- [ ] Integration tests: fight fires trigger on both creatures, non-fight damage does NOT fire

### Investigated Trigger
- [ ] Add `INVESTIGATED_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever a land is investigated", "whenever you investigate"
- [ ] Wire into token creation flow: when an artifact token representing a clue is created (investigate action), check all permanents for investigated trigger patterns and queue `PendingTrigger`s with `trigger_type="investigated"`
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "investigated" triggers through existing effect text resolution pipeline
- [ ] Integration tests: investigate fires trigger, non-investigate token creation does NOT fire

### Searched Library Trigger
- [ ] Add `SEARCHED_LIBRARY_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever you search your library", "whenever a player searches"
- [ ] Wire into library search flow: when any effect searches the library (tutor, transmute, etc.), check all permanents for searched trigger patterns and queue `PendingTrigger`s with `trigger_type="searched_library"`
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "searched_library" triggers through existing effect text resolution pipeline
- [ ] Integration tests: library search fires trigger, non-search effects do NOT fire

### Tapped For Mana Trigger
- [ ] Add `TAPPED_FOR_MANA_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever a land produces mana", "whenever {T} is paid"
- [ ] Wire into mana production flow: when a land's tap ability adds mana to pool, check all permanents for mana trigger patterns and queue `PendingTrigger`s with `trigger_type="tapped_for_mana"` including mana type/color data
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "tapped_for_mana" triggers through existing effect text resolution pipeline
- [ ] Integration tests: land tap fires trigger, non-mana tap does NOT fire

### Attached/Unattach Trigger
- [ ] Add `ATTACH_TRIGGER_PATTERNS` and `UNATTACH_TRIGGER_PATTERNS` lists to triggers.py with regexes matching: "whenever this becomes attached", "whenever this unattaches"
- [ ] Wire into equip/attachment flow: when a permanent's `attached_to` field changes, check for attach/unattach trigger patterns and queue appropriate `PendingTrigger`s with `trigger_type="attached"` or `"unattached"`
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches both trigger types through existing effect text resolution pipeline
- [ ] Integration tests: equip fires attached trigger, unequip/death fires unattach trigger

### Transformed Trigger
- [ ] Add `TRANSFORM_TRIGGER_PATTERNS` list to triggers.py with regexes matching: "whenever this transforms", "when (?:this|~) transforms"
- [ ] Wire into MDFC transform flow in zones.py's `_transform_mdfc()`: when a permanent transforms, check for transform trigger patterns and queue `PendingTrigger`s with `trigger_type="transformed"`
- [ ] Stack resolution: `_resolve_triggered_effect()` dispatches "transformed" triggers through existing effect text resolution pipeline
- [ ] Integration tests: MDFC transform fires trigger, non-MDFC effects do NOT fire

### Cross-cutting requirements
- [ ] All new trigger patterns follow the existing pattern in triggers.py: regex list + dedicated check function (e.g., `check_sacrifice_triggers()`) that iterates battlefield permanents and queues matching PendingTriggers
- [ ] All new trigger types are dispatched through `_resolve_triggered_effect()` in stack.py using the effect description text resolution pipeline
- [ ] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [ ] Each trigger type has at least 3 integration tests covering: positive fire case, negative no-fire case, self-referential guard

## Dependencies
- None (independent of other Sprint 7 stories; uses existing trigger infrastructure in triggers.py and stack.py)

## Priority: Medium

## Estimated Effort: L (9 triggers × ~0.3 day each = 2.5 days)

## Notes
- **Sacrifice detection**: The key challenge is distinguishing sacrifice from other death events. Reference how `_queue_death_triggers()` already handles this — the zone change event includes a `reason` field that can be "sacrifice", "destroy", etc. Add a parallel check for sacrifice-specific triggers.
- **Countered trigger timing**: Counterspell resolution in stack.py needs to emit the countered event BEFORE removing the spell from the stack, so triggered abilities see it on the stack. Reference how death triggers work — zone change notification fires before the permanent is fully removed.
- **Becomes target integration**: This requires hooking into the targeting validation flow. When `_validate_targets()` or similar functions check if a target is valid, also check for "becomes target" triggers and queue them. Consider adding the trigger queuing to `stack.py`'s target selection code.
- **Fight resolution wiring**: Fight is already partially implemented in stack.py's `_apply_fight()`. The trigger just needs to be queued at the same point where damage is dealt during fight resolution.
- **Tapped for mana complexity**: Mana production happens outside the normal stack flow (it goes directly into the mana pool). Triggers that fire on mana production need special handling — they go on the stack AFTER mana is added but BEFORE priority is granted. Reference how "mana ability" triggers work in CR 605.
- **Transform trigger wiring**: MDFC transform logic already exists in zones.py's `_transform_mdfc()`. The trigger just needs to be queued at the same point where the permanent flips sides.

## Implementation Status Audit (2026-08-20, code review agent)
This story file predates 7-2 (13 dead-code trigger wiring) and 7-3 (countered + investigated). Status of the 9 patterns as of the audit, verified against `triggers.py` (2147 lines):

| # | Pattern | Status (2026-08-20) |
|---|---------|--------------------|
| 1 | sacrificed | ✅ 7-2 — `check_sacrifice_triggers` (triggers.py:706), wired via `_sacrifice_permanent` (zones.py:826) |
| 2 | countered | ✅ 7-3 — `check_countered_triggers` (triggers.py:1478), `COUNTERED_TRIGGER_PATTERNS` (228-237) |
| 3 | becomes_target | ✅ 7-2 — `check_becomes_target_triggers` (triggers.py:1030), `BECOMES_TARGET_TRIGGER_PATTERNS` (198-201) |
| 4 | fight | ✅ 7-2 — `check_fight_triggers` (triggers.py:876) |
| 5 | investigated | ✅ 7-3 — `check_investigated_triggers` (triggers.py:1548), `INVESTIGATED_TRIGGER_PATTERNS` (249-254). Note: the "whenever a land is investigated" phrasing was an approved 7-3 scope delta (out of scope; see implementation.md) |
| 6 | searched_library | ✅ 7-2/TRG-20 — implemented within the tutor category: `TUTOR_TRIGGER_PATTERNS` (triggers.py:192-195) handled by `check_tutor_triggers` (triggers.py:992, incl. TRG-20 Fix-5 "you" controller filter) |
| 7 | tapped_for_mana | ✅ 7-2 — implemented as `mana_production`: `check_mana_production_triggers` (triggers.py:1657), wired at `resolve_land_mana_ability()` (mana.py) |
| 8 | attached/unattach | ⚠️ Partial — attach ✅ 7-2: `check_attach_triggers` (triggers.py:1092); **unattach path is latent (no call site)** — tracked in `SPRINT7-P1-trigger-fidelity-minors.md` item 2 and `story-trg-unattach.md` |
| 9 | transformed | ✅ 7-2 — `check_transformed_triggers` (triggers.py:953), `TRANSFORMED_TRIGGER_PATTERNS` (186-189), wired in the daynight.py transition logic |

**Recommendation:** close this story as **superseded** by 7-2 + 7-3. The only remaining work (the unattach call site) is already tracked in `SPRINT7-P1-trigger-fidelity-minors.md` item 2. If it is ever reopened, rescope to that single item — do NOT re-implement patterns 1-7 or 9. The AC baseline "2792+ regression tests" is a historical floor; the current suite baseline is 2816 passed / 3 skipped / 13 xfailed (post-7-3).

# Pipeline Status

| Feature | Dev Status | QA Status | Notes |
|---------|-----------|-----------|-------|
| MON-01: The Monarch | ✅ Complete | ✅ Passed | 60 tests pass, 2027 total — monarch tracking, combat transfer, end step draw |
| CMD-01: Commander Rules | ✅ Complete | ✅ Passed | 66 tests pass, 0 regressions — tax, damage loss, zone replacement, partners |
| BUG-26: Spree mechanic completion | ✅ Complete | ✅ Passed | All 13 tests pass, 0 regressions |
| 034-etb-choices tests | ✅ Complete | ✅ Passed | 68 tests (52 pass, 3 skip, 13 xfail), no regressions |
| Landfall verification (BUG-23) | ✅ Complete | ✅ Passed | Verified — 3 landfall tests pass, 522 ability tests pass |

## Active Work
CMD-01 and MON-01 complete. Next: VEN-01 Venture into the Dungeon or PRO-01 Proliferate (Sprint 1).

## 038-Gap-Analysis Backlog

### Metrics Summary
| Category | Items | Covered | Gap | Priority |
|----------|-------|---------|-----|----------|
| **A: Keywords** | 186 | 17 | **169** | P3 |
| **B: Trigger types** | 159 | 55 | **104** | P2 |
| **C: Game mechanics** | 10 | ~3 | **7** | P2 |
| **D: Game formats** | 5 | 0 | **5** | P3 |
| **E: API features** | 6 | 0 | **6** | P3 |

### Sprint 1: Core Game Mechanics (P2)
| ID | Feature | Status | Dev | QA | Dependencies |
|----|---------|--------|-----|----|-------------|
| CMD-01 | Commander Rules | ✅ Complete | ✅ Done | ✅ Passed | None |
| MON-01 | The Monarch | ✅ Complete | ✅ Done | ✅ Passed | None |
| VEN-01 | Venture into the Dungeon | ⏳ Pending | — | — | None |
| PRO-01 | Proliferate System | ⏳ Pending | — | — | None |

### Sprint 2: Advanced Mechanics (P2)
| ID | Feature | Status | Dev | QA | Dependencies |
|----|---------|--------|-----|----|-------------|
| DNG-01 | Day/Night Cycle | ⏳ Pending | — | — | Turn manager hooks |
| INT-01 | The Initiative | ⏳ Pending | — | — | MON-01, VEN-01 |
| COM-01 | Companion Mechanic | ⏳ Pending | — | — | Sideboard zone |

### Sprint 3: Trigger & Keyword Coverage (P2)
| ID | Feature | Status | Dev | QA | Dependencies |
|----|---------|--------|-----|----|-------------|
| TRG-20 | Top 10 Missing Trigger Categories | ⏳ Pending | — | — | None |
| KW-16..30 | Top 15 High-Value Keywords | ⏳ Pending | — | — | KW-01 (base.py) |

### Sprint 4: Format Validation (P3)
| ID | Feature | Status | Dev | QA | Dependencies |
|----|---------|--------|-----|----|-------------|
| FMT-01 | Format Rules Engine | ⏳ Pending | — | — | Card data (Scryfall) |

### Sprint 5: Application Features (P3)
| ID | Feature | Status | Dev | QA | Dependencies |
|----|---------|--------|-----|----|-------------|
| APP-01 | Card Search API | ⏳ Pending | — | — | Scryfall data loaded |
| APP-02 | Deck Building AI | ⏳ Pending | — | — | FMT-01 |
| APP-03 | Game Replay | ⏳ Pending | — | — | Transcript system |
| APP-04 | Spectate / WebSocket | ⏳ Pending | — | — | FastAPI WebSocket |
| APP-05 | Draft / Sealed Simulation | ⏳ Pending | — | — | APP-02 |
| APP-06 | Player Stats / ELO | ⏳ Pending | — | — | Game recording |

### Pending Items (Not yet in sprints)
| Category | Items | Status |
|----------|-------|--------|
| **A: Keywords (169 remaining)** | Affinity, Amplify, Ascend, Bestow, Blitz, Bloodthirst, Bushido, Buyback, Champion, Changeling, Cipher, Companion, Crew, Cumulative Upkeep, Cycling, Dash, Daybound/Nightbound, Devour, Disturb, Embalm, Entwine, Epic, Equip, Escalate, Eternalize, Exalted, Exploit, Extort, Fabricate, Fading, Frenzy, Graft, Gravestorm, Haunt, Hideaway, Horsemanship, Ingest, Landwalk, Living Weapon, Melee, Mentor, Modular, Myriad, Ninjutsu, Outlast, Overload, Partner, Provoke, Prowl, Rampage, Ravenous, Recover, Reconfigure, Reinforce, Renown, Replicate, Retrace, Riot, Ripple, Soulbond, Soulshift, Splice, Spree, Squad, Station, Storm, Strive, Sunburst, Surge, Training, Undaunted, Undying, Ward, and many more | ⏳ Pending |
| **B: Trigger types (104 remaining)** | abandoned, attached/unattach, loses_game, become_monarch/initiative, becomes_target, class_level_gained, committed_crime, completed_dungeon, countered, day_time_changes, fight, flipped_coin, investigated, mentored, mutates, proliferated, ring_tempts_you, rolled_die, sacrificed, tapped_for_mana, token_created, transformed, tutored/searched_library, voted, and many more | ⏳ Pending |
| **C: Game mechanics (7 remaining)** | Commander Rules, Day/Night Cycle, The Monarch, The Initiative, Venture/Dungeon, Proliferate, Companion | ⏳ Pending |
| **D: Game formats (5 remaining)** | Format validation, Banned/restricted lists, Multiplayer rules, Sideboarding, Match system | ⏳ Pending |
| **E: API features (6 remaining)** | Card search, Deck building AI, Game replay, Draft/sealed, Spectator, Player stats | ⏳ Pending |

## Files Modified
- `mtg_engine/engine/stack.py` - Add missing effect patterns to `_apply_single_effect_text()`

## Developer Task: BUG-26 Spree Effect Resolution
**Context**: Spree cards (e.g., Insatiable Avarice) have optional additional costs with effects. The mode parsing and choice queuing work, but `_apply_single_effect_text()` lacks patterns for Spree-specific effects.

**Current state**:
- `stack.py` lines 161-179: Mode detection ✅ (parses `+ {cost} — effect`)
- `game.py` lines 1512-1558: Choice handling ✅ (spree_select action)
- `stack.py` lines 823-839: Resolution calls `_apply_single_effect_text()` ⚠️

**Gap**: `_apply_single_effect_text()` (line 745) has no patterns for:
1. `"search your library for a card, then shuffle and put that card on top"` → tutor effect
2. `"target player draws three cards and loses 3 life"` → combined draw + lose life

**Required changes**:
1. Add pattern for "search your library...put {card} on top" (tutor) in `_apply_single_effect_text()`
2. Split multi-clause effects like "draw N cards and lose X life" into separate sub-effects
3. Handle "target player draws N cards" (opponent draw, not caster)
4. Ensure patterns match the exact text from Spree mode parsing

**Test file**: Create `tests/engine/test_spree.py` with Insatiable Avarice example

**Example card text to support**:
```
Spree — (Choose one or more additional costs.)
+ {2} — Search your library for a card, then shuffle and put that card on top.
+ {B}{B} — Target player draws three cards and loses 3 life.
```

**Key patterns needed in `_apply_single_effect_text()`**:
- `r"search your library.*?put (?:that )?(?:card )?(?:on top|into your hand)"` → tutor effect
- `r"(?:target player\s+)?draws?\s+(\d+)\s+cards?.*?loses?\s+(\d+)\s+life"` → draw + lose life
- Handle "and" as clause separator for combined effects

**Note**: The existing `_apply_spell_effect()` already handles spree at lines 823-839 by calling `_apply_single_effect_text()`. Just need to add patterns.

## QA Checklist for BUG-26
1. Test Insatiable Avarice cast with Spree mode selection
2. Verify "search library...put on top" tutor effect resolves correctly
3. Verify "target player draws N cards and loses X life" combined effect resolves
4. Verify multiple spree modes can be selected and all resolve
5. Run full test suite to ensure no regressions

## Implementation Notes for Developer
- Read `mtg_engine/engine/stack.py` lines 745-811 for current `_apply_single_effect_text()` patterns
- The effect text from Spree modes is already parsed and stored in `pending_spree_effects`
- Each spree effect string looks like: "Search your library for a card, then shuffle and put that card on top." or "Target player draws three cards and loses 3 life."
- Add new patterns to the existing list in `_apply_single_effect_text()` (around line 750)
- For combined effects with "and", consider splitting into sub-effects before pattern matching
- Create test file `tests/engine/test_spree.py` that:
  - Creates an Insatiable Avarice card with Spree modes
  - Simulates casting it and selecting spree modes
  - Verifies effects resolve correctly (library search, draw+lose life)

## Files to Read Before Starting
1. `mtg_engine/engine/stack.py` lines 745-811 — current `_apply_single_effect_text()` patterns
2. `mtg_engine/engine/stack.py` lines 823-839 — spree resolution call site
3. `specs/036-spree/plan.md` — full spec for reference

## Acceptance Criteria
- [x] `_apply_single_effect_text()` has patterns for Spree tutor and combined effects
- [x] Insatiable Avarice spree modes resolve correctly when selected
- [x] New test file `tests/engine/test_spree.py` passes all tests (13/13)
- [x] No regressions in existing test suite (345 engine tests pass, 1656 total tests pass)

## Status
✅ ALL COMPLETE — Pipeline cleared. All features verified and shipped.

## Pipeline Progress
- BUG-26 Spree: ✅ Complete (verified)
- BUG-23 Landfall: ✅ Complete (verified)
- 034-etb-choices tests: ✅ Complete (verified)

## Current Blockers
None — All features complete.

## Summary for Human Review
1. **BUG-26 Spree** (HIGH) — ✅ Complete — 13/13 tests pass, 345 engine tests pass
2. **BUG-23 Landfall** (MEDIUM) — ✅ Verified — 3 landfall tests pass, 522 ability tests pass
3. **034-etb-choices tests** (HIGH) — ✅ Complete — 68 tests (52 pass, 3 skip, 13 xfail), 1931 total tests pass

## Status
All pipeline items complete. No remaining work.

## Risk Assessment
- All risks resolved. No blockers.

---
---

## Completed Work Log

### BUG-26 Spree (Completed 2026-06-13)
- Added `_lose_life` and `_tutor_to_top` helpers to `stack.py`
- Added Spree patterns to `_apply_single_effect_text()`
- Created `tests/engine/test_spree.py` (13 tests)
- Verified: 13/13 pass, 345 engine tests pass, 0 regressions

### BUG-23 Landfall (Verified 2026-06-13)
- Verified existing landfall implementation
- All 3 landfall tests pass, 522 ability tests pass, 0 regressions

### 034-etb-choices (Completed 2026-06-13)
- Architected test plan covering 5 test files
- Implemented: `test_etb_detection.py` (18 tests), `test_etb_ai.py` (22 tests), `test_etb_integration.py` (10 tests), `test_etb_choices.py` (10 tests), `test_etb_gameplay.py` (5 tests)
- Verified: 68 tests (52 pass, 3 skip, 13 xfail), 1931 total tests pass, 0 regressions

## Pipeline Status Summary
```
BUG-26 Spree: ✅ COMPLETE
BUG-23 Landfall: ✅ COMPLETE
034-etb-choices tests: ✅ COMPLETE
```

All pipeline items complete. No remaining work.

---

## Changelog
- 2026-06-13: Created pipeline, assigned BUG-26 Spree to Developer
- 2026-06-13: Identified 3 remaining items (BUG-26, 034-etb-choices tests, landfall)
- 2026-06-13: BUG-26 Spree assigned to Developer for effect pattern completion
- 2026-06-13: **BUG-26 Implementation Complete** — Added `_lose_life` and `_tutor_to_top` helpers, Spree patterns in `_apply_single_effect_text()`, and `tests/engine/test_spree.py` test file
- 2026-06-13: Updated AGENTS.md with BUG-26 completion notes
- 2026-06-13: Status updated to reflect implementation complete, awaiting verification
- 2026-06-13: **BUG-23 Landfall Verified** — All 3 landfall tests pass, 522 ability tests pass, 0 regressions
- 2026-06-13: Pipeline status updated: BUG-26 and BUG-23 both complete, 034-etb-choices next
- 2026-06-13: **034-etb-choices Complete** — 68 tests implemented (52 pass, 3 skip, 13 xfail), 1931 total tests pass, 0 regressions

---

## Notes for Future Reference
- All main TASK items (TASK-01 through TASK-28) in tasks.md are marked complete
- Core engine features implemented: combat, triggers, layers, SBA, commander format
- BUG-26 Spree: ✅ Complete (effect patterns + 13 tests)
- BUG-23 Landfall: ✅ Complete (keyword detection + 3 tests)
- 034-etb-choices: ✅ Complete (68 tests covering detection, AI, integration, API, gameplay)
- All pipeline items complete. No remaining work.

## Key Files for Reference
- `mtg_engine/engine/stack.py` — Main file for effect resolution (BUG-26)
- `mtg_engine/engine/zones.py` — ETB detection and AI resolution (034-etb-choices)
- `mtg_engine/api/routers/game.py` — API handlers for choices
- `mtg_engine/models/game.py` — GameState with pending_etb_choice, pending_spree_choice
- `tests/engine/test_spree.py` — Spree mechanic tests
- `tests/engine/test_etb_detection.py` — ETB pattern detection tests
- `tests/engine/test_etb_ai.py` — ETB AI heuristic tests
- `tests/engine/test_etb_integration.py` — ETB engine integration tests
- `tests/api/test_etb_choices.py` — ETB API endpoint tests
- `tests/rules/test_etb_gameplay.py` — ETB end-to-end gameplay tests

## Related Specs
- `specs/036-spree/plan.md` — Spree mechanic implementation plan
- `specs/034-etb-choices/spec.md` — ETB choice system spec
- `spec.md` — Main bug fix log

## Contact Info
For questions about this pipeline, contact the PM agent or review the status file.

---

## Appendix: Spree Effect Examples

### Insatiable Avarice (March of the Machine)
```
Spree — (Choose one or more additional costs.)
+ {2} — Search your library for a card, then shuffle and put that card on top.
+ {B}{B} — Target player draws three cards and loses 3 life.
```

### Expected Effect Text After Parsing
- Mode 1: "Search your library for a card, then shuffle and put that card on top."
- Mode 2: "Target player draws three cards and loses 3 life."

### Patterns Needed in `_apply_single_effect_text()`
1. Tutor pattern: `r"search your library.*?put (?:that )?(?:card )?(?:on top|into your hand)"`
2. Combined draw+lose life: Split on "and" → apply both sub-effects
3. Opponent draw: Handle "target player draws N cards" vs caster drawing

### Implementation Notes
- The effect text is already parsed and stored in `pending_spree_effects`
- Each spree effect string needs to match one of the patterns in `_apply_single_effect_text()`
- For combined effects, consider splitting on "and" before pattern matching

### Testing Strategy
1. Create Insatiable Avarice card with Spree modes in test fixture
2. Simulate casting the spell and selecting spree modes via API
3. Verify `pending_spree_effects` contains correct effect text after selection
4. Resolve the spell and verify effects apply correctly:
   - Tutor: Library search, put on top
   - Draw+lose life: Target player draws 3 cards, loses 3 life

### Expected Test Cases
- Test single spree mode selection (tutor only)
- Test single spree mode selection (draw+lose life only)
- Test multiple spree modes selected
- Test no spree modes selected (base spell resolves normally)

---
*End of pipeline status document — maintained by PM agent*

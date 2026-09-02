# Sprint A: Merge Sprint 6 + Stabilize

## Overview
Merge the `sprint2/litellm-codebot` branch which contains 17 keyword modules implemented in parallel, resolve any merge conflicts with the main branch, and ensure all tests pass. This sprint is purely integration work — no new features are designed here.

**Branch**: `sprint2/litellm-codebot`
**Keywords to merge**: Morph, Suspend, Unearth, Evoke, Miracle, Afterlife, Scavenge, Bloodthirst, Extort, Sunburst, Replicate, Surge, Buyback, Persist, Undying, Entwine, Transmute

---

## User Stories

### SA-01: Merge Sprint 6 Branch and Resolve Conflicts

**User Story**
As a developer, I want to merge the `sprint2/litellm-codebot` branch into main so that all 17 keyword modules are available in the codebase.

**Context**
The `sprint2/litellm-codebot` branch contains implementations for Morph, Suspend, Unearth, Evoke, Miracle, Afterlife, Scavenge, Bloodthirst, Extort, Sunburst, Replicate, Surge, Buyback, Persist, Undying, Entwine, and Transmute. These were developed in parallel with main-branch work (KW-16 through KW-31, APP-04 through APP-06). Merging may produce conflicts in:
- `mtg_engine/models/game.py` — new pending choice fields added on both branches
- `mtg_engine/engine/stack.py` — keyword detection patterns added on both branches
- `mtg_engine/api/routers/game.py` — legal actions and choice handlers added on both branches
- `mtg_engine/ability/keywords/__init__.py` — module exports

**Acceptance Criteria**
- [ ] Merge `sprint2/litellm-codebot` into main branch (or rebase, whichever produces cleaner history)
- [ ] All merge conflicts resolved with no loss of functionality from either branch
- [ ] No duplicate keyword modules (e.g., if Persist exists on both branches, keep the more complete version)
- [ ] `mtg_engine/models/game.py` has all pending choice fields from both branches consolidated
- [ ] `mtg_engine/engine/stack.py` has all keyword detection patterns from both branches
- [ ] `mtg_engine/api/routers/game.py` has all legal action handlers and choice resolvers from both branches
- [ ] All 17 new keyword modules are importable without errors

**Dependencies**: None (first story in Sprint A)

**Priority: High**

**Estimated Effort**: 2-4 hours (depends on conflict complexity)

---

### SA-02: Verify All 17 Merged Keywords Follow Project Standards

**User Story**
As a maintainer, I want to verify that all merged keyword modules follow the project's coding standards so that they are consistent with existing keywords and maintainable.

**Context**
The project enforces specific patterns for keyword modules:
- Pure transforms via `model_copy(update={...})` — never mutate GameState directly
- Detection/parsing from oracle text via regex
- Human path queues pending choice on GameState; AI path auto-resolves
- Each keyword has `has_keyword()`, `from_oracle_text()`, and `apply()` methods

The merged keywords may not follow these patterns since they were developed in a separate branch.

**Acceptance Criteria**
- [ ] Each of the 17 modules (Morph, Suspend, Unearth, Evoke, Miracle, Afterlife, Scavenge, Bloodthirst, Extort, Sunburst, Replicate, Surge, Buyback, Persist, Undying, Entwine, Transmute) has:
  - [ ] `has_keyword()` or equivalent detection method
  - [ ] `from_oracle_text()` parser for cost/value extraction
  - [ ] `apply(game_state, ...)` that returns new GameState via `model_copy(update={...})`
- [ ] No module directly mutates `game_state` attributes (e.g., `game_state.pending_xxx = ...`)
- [ ] All modules use proper type hints (`from __future__ import annotations`, `TYPE_CHECKING`)
- [ ] All modules have appropriate logging via `logging.getLogger(__name__)`

**Dependencies**: SA-01

**Priority: High**

**Estimated Effort**: 2-3 hours (review + fixes)

---

### SA-03: Fix Test Suite After Merge

**User Story**
As a developer, I want all tests to pass after the merge so that I can trust the codebase is working correctly.

**Context**
Before merging, main branch had 2678+ passing tests (3 skipped, 13 xfailed). The `sprint2/litellm-codebot` branch has its own test suite for the 17 keywords. After merge:
- Some existing tests may break due to model changes (new fields on GameState)
- New keyword tests from the feature branch need to be integrated
- There may be test conflicts if both branches modified shared test helpers

**Acceptance Criteria**
- [ ] `pytest tests/ -v` runs with 0 failures (xfails and skips are acceptable)
- [ ] All pre-existing tests that passed before merge still pass (no regressions)
- [ ] New keyword tests from the feature branch are integrated and passing
- [ ] Test count increases by at least 51 (minimum 3 tests per new keyword × 17 keywords)
- [ ] No test imports reference files or modules that no longer exist post-merge

**Dependencies**: SA-01, SA-02

**Priority: High**

**Estimated Effort**: 2-4 hours

---

### SA-04: Wire Merged Keywords into Stack Resolution and Legal Actions

**User Story**
As a player or AI agent, I want the merged keywords to actually fire during gameplay so that cards with these abilities work correctly.

**Context**
A keyword module alone is not enough — it must be wired into:
1. `mtg_engine/engine/stack.py` — detection patterns in `_apply_single_effect_text()` and/or `_apply_spell_effect()` so the keyword fires when a card resolves
2. `mtg_engine/api/routers/game.py` — legal action computation in `_compute_legal_actions()` for human player choices, and choice handler in the `/choice` endpoint

Some of these keywords (e.g., Morph, Suspend) require GameState fields for pending choices that may need to be added.

**Acceptance Criteria**
- [ ] Each keyword that requires stack detection has a regex pattern in `stack.py` effect resolution
- [ ] Each keyword that queues a human choice has:
  - [ ] Corresponding field on `GameState` (e.g., `pending_morph_choice`)
  - [ ] Legal action entries in `_compute_legal_actions()` when the pending choice is active
  - [ ] Choice handler logic in the `/choice` endpoint to resolve the pending state
- [ ] Each keyword that auto-resolves for AI has its `apply()` called at the appropriate game moment
- [ ] Integration test exists for each keyword demonstrating end-to-end flow (cast card → keyword fires → effect applies)

**Dependencies**: SA-01, SA-02

**Priority: High**

**Estimated Effort**: 4-6 hours

---

### SA-05: Update AGENTS.md and Documentation After Merge

**User Story**
As a developer joining the project, I want up-to-date documentation so that I understand what has been implemented.

**Context**
AGENTS.md tracks recent changes with detailed bullet points for each completed feature. The README.md describes available API endpoints. Both need updating to reflect the 17 new keywords.

**Acceptance Criteria**
- [ ] AGENTS.md "Recent Changes" section includes an entry for Sprint A merge listing all 17 keywords
- [ ] Each keyword's implementation summary follows the same format as existing entries (KW-16 through KW-31)
- [ ] README.md is updated if any new API endpoints were added by the merged branch
- [ ] `mtg_engine/ability/keywords/__init__.py` exports are documented

**Dependencies**: SA-03

**Priority: Medium**

**Estimated Effort**: 1 hour

---

## Sprint A Dependencies Map

```
SA-01 (Merge) ──┬──→ SA-02 (Standards Review) ──┐
                │                                 ├──→ SA-04 (Wire into Stack/Legal Actions)
                └──→ SA-03 (Fix Tests) ←──────────┘
                                         ↓
                                    SA-05 (Documentation)
```

## Sprint A Summary

| # | Story | Priority | Effort | Dependencies |
|---|-------|----------|--------|--------------|
| SA-01 | Merge branch + resolve conflicts | High | 2-4h | none |
| SA-02 | Verify coding standards | High | 2-3h | SA-01 |
| SA-03 | Fix test suite | High | 2-4h | SA-01, SA-02 |
| SA-04 | Wire into stack + legal actions | High | 4-6h | SA-01, SA-02 |
| SA-05 | Update documentation | Medium | 1h | SA-03 |

**Total estimated effort**: 11-18 hours

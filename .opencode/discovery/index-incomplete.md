# Discovery Index — Incomplete Items

> This index tracks all incomplete work identified during gap analysis. Completed items from Sprints 4–5 are tracked in `index.md`.

**Last updated**: 2026-07-15  
**Total stories**: 21 across 4 sprints  
**Total estimated effort**: 76–113 hours

---

## Sprint A: Merge Sprint 6 + Stabilize

Merge the `sprint2/litellm-codebot` branch containing 17 keyword modules, resolve conflicts, verify standards, and ensure all tests pass.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| SA-01 | Merge Sprint 6 branch + resolve conflicts | [sprint-a-merge-sprint6.md](./sprint-a-merge-sprint6.md) | High | none | ⏳ |
| SA-02 | Verify all 17 merged keywords follow project standards | [sprint-a-merge-sprint6.md](./sprint-a-merge-sprint6.md) | High | SA-01 | ⏳ |
| SA-03 | Fix test suite after merge | [sprint-a-merge-sprint6.md](./sprint-a-merge-sprint6.md) | High | SA-01, SA-02 | ⏳ |
| SA-04 | Wire merged keywords into stack resolution + legal actions | [sprint-a-merge-sprint6.md](./sprint-a-merge-sprint6.md) | High | SA-01, SA-02 | ⏳ |
| SA-05 | Update AGENTS.md and documentation after merge | [sprint-a-merge-sprint6.md](./sprint-a-merge-sprint6.md) | Medium | SA-03 | ⏳ |

**Effort**: 11–18 hours · **Stories**: 5 (4 High, 1 Medium)

---

## Sprint B: High-Value Keywords Batch 2

Implement Partner/Ward/Scry/Equip and a large batch of additional high-value keywords for Commander and competitive formats.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| SB-01 | Partner / Partner With (CR 702.49) | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | High | none | ⏳ |
| SB-02 | Ward `apply()` implementation (CR 702.145) | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | High | none | ⏳ |
| SB-03 | Scry `apply()` implementation (CR 701.20) | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | High | none | ⏳ |
| SB-04 | Equip activation flow | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | High | none | ⏳ |
| SB-05 | Persist implementation (CR 702.86) | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | Medium | Sprint A (if not merged) | ⏳ |
| SB-06 | Undying implementation (CR 702.88) | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | Medium | Sprint A (if not merged) | ⏳ |
| SB-07 | Additional high-value keywords batch (30 keywords) | [sprint-b-keywords-batch2.md](./sprint-b-keywords-batch2.md) | Medium | SB-01..SB-06 | ⏳ |

**Effort**: 38–53 hours · **Stories**: 7 (4 High, 3 Medium)

---

## Sprint C: Missing Triggers, TODO Fixes, and Edge Cases

Address incomplete trigger categories, fix documented TODOs in the codebase, and close known gaps.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| SC-01 | Implement missing trigger categories (8 types) | [sprint-c-triggers-todos.md](./sprint-c-triggers-todos.md) | Medium | none | ⏳ |
| SC-02 | Fix checkland and fetchland ETB handling (game.py:2397) | [sprint-c-triggers-todos.md](./sprint-c-triggers-todos.md) | High | none | ⏳ |
| SC-03 | Fix `recent_games` stats placeholder (player_stats.py:65) | [sprint-c-triggers-todos.md](./sprint-c-triggers-todos.md) | Medium | none | ⏳ |
| SC-04 | Implement loyalty ability activation | [sprint-c-triggers-todos.md](./sprint-c-triggers-todos.md) | High | none | ⏳ |
| SC-05 | Fix known ETB detection regex gaps | [sprint-c-triggers-todos.md](./sprint-c-triggers-todos.md) | Medium | SC-02 | ⏳ |

**Effort**: 11–17 hours · **Stories**: 5 (2 High, 3 Medium)

---

## Sprint D: Multiplayer Rules Foundation and Match System

Build foundational support for 3+ player games and best-of-3 sideboarding match system.

| # | Story | File | Priority | Dependencies | Status |
|---|-------|------|----------|--------------|--------|
| SD-01 | Multiplayer game creation + turn order | [sprint-d-multiplayer-match.md](./sprint-d-multiplayer-match.md) | High | none | ⏳ |
| SD-02 | Multiplayer combat resolution | [sprint-d-multiplayer-match.md](./sprint-d-multiplayer-match.md) | High | SD-01 | ⏳ |
| SD-03 | Multiplayer targeting + spell resolution | [sprint-d-multiplayer-match.md](./sprint-d-multiplayer-match.md) | Medium | SD-01 | ⏳ |
| SD-04 | Sideboarding + best-of-3 match system | [sprint-d-multiplayer-match.md](./sprint-d-multiplayer-match.md) | Medium | none | ⏳ |
| SD-05 | Multiplayer SBA + win/loss conditions | [sprint-d-multiplayer-match.md](./sprint-d-multiplayer-match.md) | Medium | SD-01 | ⏳ |

**Effort**: 16–25 hours · **Stories**: 5 (2 High, 3 Medium)

---

## Cross-Sprint Dependency Map

```
SPRINT A                          SPRINT B                        SPRINT C              SPRINT D
─────────                         ────────                        ────────              ────────
SA-01 (Merge)                     SB-01 (Partner)                 SC-01 (Triggers)      SD-01 (Multiplayer
  ├── SA-02 (Standards)             │                               │                    Creation)
  ├── SA-03 (Tests)                 ├── SB-07                       ├── SC-05             ├── SD-02 (Combat)
  └── SA-04 (Wire up)               │                               │                   ├── SD-03 (Targeting)
      └── SA-05 (Docs)              │                               │                   └── SD-05 (SBA)
                                    │                               │
                              SB-02..SB-06                          SC-02..SC-04          SD-04 (Sideboarding)
                              (mostly independent)                  (independent)         [independent]

Cross-sprint note: SB-05/SB-06 may be satisfied by Sprint A merge if Persist/Undying exist on feature branch.
```

## Priority Summary

| Priority | Count | Stories |
|----------|-------|---------|
| High | 12 | SA-01..SA-04, SB-01..SB-04, SC-02, SC-04, SD-01, SD-02 |
| Medium | 9 | SA-05, SB-05..SB-07, SC-01, SC-03, SC-05, SD-03..SD-05 |

## Recommendation: Execution Order

1. **Start with Sprint A** — It's a merge and stabilization sprint that unblocks everything else. The 17 keywords from the feature branch may satisfy some of Sprint B's stories (Persist, Undying), reducing total work.
2. **Sprint C in parallel with Sprint A** — Stories SC-02, SC-03, SC-04 are independent TODO fixes that don't depend on any sprint and can be done while reviewing merge conflicts.
3. **Sprint B after Sprint A** — Partner (SB-01) is the highest-value single story for Commander completeness. Ward, Scry, and Equip follow as they fix existing stub modules. The large batch (SB-07) can be tackled incrementally.
4. **Sprint D last** — Multiplayer requires the most structural changes to GameState and turn management. Best done after the keyword backlog is cleared so that new keywords can be designed with multiplayer in mind from the start.

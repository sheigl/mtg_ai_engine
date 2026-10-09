# Pipeline Status

## Current Feature: Story 7-7 (Phasing/Modulate/Saddle/Prototype) — 7-7a ✅, 7-7b🔄 in progress
## Last Step Completed: 7-7a Phasing (CR 702.26) FULL PIPELINE (Implement → Code Review [revision round] → Test → Document). Suite 3193/0/3skip/13xfail (+26 net from Convoke baseline 3167); skip/xfail byte-identical; ruff 0 NEW. AGENTS.md updated.
## Next Action: Implement Saddle (7-7b) — Discovery recommended order: Phasing first, then Saddle (highest infra reuse), then Modulate + Prototype in parallel.

### Story 7-7 sub-stories progress
| Sub-story | Keyword (CR) | Implement | Code Review | Test | Document |
|-----------|--------------|-----------|-------------|------|----------|
| 7-7a | Phasing (702.26) | ✅ | ✅ (revision fixed: API-layer legal-action exclusion + cast_spell ValueError → HTTP 422) | ✅ (3193/0/3skip/13xfail, +26 net) | ✅ |
| 7-7b | Saddle (BLI 2025) | 🔄 In progress | ⏳ | ⏳ | ⏳ |
| 7-7c | Modulate (MOM 2023) | ⏳ | ⏳ | ⏳ | ⏳ |
| 7-7d | Prototype (BLI 2025) | ⏳ | ⏳ | ⏳ | ⏳ |

## OOS items (user-directed completion)
| Item | Description | Implement | Code Review | Test | Document |
|------|-------------|-----------|-------------|------|----------|
| OOS-1 | Ward fires on ABILITIES (CR 702.145a "spell or ability") — was spells-only | ✅ Done | ✅ Approved | ✅ Passed | ✅ Done |
| OOS-2 | Toxic spurious no-op combat_damage PendingTrigger (trigger hygiene) | ✅ Done | ✅ Approved | ✅ Passed | ✅ Done |

## Notes / Open items
- Baseline evolution: 3031 (Ward) → 3046 (Toxic) → 3067 (Ward-on-Abilities/OOS-1) → 3079 (Toxic trigger hygiene/OOS-2) → 3102 (Buyback) → 3115 (Entwine) → 3126 (Overload) → 3139 (Miracle) → 3149 (Bloodthirst) → 3167 (Convoke) → **3193 (Phasing, 7-7a)**. CURRENT: 3193/0/3skip/13xfail.
- Skip/xfail set MUST stay byte-identical: 3 skip = tests/api/test_etb_choices.py:185/190/195; 13 xfail across test_etb_ai/detection/integration. (Verified for Phasing.)
- Git: committed as `78334bb` (rebased onto remote f207cfd), pushed as `e2d570d` to origin/main this session — 486 files changed, +45734/−2088. Per explicit user directive, commits ARE allowed now (the "do not commit" note in prior notes is STALE).
- Subagents unreliable — empty/partial results + CodeReview is shell-less. ALWAYS confirm via ground-truth grep after; Test is the only authoritative regression source.

(End of file)

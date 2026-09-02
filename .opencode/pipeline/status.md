# Pipeline Status

## Current Feature: Story 7-6 (Buyback/Entwine/Overload/Miracle/Bloodthirst/Convoke) — 7-6a ✅ 7-6b ✅ 7-6c ✅ 7-6d ✅ 7-6e ✅ 7-6f ✅, COMPLETE
## Last Step Completed: 7-6f Convoke (CR 702.43) FULL PIPELINE + Document verified (3167/0/3/13, +18 net). AGENTS.md top entry. Ruff 0 NEW; skip/xfail byte-identical.
## Next Action: 7-6 umbrella complete. Next backlog item: review remaining Sprint 7 P1/P2 items or move to next feature.

### 7-6 umbrella progress (sub-stories 7-6a..7-6f)
| Sub-story | Keyword (CR) | Implement | Code Review | Test | Document |
|-----------|--------------|-----------|-------------|------|----------|
| 7-6a | Buyback (702.27) | ✅ | ✅ | ✅ (3102/0/3/13) | ✅ |
| 7-6b | Entwine (702.39) | ✅ | ✅ | ✅ (3115/0/3/13) | ✅ |
| 7-6c | Overload (702.95) | ✅ | ✅ | ✅ (3126/0/3/13) | ✅ |
| 7-6d | Miracle (702.93) | ✅ | ✅ | ✅ (3139/0/3/13) | ✅ |
| 7-6e | Bloodthirst (702.22) | ✅ | ✅ | ✅ (3149/0/3/13) | ✅ |
| 7-6f | Convoke (702.43) | ✅ | ✅ | ✅ (3167/0/3/13) | ✅ |

## OOS items (user-directed completion)
| Item | Description | Implement | Code Review | Test | Document |
|------|-------------|-----------|-------------|------|----------|
| OOS-1 | Ward fires on ABILITIES (CR 702.145a "spell or ability") — was spells-only | ✅ Done | ✅ Approved | ✅ Passed | ✅ Done |
| OOS-2 | Toxic spurious no-op combat_damage PendingTrigger (trigger hygiene) | ✅ Done | ✅ Approved | ✅ Passed | ✅ Done |

| Feature | Discovery + Planning | Implement | Code Review | Test | Document |
|---------|----------|-------------|------|----------|----------|
| 7-5 Umbrella (Crew..Toxic) | ✅ | ✅ | ✅ | ✅ | ✅ | SHIPPED (3046/0/3/13) |
| OOS-1 Ward-on-Abilities | n/a | ✅ | ✅ | ✅ | ✅ | 3067/0/3/13 (+21 net) |
| OOS-2 Toxic trigger hygiene | n/a | ✅ | ✅ | ✅ | ✅ | 3079/0/3/13 (+12 net) |

## Notes / Open items
- Baseline evolution: 3031 (Ward) → 3046 (Toxic) → 3067 (Ward-on-Abilities/OOS-1) → 3079 (Toxic trigger hygiene/OOS-2) → 3102 (Buyback) → 3115 (Entwine) → 3126 (Overload) → 3139 (Miracle) → 3149 (Bloodthirst) → 3167 (Convoke). CURRENT: 3167/0/3/13.
- 7-6e Bloodthirst: real apply() + ETB wiring + damage tracking complete; 19 integration tests (TestBloodthirstUnit 6, TestBloodthirstApply 5, TestBloodthirstETB 6, TestBloodthirstDamageTracking 2); suite 3149/0/3/13 (+10 net from 3139). AGENTS.md updated. Verified this session: 19 pass, keywords baseline 108 pass, ruff 0 NEW (4 E402 pre-existing).
- 7-6f Convoke: real apply() + cost reduction via tapping creatures; 9 integration tests; suite 3167/0/3/13 (+18 net from 3149). AGENTS.md top entry. Verified this session: 9 pass.
- 7-6 umbrella COMPLETE (all six sub-stories 7-6a..7-6f shipped).
- Subagents unreliable — empty/partial results + CodeReview is shell-less. ALWAYS confirm via ground-truth grep after; Test is the only authoritative regression source.
- Tree dirty by design (Sprint 7 + OOS work uncommitted per "do not commit"). HEAD at 7363140; do NOT commit.

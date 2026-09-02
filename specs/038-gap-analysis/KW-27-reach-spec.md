# KW-27 Reach Design Spec

## CR Reference
- **CR Section**: 702.17 Reach
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.17a Reach is a static ability.
> 
> 702.17b A creature with flying can't be blocked except by creatures with flying and/or reach. (See rule 509, "Declare Blockers Step," and rule 702.9, "Flying.")
> 
> 702.17c Multiple instances of reach on the same creature are redundant.

## Keyword Type
- **Category**: Passive
- **Base class**: `PassiveKeyword`
- **CR classification**: Static ability (blocking permission)

## Behavior Summary
Reach allows a creature to block flying creatures, bypassing the normal restriction that only flying creatures can block flyers. A creature with reach can block any creature regardless of whether it has flying. This is primarily useful against flying attackers — without reach or flying, a creature cannot legally block a flyer. Reach doesn't grant any offensive benefits; it's purely a defensive capability.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\breach\b"` — detects presence of reach keyword in oracle text or keywords list
- **Cost/count extraction**: N/A — reach has no associated cost or numeric value
- **Plain keyword fallback**: Reach is always a plain keyword with no cost; detection checks for keyword presence

### Query Helper Signatures (No Apply Method)
```python
def has_reach(game_state: GameState, perm_id: str) -> bool:
    # Returns True if the permanent has reach
    
def can_block_flying(game_state: GameState, blocker_perm_id: str) -> bool:
    # Returns True if blocker has flying or reach (CR 702.17b)
```

### State Tracking
- **GameState field(s)** used: None — query helpers read from battlefield permanents' keywords
- **PlayerState field(s)** used: None
- **Pure transform**: N/A — query helpers return boolean, don't modify state

### Human vs AI Path
- **N/A** — Passive keyword with no choices to make; blocking validation applies equally to both players

## Edge Cases
1. **Blocker not on battlefield** — Query helper should handle gracefully if blocker_perm_id doesn't exist in battlefield
2. **Reach combined with menace** — A creature with reach and menace can block flying but still requires 2+ blockers to block menacing flyers
3. **Non-flying attacker blocked normally** — Reach has no effect when blocking non-flying creatures; any creature can block them

## Related Keywords
- **Flying (702.9)**: The evasion ability that reach counters; creatures with flying can also block flying attackers
- **Menace (702.111)**: Requires 2+ blockers; combines with reach for "2+ blockers with flying/reach" restriction against flying+menace
- **Reach and ground combat** — Reach only matters when facing flying opponents; otherwise functions as normal blocking

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Creature with reach blocks flying attacker | `can_block_flying()` returns True, blocking legal | CR 702.17b |
| 2 | Creature without reach/flying attempts to block flyer | `can_block_flying()` returns False, blocking illegal | CR 702.17b |
| 3 | Creature with flying blocks flying attacker | `can_block_flying()` returns True (flying also works) | CR 702.9 |
| 4 | Blocker not on battlefield edge case | Query helper handles gracefully (returns False or raises) | — |
| 5 | Detection: keyword in card keywords list | Card with "reach" in keywords field is detected | — |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/reach.py`
- [x] Query helper functions implemented (`has_reach`, `can_block_flying`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (8 tests)
- [ ] Stacked in blocking validation — TODO: wire into combat blocker assignment logic

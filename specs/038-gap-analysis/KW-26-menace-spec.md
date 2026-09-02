# KW-26 Menace Design Spec

## CR Reference
- **CR Section**: 702.111 Menace
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.111a Menace is an evasion ability.
> 
> 702.111b A creature with menace can't be blocked except by two or more creatures. (See rule 509, "Declare Blockers Step.")
> 
> 702.111c Multiple instances of menace on the same creature are redundant.

## Keyword Type
- **Category**: Passive
- **Base class**: `PassiveKeyword`
- **CR classification**: Evasion ability (static ability)

## Behavior Summary
Menace is an evasion ability that requires at least two creatures to block a menacing attacker. A single blocker cannot legally block a creature with menace — the defending player must assign two or more blockers to successfully block it. This makes menacing creatures harder to deal with during combat, as they require multiple resources to stop.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bmenace\b"` — detects presence of menace keyword in oracle text or keywords list
- **Cost/count extraction**: N/A — menace has no associated cost or numeric value
- **Plain keyword fallback**: Menace is always a plain keyword with no cost; detection checks for keyword presence

### Query Helper Signatures (No Apply Method)
```python
def is_menacing(game_state: GameState, perm_id: str) -> bool:
    # Returns True if the permanent has menace
    
def can_block_menacing(game_state: GameState, attacker_perm_id: str, blocker_perm_ids: list[str]) -> bool:
    # Returns True only if len(blocker_perm_ids) >= 2 (CR 702.111b)
```

### State Tracking
- **GameState field(s)** used: None — query helpers read from battlefield permanents' keywords
- **PlayerState field(s)** used: None
- **Pure transform**: N/A — query helpers return boolean, don't modify state

### Human vs AI Path
- **N/A** — Passive keyword with no choices to make; blocking validation applies equally to both players

## Edge Cases
1. **Attacker not on battlefield** — Query helper should handle gracefully if attacker_perm_id doesn't exist in battlefield
2. **Menace combined with other evasion abilities** — Flying + menace requires 2+ blockers with flying or reach; implementation must check both restrictions
3. **Multiple menacing attackers** — Each menacing creature independently requires 2+ blockers; defender may need to allocate multiple creatures per attacker

## Related Keywords
- **Flying (702.9)**: Another evasion ability that restricts which creatures can block; combines with menace for dual restriction
- **Reach (702.17)**: Allows creatures to block flying; works with menace to enable 2+ reach blockers against flying+menace attackers
- **Menace and unblockable** — If defender has fewer than 2 creatures total, menacing attacker cannot be blocked

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Single blocker attempts to block menacing creature | `can_block_menacing()` returns False, blocking illegal | CR 702.111b |
| 2 | Two blockers assigned to menacing creature | `can_block_menacing()` returns True, blocking legal | CR 702.111b |
| 3 | Non-menacing creature blocked normally | `is_menacing()` returns False, no restriction | — |
| 4 | Attacker not on battlefield edge case | Query helper handles gracefully (returns False or raises) | — |
| 5 | Detection: keyword in card keywords list | Card with "menace" in keywords field is detected | — |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/menace.py`
- [x] Query helper functions implemented (`is_menacing`, `can_block_menacing`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (5 tests)
- [ ] Stacked in blocking validation — TODO: wire into combat blocker assignment logic

# KW-28 Shroud Design Spec

## CR Reference
- **CR Section**: 702.18 Shroud
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.18a Shroud is a static ability. "Shroud" means "This permanent or player can't be the target of spells or abilities."
> 
> 702.18b Multiple instances of shroud on the same permanent or player are redundant.

## Keyword Type
- **Category**: Passive
- **Base class**: `PassiveKeyword`
- **CR classification**: Static ability (targeting restriction)

## Behavior Summary
Shroud prevents a permanent or player from being targeted by ANY spells or abilities, regardless of who controls them. Unlike hexproof (which only blocks opponent targeting), shroud blocks all targeting — the controller cannot target their own shrouded permanents either. This makes shroud significantly more restrictive than hexproof and is rarely seen on modern cards due to its harsh limitations.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bshroud\b"` — detects presence of shroud keyword in oracle text or keywords list
- **Cost/count extraction**: N/A — shroud has no associated cost or numeric value
- **Plain keyword fallback**: Shroud is always a plain keyword with no cost; detection checks for keyword presence

### Query Helper Signatures (No Apply Method)
```python
def is_shrouded(game_state: GameState, perm_id_or_player_name: str) -> bool:
    # Returns True if the permanent or player has shroud
    
def can_target_shrouded(game_state: GameState, target: str) -> bool:
    # Returns False whenever target has shroud, regardless of controller (CR 702.18a)
```

### State Tracking
- **GameState field(s)** used: None — query helpers read from battlefield permanents' keywords
- **PlayerState field(s)** used: None — player-level shroud not yet implemented on PlayerState
- **Pure transform**: N/A — query helpers return boolean, don't modify state

### Human vs AI Path
- **N/A** — Passive keyword with no choices to make; targeting validation applies equally to both players

## Edge Cases
1. **Controller cannot target own shrouded permanents** — Unlike hexproof, the controller is also blocked from targeting; this affects beneficial effects like "tap: draw a card" abilities
2. **"Shroud" vs "Hexproof" distinction** — Shroud blocks ALL targeting; hexproof only blocks opponent targeting; implementation must not confuse these
3. **Multiple shroud sources** — CR 702.18b states multiple instances are redundant; no stacking or amplification effect

## Related Keywords
- **Hexproof (702.11)**: Less restrictive version that allows controller to target own permanents
- **Protection**: Also prevents targeting but includes additional effects (can't be blocked, damaged, enchanted, equipped)
- **Shroud and self-targeting** — Controller cannot use "target creature you control" effects on shrouded permanents

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Opponent targets shrouded permanent | `can_target_shrouded()` returns False, targeting illegal | CR 702.18a |
| 2 | Controller targets own shrouded permanent | `can_target_shrouded()` returns False, targeting illegal (unlike hexproof) | CR 702.18a |
| 3 | Permanent without shroud targeted normally | `is_shrouded()` returns False, no restriction | — |
| 4 | Query helper not-found edge case | `is_shrouded()` returns False for non-existent perm_id | — |
| 5 | Detection: keyword in card keywords list | Card with "shroud" in keywords field is detected | — |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/shroud.py`
- [x] Query helper functions implemented (`is_shrouded`, `can_target_shrouded`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (7 tests)
- [ ] Stacked in targeting validation — TODO: wire into `_compute_legal_actions` and spell targeting checks

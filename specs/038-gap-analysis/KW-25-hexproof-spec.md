# KW-25 Hexproof Design Spec

## CR Reference
- **CR Section**: 702.11 Hexproof
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.11a Hexproof is a static ability.
> 
> 702.11b "Hexproof" on a permanent means "This permanent can't be the target of spells or abilities your opponents control."
> 
> 702.11c "Hexproof" on a player means "You can't be the target of spells or abilities your opponents control."

## Keyword Type
- **Category**: Passive
- **Base class**: `PassiveKeyword`
- **CR classification**: Static ability (targeting restriction)

## Behavior Summary
Hexproof prevents a permanent or player from being targeted by spells or abilities controlled by opponents. The controller of the hexproof permanent can still target it with their own spells and abilities. This is a continuous effect that applies whenever targeting legality is checked — it doesn't use the stack and has no activation cost. Unlike shroud, hexproof only blocks opponent targeting, not self-targeting.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bhexproof\b"` — detects presence of hexproof keyword in oracle text or keywords list
- **Cost/count extraction**: N/A — hexproof has no associated cost or numeric value
- **Plain keyword fallback**: Hexproof is always a plain keyword with no cost; detection checks for keyword presence

### Query Helper Signatures (No Apply Method)
```python
def is_hexproof(game_state: GameState, perm_id_or_player_name: str) -> bool:
    # Returns True if the permanent or player has hexproof
    
def can_target_hexproof(game_state: GameState, target: str, source_controller: str) -> bool:
    # Returns True only if target lacks hexproof OR source controller equals target controller (CR 702.11b)
```

### State Tracking
- **GameState field(s)** used: None — query helpers read from battlefield permanents' keywords
- **PlayerState field(s)** used: None — player-level hexproof not yet implemented on PlayerState
- **Pure transform**: N/A — query helpers return boolean, don't modify state

### Human vs AI Path
- **N/A** — Passive keyword with no choices to make; targeting validation applies equally to both players

## Edge Cases
1. **Controller change after hexproof granted** — If permanent changes controllers, the new controller can target it (hexproof only blocks opponents)
2. **"Hexproof from [quality]" variant (702.11d)**: Partial hexproof that only blocks specific colored spells/abilities; not yet implemented
3. **Multiple targeting sources** — Each spell/ability checks hexproof independently; one opponent's inability to target doesn't affect another

## Related Keywords
- **Shroud (702.18)**: Blocks ALL targeting regardless of controller; stricter than hexproof
- **Protection**: Also prevents targeting but includes additional effects (can't be blocked, damaged, enchanted, equipped)
- **Hexproof and self-targeting** — Controller can target own hexproof permanents for beneficial or detrimental effects

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Opponent targets hexproof permanent | `can_target_hexproof()` returns False, targeting illegal | CR 702.11b |
| 2 | Controller targets own hexproof permanent | `can_target_hexproof()` returns True, targeting legal | CR 702.11b |
| 3 | Permanent without hexproof targeted normally | `is_hexproof()` returns False, no restriction | — |
| 4 | Query helper not-found edge case | `is_hexproof()` returns False for non-existent perm_id | — |
| 5 | Detection: keyword in card keywords list | Card with "hexproof" in keywords field is detected | — |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/hexproof.py`
- [x] Query helper functions implemented (`is_hexproof`, `can_target_hexproof`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (7 tests)
- [ ] Stacked in targeting validation — TODO: wire into `_compute_legal_actions` and spell targeting checks

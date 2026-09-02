# KW-19 Delve Design Spec

## CR Reference
- **CR Section**: 702.66 Delve
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.66a Delve is a static ability that functions while the spell with delve is on the stack. "Delve" means "For each generic mana in this spell's total cost, you may exile a card from your graveyard rather than pay that mana."
> 
> 702.66b The delve ability isn't an additional or alternative cost and applies only after the total cost of the spell with delve is determined.
> 
> 702.66c Multiple instances of delve on the same spell are redundant.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Cost reduction (static ability, not additional/alternative cost)

## Behavior Summary
Delve allows a player to exile cards from their graveyard to pay for generic mana in the spell's total cost. Each exiled card pays for one generic mana. Delve is NOT an alternative or additional cost — it applies after the total cost is determined and only replaces generic mana portions of that cost. Colored mana requirements must still be paid with actual colored mana.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bdelve\b"` — detects presence of delve keyword; `r"delve\s+(\d+|\b(one|two|three|four|five|six|seven|eight|nine)\b)"` — extracts numeric count for word numbers and digits (fixed bug: was only capturing single `{...}` blocks)
- **Cost/count extraction**: `parse_delve_cost(oracle_text) -> str | None` returns the generic mana cost string; `parse_delve_count(oracle_text) -> int` returns the number of cards to exile (handles both digit and word numbers like "two")
- **Plain keyword fallback**: Cards with just "Delve" (no explicit count) are detected via `from_oracle_text()` but parsing functions return defaults

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_delve_choice on GameState
    # For AI player: auto-resolves based on graveyard card availability
```

### State Tracking
- **GameState field(s)** used: `pending_delve_choice: Optional[dict]` — contains `player`, `card_name`, `delve_cost`, `resolved`
- **PlayerState field(s)** used: None (graveyard cards exiled during resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_delve_choice` on GameState with `resolved=False`; API handler resolves choice (`delve_pay` or `delve_skip`)
- **AI player**: Auto-resolves based on graveyard card count; if enough cards available, exiles them and sets `resolved=True`; if not, sets `resolved=True` without exile

## Edge Cases
1. **Multi-part mana costs** — Fixed bug: regex now handles `{2}{U}` style costs (was only capturing single `{...}` blocks)
2. **Word number parsing** — Fixed bug: regex matches "two" in addition to digits (`\d+`) for cards like "Delve two cards"
3. **No generic mana in cost** — If spell has no generic mana, delve is effectively useless; implementation should handle gracefully

## Related Keywords
- **Convoke (702.51)**: Similar cost reduction but uses tapped creatures instead of exiled graveyard cards
- **Sacrifice to cast**: Non-keyword mechanic that also reduces casting cost through permanent sacrifice
- **Delve and colored mana** — Delve only replaces generic mana; colored portions must be paid normally

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_delve_choice` set with card info, cost, resolved=False | CR 702.66a |
| 2 | AI player — auto-resolves when graveyard has cards | Cards exiled from graveyard, `resolved=True` | CR 702.66a |
| 3 | AI player — skips when graveyard empty | No exile, `resolved=True`, delve not used | CR 702.66a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Delve" | — |
| 6 | Multi-part cost parsing | `parse_delve_cost()` handles `{2}{U}` correctly | CR 702.66a |
| 7 | Word number extraction | `parse_delve_count()` extracts from "two cards" pattern | CR 702.66a |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/delve.py`
- [x] Detection & parsing functions implemented (`parse_delve_cost`, `parse_delve_count`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (pending_delve_choice)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (10 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into mana payment flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

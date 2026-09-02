# KW-17 Flashback Design Spec

## CR Reference
- **CR Section**: 702.34 Flashback
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.34a Flashback appears on some instants and sorceries. It represents two static abilities: one that functions while the card is in a player's graveyard and another that functions while the card is on the stack. "Flashback [cost]" means "You may cast this card from your graveyard if the resulting spell is an instant or sorcery spell by paying [cost] rather than paying its mana cost" and "If the flashback cost was paid, exile this card instead of putting it anywhere else any time it would leave the stack." Casting a spell using its flashback ability follows the rules for paying alternative costs in rules 601.2b and 601.2f–h.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Alternative cost (static ability) + replacement effect

## Behavior Summary
Flashback allows a player to cast an instant or sorcery from their graveyard by paying the flashback cost instead of the mana cost. When the spell leaves the stack (resolves, is countered, etc.), it is exiled instead of going to the graveyard. This is both an alternative casting cost and a replacement effect that applies whenever the spell would leave the stack.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bflashback\s*[—\-]?\s*(\{[^}]+\})"` — extracts flashback cost from oracle text
- **Cost/count extraction**: `parse_flashback_cost(oracle_text) -> str | None` returns the `{...}` mana cost string
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Flashback" and no cost; `parse_flashback_cost()` returns `None` in that case

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_flashback_exile on GameState
    # For AI player: auto-resolves based on mana affordability
```

### State Tracking
- **GameState field(s)** used: `pending_flashback_exile: Optional[dict]` — contains `player`, `card_id`, `card_name`, `flashback_cost`, `resolved`
- **PlayerState field(s)** used: None (mana pool modified in-place during AI resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_flashback_exile` on GameState with `resolved=False`; API handler resolves choice (`flashback_pay` or `flashback_skip`)
- **AI player**: Auto-resolves using `can_pay_cost(player.mana_pool, flashback_cost)` heuristic; if affordable, deducts mana and sets `resolved=True`; if not, sets `resolved=True` without mana deduction

## Edge Cases
1. **Flashback with colored mana requirement** — AI must check for specific colored mana availability, not just generic mana count
2. **Spell countered after flashback paid** — Card is still exiled (replacement effect applies whenever spell leaves stack)
3. **Card already in exile zone** — Flashback only functions from graveyard; cards in other zones cannot use flashback

## Related Keywords
- **Escape (702.138)**: Also allows casting from graveyard with alternative cost, but doesn't exile on leaving stack
- **Madness (702.35)**: Alternative cost triggered by discard event rather than voluntary casting
- **Rebound**: Similar "instead of going to graveyard" mechanic but triggers on resolution

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_flashback_exile` set with card info, cost, resolved=False | CR 702.34a |
| 2 | AI player — auto-resolves when affordable | Mana deducted from pool, `resolved=True` | CR 702.34a |
| 3 | AI player — skips when unaffordable | No mana change, `resolved=True`, flashback not paid | CR 702.34a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Flashback {2}{U}" | — |
| 6 | Detection: plain keyword only | `parse_flashback_cost()` returns None, detection still works | — |
| 7 | Colored mana flashback cost | AI pays colored mana first, then generic from pool | CR 702.34a |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/flashback.py`
- [x] Detection & parsing functions implemented (`parse_flashback_cost`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (`pending_flashback_exile: Optional[dict] = Field(default=None)`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (10 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into graveyard casting flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

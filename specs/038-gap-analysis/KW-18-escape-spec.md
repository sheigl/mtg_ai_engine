# KW-18 Escape Design Spec

## CR Reference
- **CR Section**: 702.138 Escape
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.138a Escape represents a static ability that functions while the card with escape is in a player's graveyard. "Escape [cost]" means "You may cast this card from your graveyard by paying [cost] rather than paying its mana cost." Casting a spell using its escape ability follows the rules for paying alternative costs in rules 601.2b and 601.2f–h.
> 
> 702.138b A spell or permanent "escaped" if that spell or the spell that became that permanent as it resolved was cast from a graveyard with an escape ability.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Alternative cost (static ability)

## Behavior Summary
Escape allows a player to cast a card from their graveyard by paying the escape cost instead of the mana cost. Unlike Flashback, Escape does not automatically exile the card when it leaves the stack — the card goes to its normal destination (graveyard for instants/sorceries, battlefield for permanents). Some cards have additional abilities that trigger "when it enters this way" or grant counters/abilities if the permanent escaped.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bescape\s*[—\-]?\s*(\{[^}]+\})"` — extracts escape cost from oracle text; `(?:exile|escape)\s+(\d+)\s+other` — extracts exile count for cards that require exiling other cards
- **Cost/count extraction**: `parse_escape_cost(oracle_text) -> str | None` returns the `{...}` mana cost string; `parse_exile_count(oracle_text) -> int` returns the number of additional cards to exile
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Escape" and no cost; `parse_escape_cost()` returns `None` in that case

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_escape_exile on GameState
    # For AI player: auto-resolves based on mana affordability
```

### State Tracking
- **GameState field(s)** used: `pending_escape_exile: Optional[dict]` — contains `player`, `card_id`, `card_name`, `escape_cost`, `exile_count`, `resolved`
- **PlayerState field(s)** used: None (mana pool modified in-place during AI resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_escape_exile` on GameState with `resolved=False`; API handler resolves choice (`escape_pay` or `escape_skip`)
- **AI player**: Auto-resolves using `can_pay_cost(player.mana_pool, escape_cost)` heuristic; if affordable, deducts mana and sets `resolved=True`; if not, sets `resolved=True` without mana deduction

## Edge Cases
1. **Escape with exile count requirement** — Some cards require exiling N other cards from graveyard in addition to paying the cost; current implementation tracks count but doesn't enforce exile selection
2. **Card enters battlefield via escape** — Unlike flashback, permanents cast via escape stay on battlefield and don't auto-exile when leaving stack
3. **"Escaped" designation tracking** — CR 702.138b defines "escaped" status; current implementation doesn't track this flag for linked abilities

## Related Keywords
- **Flashback (702.34)**: Similar graveyard casting but exiles card when it leaves stack
- **Madness (702.35)**: Alternative cost triggered by discard event rather than voluntary casting
- **Reanimate**: Non-keyword effect that also casts from graveyard without exile requirement

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_escape_exile` set with card info, cost, exile_count, resolved=False | CR 702.138a |
| 2 | AI player — auto-resolves when affordable | Mana deducted from pool, `resolved=True` | CR 702.138a |
| 3 | AI player — skips when unaffordable | No mana change, `resolved=True`, escape not paid | CR 702.138a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Escape {3}{B}" | — |
| 6 | Detection: plain keyword only | `parse_escape_cost()` returns None, detection still works | — |
| 7 | Exile count parsing | `parse_exile_count()` extracts N from "Escape N other cards" pattern | CR 702.138a |
| 8 | Colored mana escape cost | AI pays colored mana first, then generic from pool | CR 702.138a |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/escape.py`
- [x] Detection & parsing functions implemented (`parse_escape_cost`, `parse_exile_count`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (`pending_escape_exile: Optional[dict] = None`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (11 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into graveyard casting flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

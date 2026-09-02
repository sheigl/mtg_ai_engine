# KW-16 Kicker Design Spec

## CR Reference
- **CR Section**: 702.33 Kicker
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.33a Kicker is a static ability that functions while the spell with kicker is on the stack. "Kicker [cost]" means "You may pay an additional [cost] as you cast this spell." Paying a spell's kicker cost(s) follows the rules for paying additional costs in rules 601.2b and 601.2f–h.
> 
> 702.33d If a spell's controller declares the intention to pay any of that spell's kicker costs, that spell has been "kicked." If a spell has two kicker costs or has multikicker, it may be kicked multiple times. See rule 601.2b.
> 
> 702.33e Objects with kicker or multikicker have additional abilities that specify what happens if they were kicked. These abilities are linked to the kicker or multikicker abilities printed on that object: they can refer only to those specific kicker or multikicker abilities. See rule 607, "Linked Abilities."

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Additional optional cost (static ability)

## Behavior Summary
Kicker is an additional optional cost that may be paid as a spell is cast. When the kicker cost is paid, the spell is considered "kicked" and its enhanced effect resolves instead of the base effect. The decision to pay kicker happens during the casting process before targets are chosen (CR 601.2c). If part of the ability only applies if kicked and includes targets, those targets are chosen only if the spell was kicked.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bkicker\s*[—\-]?\s*(\{[^}]+\})"` — extracts kicker cost from oracle text
- **Cost/count extraction**: `parse_kicker_cost(oracle_text) -> str | None` returns the `{...}` mana cost string
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Kicker" and no cost; `parse_kicker_cost()` returns `None` in that case

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_kicker_choice on GameState
    # For AI player: auto-resolves based on mana affordability
```

### State Tracking
- **GameState field(s)** used: `pending_kicker_choice: Optional[dict]` — contains `player`, `card_name`, `kicker_cost`, `base_cost`, `resolved`
- **PlayerState field(s)** used: None (mana pool modified in-place during AI resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_kicker_choice` on GameState with `resolved=False`; API handler resolves choice (`kicker_pay` or `kicker_skip`)
- **AI player**: Auto-resolves using `can_pay_cost(player.mana_pool, kicker_cost)` heuristic; if affordable, deducts mana and sets `resolved=True`; if not, sets `resolved=True` without mana deduction

## Edge Cases
1. **Card with multiple kicker costs** — CR 702.33f allows separate "kicked with its [A] kicker" abilities; current implementation handles single kicker cost only
2. **Kicker with colored mana requirement** — AI must check for specific colored mana availability, not just generic mana count
3. **Spell leaves stack before resolution** — If kicked spell is countered or removed, the "if this spell was kicked" clause still applies to any triggered abilities that fired

## Related Keywords
- **Multikicker (702.33c)**: Variant allowing kicker cost to be paid multiple times; not yet implemented
- **Sticker Kicker (702.33h)**: Modern variant combining kicker with sticker counter mechanics; not yet implemented
- **Kicker and/or**: CR 702.33b treats "Kicker [cost 1] and/or [cost 2]" as two separate kicker abilities

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_kicker_choice` set with card info, cost, resolved=False | CR 702.33a |
| 2 | AI player — auto-resolves when affordable | Mana deducted from pool, `resolved=True` | CR 702.33d |
| 3 | AI player — skips when unaffordable | No mana change, `resolved=True`, kicker not paid | CR 702.33a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Kicker {4}" | — |
| 6 | Detection: plain keyword only | `parse_kicker_cost()` returns None, detection still works | — |
| 7 | Colored mana kicker cost | AI pays colored mana first, then generic from pool | CR 702.33a |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/kicker.py`
- [x] Detection & parsing functions implemented (`parse_kicker_cost`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (`pending_kicker_choice: Optional[dict] = None`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (10 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into mana payment flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

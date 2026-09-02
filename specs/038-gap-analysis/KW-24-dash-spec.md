# KW-24 Dash Design Spec

## CR Reference
- **CR Section**: 702.109 Dash
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.109a Dash represents three abilities: two static abilities that function while the card with dash is on the stack, one of which may create a delayed triggered ability, and a static ability that functions while the object with dash is on the battlefield. "Dash [cost]" means "You may cast this card by paying [cost] rather than its mana cost," "If this spell's dash cost was paid, return the permanent this spell becomes to its owner's hand at the beginning of the next end step," and "As long as this permanent's dash cost was paid, it has haste." Casting a spell for its dash cost follows the rules for paying alternative costs in rules 601.2b and 601.2f–h.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Alternative cost (static ability) + delayed triggered ability + static haste grant

## Behavior Summary
Dash allows a creature to be cast for an alternative cost, granting it haste so it can attack immediately. At the beginning of the next end step, the dashed creature is returned to its owner's hand. This provides a temporary attacker that can strike this turn but must be recast later. The three abilities work together: alternative casting cost, delayed return trigger, and conditional haste grant.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bdash\s*[—\-]?\s*(\{[^}]+\})"` — extracts dash cost from oracle text
- **Cost/count extraction**: `parse_dash_cost(oracle_text) -> str | None` returns the `{...}` mana cost string
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Dash" and no explicit cost; parsing functions return defaults

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> tuple[GameState, Card | None]:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_dash_choice on GameState
    # For AI player: auto-resolves based on mana affordability and combat value
```

### State Tracking
- **GameState field(s)** used: `pending_dash_choice: Optional[dict]` — contains `player`, `card_name`, `dash_cost`, `resolved`; `dashed_creatures: dict[str, ...]` — tracks which creatures were dashed for end-step return
- **PlayerState field(s)** used: None (battlefield and hand modified during resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_dash_choice` on GameState with `resolved=False`; API handler resolves choice (`dash_cast` or `dash_normal`)
- **AI player**: Auto-resolves using strategic heuristic; if mana affordable and creature can attack this turn, casts with dash and sets `resolved=True`; otherwise casts normally

## Edge Cases
1. **End-step return timing** — CR 702.109a specifies "beginning of the next end step"; must track which creatures were dashed to trigger return correctly
2. **Haste grant conditional on dash cost** — Creature only has haste if dash cost was paid; normal casting doesn't grant haste
3. **Permanent leaves battlefield before end step** — If dashed creature is destroyed or exiled, the delayed trigger still attempts to return it (but may fizzle if card not in hand)

## Related Keywords
- **Ninjutsu (702.49)**: Also allows alternate casting with immediate attack but requires returning an attacker
- **Haste**: Dash grants haste conditionally; other sources of haste are permanent until removed
- **Dash and summoning sickness** — Dashed creatures bypass summoning sickness due to granted haste

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_dash_choice` set with card info, cost, resolved=False | CR 702.109a |
| 2 | AI player — auto-resolves when beneficial | Dash cost paid, haste granted, creature tracked for return, `resolved=True` | CR 702.109a |
| 3 | AI player — skips when not beneficial | Normal cast, no haste grant, no tracking, `resolved=True` | CR 702.109a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Dash {2}{R}" | — |
| 6 | End-step return trigger | Dashed creature returned to hand at beginning of next end step | CR 702.109a |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/dash.py`
- [x] Detection & parsing functions implemented (`parse_dash_cost`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState fields added (`pending_dash_choice: Optional[dict] = None`, `dashed_creatures: dict`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (8 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into casting flow and end-step trigger
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

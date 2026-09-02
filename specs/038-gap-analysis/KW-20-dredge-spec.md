# KW-20 Dredge Design Spec

## CR Reference
- **CR Section**: 702.52 Dredge
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.52a Dredge is a static ability that functions only while the card with dredge is in a player's graveyard. "Dredge N" means "As long as you have at least N cards in your library, if you would draw a card, you may instead mill N cards and return this card from your graveyard to your hand."
> 
> 702.52b A player with fewer cards in their library than the number required by a dredge ability can't mill any of them this way.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Replacement effect (static ability)

## Behavior Summary
Dredge is a replacement effect that triggers when a player would draw a card and the dredge card is in their graveyard. If the player has at least N cards in their library, they may choose to mill N cards instead of drawing, and return the dredge card from graveyard to hand. This effectively "recycles" dead cards back into play while sacrificing library depth. The ability only functions from graveyard — it doesn't apply if the card is elsewhere.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bdredge\s+(\d+)"` — extracts N value from "Dredge N" pattern
- **Cost/count extraction**: `parse_dredge_value(oracle_text) -> int | None` returns the mill count N
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Dredge" and no explicit N; parsing functions return defaults

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_dredge_choice on GameState
    # For AI player: auto-resolves based on library size
```

### State Tracking
- **GameState field(s)** used: `pending_dredge_choice: Optional[dict]` — contains `player`, `card_name`, `dredge_n`, `resolved`
- **PlayerState field(s)** used: None (library and graveyard modified during resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_dredge_choice` on GameState with `resolved=False`; API handler resolves choice (`dredge_pay` or `dredge_skip`)
- **AI player**: Auto-resolves using library size heuristic; if library has >= N cards, mills and returns card to hand, sets `resolved=True`; if not, sets `resolved=True` without milling

## Edge Cases
1. **Library size exactly equals N** — CR 702.52a allows dredging when library has "at least N" cards; implementation must handle exact boundary correctly
2. **Multiple dredge cards in graveyard** — Each card's dredge ability functions independently; player may choose which to activate per draw event
3. **Library size check timing** — CR 702.52b prevents milling if library has fewer than N cards at the time of the replacement decision

## Related Keywords
- **Delve (702.66)**: Also uses graveyard exile but for cost reduction rather than draw replacement
- **Recoup**: Similar "exile from graveyard to reduce costs" mechanic but not a keyword ability
- **Mill effects** — Dredge mills cards as part of the replacement; interaction with mill-based strategies

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_dredge_choice` set with card info, dredge_n, resolved=False | CR 702.52a |
| 2 | AI player — auto-resolves when library sufficient | N cards milled, card returned to hand, `resolved=True` | CR 702.52a |
| 3 | AI player — skips when library insufficient | No mill, no return, `resolved=True`, dredge not used | CR 702.52b |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Dredge 3" | — |
| 6 | Library size boundary test | Dredge works when library == N, fails when library < N | CR 702.52a/b |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/dredge.py`
- [x] Detection & parsing functions implemented (`parse_dredge_value`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (pending_dredge_choice)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (9 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into draw replacement flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

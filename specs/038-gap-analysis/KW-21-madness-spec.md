# KW-21 Madness Design Spec

## CR Reference
- **CR Section**: 702.35 Madness
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.35a Madness is a keyword that represents two abilities. The first is a static ability that functions while the card with madness is in a player's hand. The second is a triggered ability that functions when the first ability is applied. "Madness [cost]" means "If a player would discard this card, that player discards it, but exiles it instead of putting it into their graveyard" and "When this card is exiled this way, its owner may cast it by paying [cost] rather than paying its mana cost. If that player doesn't, they put this card into their graveyard."
> 
> 702.35b Casting a spell using its madness ability follows the rules for paying alternative costs in rules 601.2b and 601.2f–h.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Replacement effect + triggered ability (alternative cost)

## Behavior Summary
Madness is a two-part ability: first, it replaces the discard action with exile; second, it triggers when exiled this way, allowing the owner to cast the card by paying the madness cost instead of its mana cost. If the player chooses not to or can't pay the madness cost, the card goes to graveyard. This effectively gives a "second chance" to play cards that would otherwise be discarded.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bmadness\s*[—\-]?\s*(\{[^}]+\})"` — extracts madness cost from oracle text
- **Cost/count extraction**: `parse_madness_cost(oracle_text) -> str | None` returns the `{...}` mana cost string
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Madness" and no cost; `parse_madness_cost()` returns `None` in that case

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_madness_choice on GameState
    # For AI player: auto-resolves based on mana affordability
```

### State Tracking
- **GameState field(s)** used: `pending_madness_choice: Optional[dict]` — contains `player`, `card_name`, `madness_cost`, `resolved`
- **PlayerState field(s)** used: None (mana pool modified in-place during AI resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_madness_choice` on GameState with `resolved=False`; API handler resolves choice (`madness_pay` or `madness_skip`)
- **AI player**: Auto-resolves using `can_pay_cost(player.mana_pool, madness_cost)` heuristic; if affordable, deducts mana and sets `resolved=True`; if not, sets `resolved=True` without mana deduction

## Edge Cases
1. **Madness triggered by discard effect** — Must distinguish between voluntary discard (player choice) and forced discard (effect); both trigger madness replacement
2. **Card owner vs controller** — CR 702.35a specifies "its owner may cast it"; if card is controlled by opponent, owner still gets the option
3. **Multiple cards with madness discarded simultaneously** — Each triggers independently; player resolves each in order

## Related Keywords
- **Flashback (702.34)**: Also allows casting from graveyard but voluntary rather than discard-triggered
- **Escape (702.138)**: Graveyard casting alternative without exile requirement on leaving stack
- **Delve (702.66)**: Uses graveyard cards for cost reduction but not as a triggered ability

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_madness_choice` set with card info, cost, resolved=False | CR 702.35a |
| 2 | AI player — auto-resolves when affordable | Mana deducted from pool, `resolved=True` | CR 702.35a |
| 3 | AI player — skips when unaffordable | No mana change, card goes to graveyard, `resolved=True` | CR 702.35a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Madness {1}" | — |
| 6 | Colored mana madness cost | AI pays colored mana first, then generic from pool | CR 702.35a |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/madness.py`
- [x] Detection & parsing functions implemented (`parse_madness_cost`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (`pending_madness_choice: Optional[dict] = None`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (10 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into discard replacement flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

# KW-22 Morph Design Spec

## CR Reference
- **CR Section**: 702.37 Morph
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.37a Morph is a static ability that functions in any zone from which you could play the card it's on, and the morph effect works any time the card is face down. "Morph [cost]" means "You may cast this card as a 2/2 face-down creature with no text, no name, no subtypes, and no mana cost by paying {3} rather than paying its mana cost." (See rule 708, "Face-Down Spells and Permanents.")
> 
> 702.37c To cast a card using its morph ability, turn it face down and announce that you're using a morph ability. It becomes a 2/2 face-down creature card with no text, no name, no subtypes, and no mana cost. Any effects or prohibitions that would apply to casting a card with these characteristics (and not the face-up card's characteristics) are applied to casting this card. These values are the copiable values of that object's characteristics. Put it onto the stack (as a face-down spell with the same characteristics), and pay {3} rather than pay its mana cost. This follows the rules for paying alternative costs.
> 
> 702.37e Any time you have priority, you may turn a face-down permanent you control with a morph ability face up. This is a special action; it doesn't use the stack (see rule 116). To do this, show all players what the permanent's morph cost would be if it were face up, pay that cost, then turn the permanent face up.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Alternative cost (static ability) + special action to reveal

## Behavior Summary
Morph allows a creature card to be cast face down as a 2/2 creature with no text, name, subtypes, or mana cost by paying {3} instead of its actual mana cost. The face-down permanent can later be turned face up as a special action (doesn't use the stack) by paying its morph cost. When turned face up, it regains its normal characteristics but ETB abilities don't trigger because it already entered the battlefield.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bmorph\s*[—\-]?\s*(\{[^}]+\})"` — extracts morph cost from oracle text (typically `{3}`)
- **Cost/count extraction**: `parse_morph_cost(oracle_text) -> str | None` returns the `{...}` mana cost string
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Morph" and no explicit cost; defaults to `{3}` per CR 702.37a

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_morph_choice on GameState
    # For AI player: auto-resolves based on mana affordability and strategic value
```

### State Tracking
- **GameState field(s)** used: `pending_morph_choice: Optional[dict]` — contains `player`, `card_name`, `morph_cost`, `resolved`
- **PlayerState field(s)** used: None (mana pool modified in-place during AI resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_morph_choice` on GameState with `resolved=False`; API handler resolves choice (`morph_cast` or `morph_normal`)
- **AI player**: Auto-resolves using strategic heuristic; if mana affordable and hiding identity is beneficial, casts face down and sets `resolved=True`; otherwise casts normally

## Edge Cases
1. **Face-down permanent characteristics** — Must track that the permanent is a 2/2 with no text/name/subtypes while face down; current implementation may not fully model this state
2. **Turning face up as special action** — CR 702.37e specifies this doesn't use the stack; implementation must handle as immediate effect rather than stack-based resolution
3. **ETB abilities on face-up reveal** — CR 702.37e explicitly states ETB abilities don't trigger when turning face up because permanent already entered battlefield

## Related Keywords
- **Megamorph (702.37b)**: Variant that adds +1/+1 counter when turned face up if megamorph cost was paid; not yet implemented
- **Disguise**: Older keyword with similar face-down casting mechanic but different rules
- **Morph and targeting** — Face-down creatures can be targeted normally; their hidden identity affects blocking restrictions

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_morph_choice` set with card info, cost, resolved=False | CR 702.37a |
| 2 | AI player — auto-resolves when beneficial | Morph cost paid, permanent enters face down, `resolved=True` | CR 702.37c |
| 3 | AI player — skips when not beneficial | Normal cast, no pending state, `resolved=True` | CR 702.37a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Morph {3}" | — |
| 6 | Face-down characteristics tracking | Permanent recorded as 2/2 with no text/name/subtypes while face down | CR 702.37c |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/morph.py`
- [x] Detection & parsing functions implemented (`parse_morph_cost`, `from_oracle_text`)
- [ ] `apply()` method with human/AI paths — **STUB**: current implementation is a no-op (`return game_state`)
- [ ] GameState field added (pending_morph_choice) — TODO: add to model if not present
- [ ] Integration tests in `tests/engine/test_keywords_integration.py` — TODO: create test suite
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into casting flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

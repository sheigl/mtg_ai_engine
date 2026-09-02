# KW-{NN} {Keyword Name} Design Spec

## CR Reference
- **CR Section**: {e.g., 702.54 Hexproof}
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > [Paste exact CR rule text here]

## Keyword Type
- **Category**: {Cost | Triggered | Replacement | Passive | Static}
- **Base class**: {CostKeyword | TriggeredKeyword | PassiveKeyword}
- **CR classification**: {e.g., "Additional cost", "Triggered ability", "Static ability"}

## Behavior Summary
{1-2 paragraph plain-language description of what the keyword does, when it fires, and how it resolves. Include any timing restrictions or conditions.}

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: {patterns used to detect this keyword in oracle text}
- **Cost/count extraction**: {how numeric values or costs are parsed from the rule text}
- **Plain keyword fallback**: {does `from_oracle_text()` handle cards with just the keyword name and no cost?}

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> GameState:
    # or tuple[GameState, AdditionalData] if returning extra data
```

### State Tracking
- **GameState field(s)** used: {e.g., `pending_<keyword>_choice`, `dashed_creatures`}
- **PlayerState field(s)** used: {if any}
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `{pending_<keyword>_choice}` on GameState; API handler resolves choice
- **AI player**: Auto-resolves using heuristic (describe logic: mana affordability, library size, etc.)

## Edge Cases
1. {Edge case 1 — e.g., "Card leaves battlefield before trigger resolves"}
2. {Edge case 2}
3. {Edge case 3}

## Related Keywords
- **{Related Keyword 1}**: {How they interact or differ — e.g., "Flashback also exiles card, Escape requires graveyard exile count"}
- **{Related Keyword 2}**: {Interaction note}

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_<keyword>_choice` set on GameState | CR XXX.XXa |
| 2 | AI player — auto-resolves when affordable | Mana deducted, effect applied | CR XXX.XXb |
| 3 | AI player — skips when unaffordable | No mana change, no pending state | CR XXX.XXc |
| 4 | Pure transform verified | Original GameState unchanged | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True | — |
| 6 | Detection: plain keyword only | `parse_*_cost()` returns None, detection still works | — |

## Implementation Status
- [ ] Module created at `mtg_engine/ability/keywords/{keyword}.py`
- [ ] Detection & parsing functions implemented
- [ ] `apply()` method with human/AI paths
- [ ] GameState field(s) added (if needed)
- [ ] Integration tests in `tests/engine/test_keywords_integration.py`
- [ ] Stacked in `stack.py` effect resolution (if triggered/cost keyword)
- [ ] API handler for human choice resolution (if applicable)

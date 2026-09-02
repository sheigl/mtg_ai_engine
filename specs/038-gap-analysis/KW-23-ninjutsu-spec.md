# KW-23 Ninjutsu Design Spec

## CR Reference
- **CR Section**: 702.49 Ninjutsu
- **Source**: `specs/comprehensive_rules.txt` (Effective June 19, 2026)
- **Full text**: > 702.49a Ninjutsu is an activated ability that functions only while the card with ninjutsu is in a player's hand. "Ninjutsu [cost]" means "[Cost], Reveal this card from your hand, Return an unblocked attacking creature you control to its owner's hand: Put this card onto the battlefield from your hand tapped and attacking."
> 
> 702.49b The card with ninjutsu remains revealed from the time the ability is announced until the ability leaves the stack.
> 
> 702.49c The creature put onto the battlefield with the ninjutsu ability enters attacking the same player, planeswalker, or battle as the creature that was returned to its owner's hand.

## Keyword Type
- **Category**: Cost
- **Base class**: `CostKeyword`
- **CR classification**: Activated ability (functions from hand)

## Behavior Summary
Ninjutsu is an activated ability that allows a player to put a creature onto the battlefield tapped and attacking by returning an unblocked attacking creature they control to its owner's hand. The ninjutsu card enters attacking the same target as the returned creature. This effectively "swaps" an attacking creature for a new one from hand, maintaining the attack while potentially changing the attacker's characteristics.

## Implementation Details

### Detection & Parsing
- **Regex pattern(s)**: `r"\bninjutsu\s*[—\-]?\s*(\{[^}]+\})"` — extracts ninjutsu cost from oracle text
- **Cost/count extraction**: `parse_ninjutsu_cost(oracle_text) -> str | None` returns the `{...}` mana cost string
- **Plain keyword fallback**: `from_oracle_text()` handles cards with just "Ninjutsu" and no explicit cost; parsing functions return defaults

### Apply Method Signature
```python
def apply(self, game_state: GameState, permanent: Permanent, **kwargs) -> tuple[GameState, Card | None]:
    # Returns new GameState via model_copy(update={...})
    # For human player: queues pending_ninjutsu_choice on GameState
    # For AI player: auto-resolves by finding unblocked attacking creature
```

### State Tracking
- **GameState field(s)** used: `pending_ninjutsu_choice: Optional[dict]` — contains `player`, `card_name`, `attacker_perm_id`, `defending_player`, `resolved`
- **PlayerState field(s)** used: None (battlefield and hand modified during resolution)
- **Pure transform**: Yes — returns new GameState via `model_copy(update={...})`

### Human vs AI Path
- **Human player**: Queues `pending_ninjutsu_choice` on GameState with `resolved=False`; API handler resolves choice (`ninjutsu_activate` or `ninjutsu_skip`)
- **AI player**: Auto-resolves by finding an unblocked attacking creature, returning it to hand, putting ninja creature onto battlefield tapped and attacking same target

## Edge Cases
1. **No unblocked attackers available** — Ninjutsu cannot be activated if there are no unblocked attacking creatures controlled by the player
2. **Attacking planeswalker vs player** — CR 702.49c specifies ninjutsu creature attacks same target as returned creature; must track defending player/planeswalker correctly
3. **Commander ninjutsu variant (702.49d)**: Allows activation from command zone in addition to hand; not yet implemented

## Related Keywords
- **Dash (702.109)**: Also allows alternate casting with haste but doesn't require returning an attacker
- **Morph (702.37)**: Face-down casting alternative that can also enter attacking
- **Ninjutsu and blocking** — Returned creature is no longer attacking; ninjutsu creature enters tapped and attacking

## Test Scenarios
| # | Scenario | Expected Behavior | CR Citation |
|---|----------|------------------|-------------|
| 1 | Human player — queues pending choice | `pending_ninjutsu_choice` set with card info, attacker_perm_id, resolved=False | CR 702.49a |
| 2 | AI player — auto-resolves when unblocked attacker exists | Attacker returned to hand, ninja enters tapped/attacking, `resolved=True` | CR 702.49a |
| 3 | AI player — skips when no unblocked attackers | No activation, card stays in hand, `resolved=True` | CR 702.49a |
| 4 | Pure transform verified | Original GameState unchanged after apply() | — |
| 5 | Detection: full keyword text | `from_oracle_text()` returns True for "Ninjutsu {1}{U}" | — |
| 6 | Attacking target preservation | Ninja creature attacks same player/planeswalker as returned attacker | CR 702.49c |

## Implementation Status
- [x] Module created at `mtg_engine/ability/keywords/ninjutsu.py`
- [x] Detection & parsing functions implemented (`parse_ninjutsu_cost`, `from_oracle_text`)
- [x] `apply()` method with human/AI paths
- [x] GameState field added (`pending_ninjutsu_choice: Optional[dict] = None`)
- [x] Integration tests in `tests/engine/test_keywords_integration.py` (6 tests)
- [ ] Stacked in `stack.py` effect resolution — TODO: wire into combat phase activation flow
- [ ] API handler for human choice resolution — TODO: add to `_compute_legal_actions` and choice router

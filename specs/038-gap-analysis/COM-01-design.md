# COM-01 Companion Mutability Fix Design

## Problem
`activate_companion()` in `companion.py` has multiple direct mutations:
- Line 84: `setattr(player.mana_pool, color, ...)` — mutates mana_pool directly
- Line 90: `player.sideboard.remove(companion_card)` — mutates sideboard list
- Line 91: `player.hand.append(companion_card)` — mutates hand list
- Line 94: `game_state.companion_used[player_name] = True` — mutates companion_used dict

## Fix Plan

### 1. Rewrite `mtg_engine/engine/companion.py` — `activate_companion()`

Change signature from `-> Optional[Card]` to `-> tuple[GameState, Card | None]`.
All mutations replaced with model_copy transforms:

```python
def activate_companion(game_state: GameState, player_name: str) -> tuple[GameState, Card | None]:
    """
    Activate the companion ability: pay {3} and put companion from sideboard into hand.
    Returns (new_game_state, companion_card_or_None).
    Once-per-game restriction enforced via companion_used tracking.
    """
    # Check once-per-game restriction
    if game_state.companion_used.get(player_name):
        logger.info("Companion: %s already used companion this game", player_name)
        return game_state, None

    player = next((p for p in game_state.players if p.name == player_name), None)
    if player is None:
        return game_state, None

    # Find a valid companion in sideboard
    companion_card = None
    for card in player.sideboard:
        if has_companion(card) and check_companion_restriction(game_state, player_name, card):
            companion_card = card
            break

    if companion_card is None:
        logger.info("Companion: %s has no valid companion in sideboard", player_name)
        return game_state, None

    # Pay {3} (deduct from mana pool) — build new ManaPool via model_copy
    total_mana = sum(getattr(player.mana_pool, c, 0) or 0 for c in ["W", "U", "B", "R", "G", "C"])
    if total_mana < 3:
        logger.info("Companion: %s doesn't have enough mana to activate", player_name)
        return game_state, None

    # Deduct {3} generically (prefer colorless first, then any other)
    new_mana = player.mana_pool.model_copy()
    remaining = 3
    for color in ["C", "W", "U", "B", "R", "G"]:
        available = getattr(new_mana, color, 0) or 0
        pay = min(remaining, available)
        setattr(new_mana, color, getattr(new_mana, color, 0) - pay)
        remaining -= pay
        if remaining <= 0:
            break

    # Move from sideboard to hand (new lists)
    new_sideboard = [c for c in player.sideboard if c is not companion_card]
    new_hand = [*player.hand, companion_card]

    # Build new player state
    new_player = player.model_copy(update={
        "mana_pool": new_mana,
        "sideboard": new_sideboard,
        "hand": new_hand,
    })

    # Build new players list
    new_players = [p if p.name != player_name else new_player for p in game_state.players]

    # Mark as used (new dict)
    new_companion_used = {**game_state.companion_used, player_name: True}

    logger.info("Companion: %s activates companion '%s'", player_name, companion_card.name)
    return game_state.model_copy(update={
        "players": new_players,
        "companion_used": new_companion_used,
    }), companion_card
```

### 2. Update existing tests in `tests/engine/test_companion.py`
- All calls to `activate_companion(gs, player)` must now unpack: `gs, card = activate_companion(gs, player)`
- Add immutability assertions: verify original GameState unchanged after activation

### 3. Create integration test suite at `tests/engine/test_companion_integration.py`
12+ integration tests covering:
- Successful activation with full state transform verification
- Immutability: original GameState, PlayerState, ManaPool all unchanged
- Once-per-game restriction via companion_used tracking
- Multi-player independent companion usage
- Activation failure cases (no mana, no companion, restriction not met)

## Acceptance Criteria
- `activate_companion()` returns `(GameState, Card | None)` — no direct mutations
- All 18 existing unit tests pass with updated unpacking + immutability assertions
- New integration test file passes all tests
- Full test suite: no regressions

"""
Companion mechanic (COM-01).
CR 702.148: Companion.

- Once per game, any time you could cast a sorcery, you may pay {3} and put your
  companion from outside the game into your hand if you meet all restrictions.
- Restrictions are printed on the card (e.g., "You own fewer than 40 cards").
"""
import logging
from typing import Optional

from mtg_engine.models.game import GameState, Card

logger = logging.getLogger(__name__)


def has_companion(card: Card) -> bool:
    """Check if a card has the Companion keyword."""
    return "companion" in [(k or "").lower() for k in (card.keywords or [])]


def check_companion_restriction(game_state: GameState, player_name: str, card: Card) -> bool:
    """
    Check whether the companion's restriction is satisfied.

    Parses oracle text for common restrictions:
      - "You own fewer than N cards" → checks hand + library count
      - Default: True (no known restriction)
    """
    oracle = (card.oracle_text or "").lower()

    import re
    match = re.search(r"you own fewer than (\d+) cards", oracle)
    if match:
        threshold = int(match.group(1))
        player = next((p for p in game_state.players if p.name == player_name), None)
        if player is None:
            return False
        owned = len(player.hand) + len(player.library)
        return owned < threshold

    return True


def activate_companion(game_state: GameState, player_name: str) -> Optional[Card]:
    """
    Activate the companion ability: pay {3} and put companion from sideboard into hand.

    Once per game restriction is enforced via companion_used tracking.

    Returns the companion card moved to hand, or None if activation failed.
    """
    # Check once-per-game restriction
    if game_state.companion_used.get(player_name):
        logger.info("Companion: %s already used companion this game", player_name)
        return None

    player = next((p for p in game_state.players if p.name == player_name), None)
    if player is None:
        return None

    # Find a valid companion in sideboard
    companion_card = None
    for card in list(player.sideboard):
        if has_companion(card) and check_companion_restriction(game_state, player_name, card):
            companion_card = card
            break

    if companion_card is None:
        logger.info("Companion: %s has no valid companion in sideboard", player_name)
        return None

    # Pay {3} (deduct from mana pool)
    total_mana = player.mana_pool.W + player.mana_pool.U + player.mana_pool.B + player.mana_pool.R + player.mana_pool.G + player.mana_pool.C
    if total_mana < 3:
        logger.info("Companion: %s doesn't have enough mana to activate", player_name)
        return None

    # Deduct {3} generically (prefer colorless first, then any other)
    remaining = 3
    for color in ["C", "W", "U", "B", "R", "G"]:
        available = getattr(player.mana_pool, color, 0) or 0
        pay = min(remaining, available)
        setattr(player.mana_pool, color, getattr(player.mana_pool, color, 0) - pay)
        remaining -= pay
        if remaining <= 0:
            break

    # Move from sideboard to hand
    player.sideboard.remove(companion_card)
    player.hand.append(companion_card)

    # Mark as used
    game_state.companion_used[player_name] = True

    logger.info("Companion: %s activates companion '%s'", player_name, companion_card.name)
    return companion_card


def get_companion_from_sideboard(game_state: GameState, player_name: str) -> Optional[Card]:
    """Return the first valid companion in a player's sideboard, or None."""
    player = next((p for p in game_state.players if p.name == player_name), None)
    if player is None:
        return None

    for card in player.sideboard:
        if has_companion(card):
            return card
    return None


def can_activate_companion(game_state: GameState, player_name: str) -> bool:
    """Check whether a player can activate their companion right now."""
    if game_state.companion_used.get(player_name):
        return False

    player = next((p for p in game_state.players if p.name == player_name), None)
    if player is None:
        return False

    total_mana = player.mana_pool.W + player.mana_pool.U + player.mana_pool.B + player.mana_pool.R + player.mana_pool.G + player.mana_pool.C
    if total_mana < 3:
        return False

    companion = get_companion_from_sideboard(game_state, player_name)
    if companion is None:
        return False

    return check_companion_restriction(game_state, player_name, companion)

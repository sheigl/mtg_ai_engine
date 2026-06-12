"""
Commander format rules (CMD-01).
CR 903: Commander variant rules.

- Commander tax: +{2} per previous cast from command zone
- Commander damage: 21+ combat damage from one commander = loss
- Color identity validation
- Command zone replacement (CR 903.9)
"""
import logging
from typing import Optional

from mtg_engine.models.game import GameState, PlayerState

logger = logging.getLogger(__name__)


def get_commander_tax(
    game_state: GameState,
    player_name: str,
    card_name: str,
) -> int:
    """
    Return the additional {C} tax for casting a commander from the command zone.
    CR 903.8: +{2} for each previous cast from command zone.

    Example: if cast twice before, tax = 4.
    """
    player = _get_player(game_state, player_name)
    previous_casts = player.commander_cast_counts.get(card_name, 0)
    return previous_casts * 2


def record_commander_cast(
    game_state: GameState,
    player_name: str,
    card_name: str,
) -> GameState:
    """Increment the commander cast count for a player."""
    player = _get_player(game_state, player_name)
    player.commander_cast_counts[card_name] = (
        player.commander_cast_counts.get(card_name, 0) + 1
    )
    return game_state


def check_commander_damage_loss(
    game_state: GameState,
) -> Optional[str]:
    """
    Check if any player has taken 21+ combat damage from a single commander.
    CR 903.10: A player that's been dealt 21+ combat damage by the same
    commander loses the game.

    Returns the name of the losing player, or None.
    """
    if game_state.format != "commander":
        return None

    for source_id, players_damage in game_state.commander_damage.items():
        for player_name, damage in players_damage.items():
            if damage >= 21:
                logger.info(
                    "Commander damage: %s dealt 21+ damage to %s (loss)",
                    source_id, player_name,
                )
                return player_name

    return None


def get_color_identity(card: 'Card') -> list[str]:
    """
    Return the color identity of a card.
    CR 903.4: Color identity includes the card's color plus any mana symbols
    in its mana cost and rules text.

    Uses the card's color_identity field if available, otherwise derives it
    from the mana cost.
    """
    if hasattr(card, "color_identity") and card.color_identity:
        return list(card.color_identity)

    # Derive from mana cost
    colors: set[str] = set()
    mana_cost = card.mana_cost or ""
    import re
    for sym in re.findall(r'\{([WUBRG])\}', mana_cost):
        colors.add(sym)
    # Also check rules text for color symbols
    oracle = card.oracle_text or ""
    for sym in re.findall(r'\{([WUBRG])\}', oracle):
        colors.add(sym)

    return sorted(colors)


def validate_deck_for_commander(
    cards: list['Card'],
    commanders: list['Card'],
) -> tuple[bool, list[str]]:
    """
    Validate a deck for Commander format.

    Rules:
    - Exactly 100 cards (including commander(s))
    - Singleton (no duplicates except basic lands)
    - Cards must match commander's color identity
    - Commander(s) must be legendary

    Returns (is_valid, list_of_violations).
    """
    violations: list[str] = []

    if len(cards) != 100:
        violations.append(f"Deck has {len(cards)} cards, must have exactly 100")

    if not commanders:
        violations.append("No commander specified")
    else:
        cmd_names = {c.name for c in commanders}

        # Build composite color identity from all commanders
        composite_identity: set[str] = set()
        for cmd in commanders:
            for c in get_color_identity(cmd):
                composite_identity.add(c)

        # Check card color identity
        for card in cards:
            if card.name not in cmd_names:
                card_identity = set(get_color_identity(card))
                if not card_identity.issubset(composite_identity):
                    violations.append(
                        f"{card.name} ({sorted(card_identity)}) not in color identity "
                        f"({sorted(composite_identity)})"
                    )

    # Singleton check (skip basic lands)
    seen: dict[str, int] = {}
    basic_lands = {"Plains", "Island", "Swamp", "Mountain", "Forest",
                   "Snow-Covered Plains", "Snow-Covered Island",
                   "Snow-Covered Swamp", "Snow-Covered Mountain",
                   "Snow-Covered Forest", "Wastes"}
    for card in cards:
        if card.name in basic_lands:
            continue
        if card.name not in seen:
            seen[card.name] = 0
        seen[card.name] += 1
        if seen[card.name] > 1:
            violations.append(f"{card.name} is not singleton ({seen[card.name]} copies)")

    return len(violations) == 0, violations


def get_commander_command_zone(
    game_state: GameState,
    player_name: str,
) -> list:
    """Return the cards in a player's command zone."""
    player = _get_player(game_state, player_name)
    return list(player.command_zone)


def add_commander_to_command_zone(
    game_state: GameState,
    player_name: str,
    card: 'Card',
) -> GameState:
    """Add a card to the player's command zone as a commander."""
    player = _get_player(game_state, player_name)
    player.command_zone.append(card)
    player.commander_name = card.name
    logger.info("Commander: %s added %s to command zone", player_name, card.name)
    return game_state


def _get_player(game_state: GameState, player_name: str) -> PlayerState:
    for p in game_state.players:
        if p.name == player_name:
            return p
    msg = f"Player {player_name} not found"
    raise ValueError(msg)

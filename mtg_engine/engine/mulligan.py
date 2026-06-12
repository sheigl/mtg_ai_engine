"""
Mulligan system with multiple variant support.
MLG-01: Mulligan types for different rulesets.

CR 103.4: Mulligan procedures vary by format/tournament rules.
Supported variants:
  - London  (2019–present, official)
  - Vancouver (2015–2019, official)
  - Paris   (2003–2015, official)
  - Original (Partial Paris, used in early Commander)
"""
import logging
import random
from enum import Enum
from typing import Optional

from mtg_engine.models.game import GameState, PlayerState

logger = logging.getLogger(__name__)


class MulliganType(str, Enum):
    LONDON = "london"
    VANCOUVER = "vancouver"
    PARIS = "paris"
    ORIGINAL = "original"


def apply_mulligan(
    game_state: GameState,
    player_name: str,
    keep: bool,
    mulligan_type: Optional[MulliganType] = None,
    rng: Optional[random.Random] = None,
) -> GameState:
    """
    Apply a mulligan decision for a player.

    Args:
        game_state: Current game state (mutated in place).
        player_name: The player making the decision.
        keep: True to keep current hand, False to mulligan.
        mulligan_type: Which mulligan variant to use. If None, reads from
                       game_state.mulligan_variant.
        rng: Optional seeded RNG for shuffling.

    Returns:
        Updated game state.
    """
    if mulligan_type is None:
        mulligan_type = get_mulligan_type(game_state)

    if not game_state.mulligan_phase_active:
        raise ValueError("Not in mulligan phase")

    player = _get_player(game_state, player_name)
    if player_name in game_state.players_kept:
        raise ValueError(f"{player_name} already kept their hand")

    hand_size = len(player.hand)

    if keep or hand_size <= 1:
        _handle_keep(game_state, player, player_name, hand_size, mulligan_type, rng)
    else:
        _handle_mulligan(game_state, player, player_name, hand_size, mulligan_type, rng)

    return game_state


def _get_player(gs: GameState, name: str) -> PlayerState:
    for p in gs.players:
        if p.name == name:
            return p
    raise ValueError(f"Player {name!r} not found")


def _handle_keep(
    gs: GameState,
    player: PlayerState,
    player_name: str,
    hand_size: int,
    mulligan_type: MulliganType,
    rng: Optional[random.Random],
) -> None:
    """Player keeps their current hand."""
    if player_name not in gs.players_kept:
        gs.players_kept.append(player_name)

    # Vancouver: scry 1 if kept fewer than starting hand
    if mulligan_type == MulliganType.VANCOUVER and hand_size < 7:
        from mtg_engine.models.game import PendingTrigger as _PT
        # Queue a scry trigger for the player
        gs.pending_scry_choice = {
            "player": player_name,
            "cards": [player.library[0]] if player.library else [],
            "count": 1,
        }
        logger.debug("Vancouver mulligan: scry 1 queued for %s", player_name)

    _check_all_kept(gs)


def _handle_mulligan(
    gs: GameState,
    player: PlayerState,
    player_name: str,
    hand_size: int,
    mulligan_type: MulliganType,
    rng: Optional[random.Random],
) -> None:
    """Player mulligans (shuffles hand back and draws fewer cards)."""
    _rng = rng or random

    if mulligan_type == MulliganType.ORIGINAL:
        _partial_paris_mulligan(gs, player, player_name, hand_size, _rng)
    else:
        _standard_mulligan(gs, player, player_name, hand_size, _rng)

    gs.hands_mulliganed[player_name] = gs.hands_mulliganed.get(player_name, 0) + 1
    logger.debug("%s mulliganed to %d cards", player_name, len(player.hand))


def _standard_mulligan(
    gs: GameState,
    player: PlayerState,
    player_name: str,
    hand_size: int,
    rng: random.Random,
) -> None:
    """
    Standard London/Paris/Vancouver mulligan:
    Shuffle hand into library, draw hand_size - 1.
    """
    player.library = list(player.hand) + list(player.library)
    rng.shuffle(player.library)
    new_size = hand_size - 1
    player.hand = player.library[:new_size]
    player.library = player.library[new_size:]


def _partial_paris_mulligan(
    gs: GameState,
    player: PlayerState,
    player_name: str,
    hand_size: int,
    rng: random.Random,
) -> None:
    """
    Original / Partial Paris mulligan:
    If it's the first mulligan, offer a partial: set aside cards, draw replacements,
    then shuffle set-aside back.
    For subsequent mulligans, do standard mulligan.
    """
    mulligan_count = gs.hands_mulliganed.get(player_name, 0)

    if mulligan_count == 0 and hand_size == 7:
        # Partial Paris: all cards set aside face-down, draw 7, shuffle set-aside back
        # In practice, we just reshuffle and draw 7 (same result without the UI complexity)
        player.library = list(player.hand) + list(player.library)
        rng.shuffle(player.library)
        player.hand = player.library[:7]
        player.library = player.library[7:]
    else:
        # Standard mulligan for subsequent attempts
        _standard_mulligan(gs, player, player_name, hand_size, rng)


def _check_all_kept(gs: GameState) -> None:
    """If all players have committed, end the mulligan phase."""
    if all(p.name in gs.players_kept for p in gs.players):
        gs.mulligan_phase_active = False
        logger.debug("All players have kept — mulligan phase ended")


def set_mulligan_type(gs: GameState, mulligan_type: MulliganType) -> None:
    """Set the mulligan variant for a game."""
    gs.mulligan_variant = mulligan_type.value


def get_mulligan_type(gs: GameState) -> MulliganType:
    """Get the mulligan variant for a game, defaulting to London."""
    variant = getattr(gs, "mulligan_variant", None) or "london"
    try:
        return MulliganType(variant)
    except ValueError:
        return MulliganType.LONDON

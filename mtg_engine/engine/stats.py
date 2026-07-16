"""
Pure engine functions for player stats and ELO calculation. Feature APP-06.
No database access — all functions are stateless transforms.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from mtg_engine.models.stats import FormatRecord, MatchupRecord, PlayerStats

logger = logging.getLogger(__name__)


def calculate_new_elo(current_elo: int, opponent_elo: int, won: bool, K: int = 32) -> int:
    """Standard ELO rating update.

    Args:
        current_elo: The player's current ELO rating.
        opponent_elo: The opponent's current ELO rating.
        won: True if the player won, False if they lost.
        K: K-factor (default 32 for standard play).

    Returns:
        Updated ELO rating (rounded to nearest integer).
    """
    expected = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 400))
    actual = 1 if won else 0
    return round(current_elo + K * (actual - expected))


def update_player_stats(
    stats: PlayerStats,
    opponent_name: str,
    opponent_elo: int,
    won: bool,
    format_name: str = "standard",
) -> PlayerStats:
    """Return a new PlayerStats with updated wins/losses/ELO/matchup/format.

    This is a pure transform — the input stats object is never mutated.

    Args:
        stats: Current player stats (will not be modified).
        opponent_name: Name of the opposing player.
        opponent_elo: Opponent's current ELO rating (for calculation).
        won: True if this player won, False for a loss.
        format_name: MTG format name (e.g. "commander", "standard").

    Returns:
        New PlayerStats instance with all counters incremented and ELO updated.
    """
    new_elo = calculate_new_elo(stats.elo, opponent_elo, won)

    # Update wins/losses
    new_wins = stats.wins + (1 if won else 0)
    new_losses = stats.losses + (0 if won else 1)

    # Update format record — deep copy to avoid mutating original (CRITICAL fix)
    formats = {k: v.model_copy() for k, v in stats.formats.items()}
    fmt = formats.get(format_name, FormatRecord())
    fmt.wins += 1 if won else 0
    fmt.losses += 0 if won else 1
    formats[format_name] = fmt

    # Update matchup record
    matchups = {k: v.model_copy() for k, v in stats.matchups.items()}
    existing = matchups.get(opponent_name)
    if existing is None:
        existing = MatchupRecord(opponent=opponent_name)
        matchups[opponent_name] = existing
    existing.wins += 1 if won else 0
    existing.losses += 0 if won else 1

    return stats.model_copy(
        update={
            "elo": new_elo,
            "wins": new_wins,
            "losses": new_losses,
            "formats": formats,
            "matchups": matchups,
            "updated_at": datetime.now(timezone.utc),
        }
    )

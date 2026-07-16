"""
AI combat decision helpers (AI-02).

Provides combat-specific scoring and decision functions used by the
heuristic AI and available for direct use in AI tests and training data.
"""
from enum import Enum
from typing import Optional

from ai_client.heuristic_player import _can_block, _perm_power, _perm_toughness
from ai_client.models import PlayerConfig


class BlockClassification(Enum):
    SAFE = "safe"
    TRADE = "trade"
    CHUMP = "chump"


def compute_power(permanent: dict) -> int:
    """Return the current power of a permanent (including counters/bonuses)."""
    return _perm_power(permanent)


def compute_toughness(permanent: dict) -> int:
    """Return the current toughness of a permanent (including counters/bonuses)."""
    return _perm_toughness(permanent)


def can_block(blocker: dict, attacker: dict) -> bool:
    """Return True if blocker can legally block attacker (flying, reach, etc.)."""
    return _can_block(blocker, attacker)


def classify_block(blocker: dict, attacker: dict) -> BlockClassification:
    """
    Classify a potential block into SAFE / TRADE / CHUMP.

    - SAFE:  blocker's power >= attacker's toughness and blocker survives
    - TRADE: blocker dies and attacker dies (mutual lethal)
    - CHUMP: only blocker dies
    """
    b_power = compute_power(blocker)
    b_tough = compute_toughness(blocker)
    a_power = compute_power(attacker)
    a_tough = compute_toughness(attacker)

    blocker_kills = b_power >= a_tough
    attacker_kills = a_power >= b_tough

    if blocker_kills and not attacker_kills:
        return BlockClassification.SAFE
    if blocker_kills and attacker_kills:
        return BlockClassification.TRADE
    return BlockClassification.CHUMP


def simulate_combat(
    attacker_permanents: list[dict],
    blocker_permanents: list[dict],
    opponent_life: int,
) -> float:
    """
    Simulate a combat round and return a score (higher = better for attacker).

    Creates a lightweight heuristic player internally to run the simulation.
    """
    from ai_client.heuristic_player import HeuristicPlayer
    from ai_client.models import AiPersonalityProfile
    config = PlayerConfig(
        name="_sim",
        player_type="heuristic",
        personality=AiPersonalityProfile.DEFAULT,
    )
    player = HeuristicPlayer(config)
    return player._simulate_combat(attacker_permanents, blocker_permanents, opponent_life)

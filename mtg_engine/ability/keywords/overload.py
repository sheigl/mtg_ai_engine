import re
from typing import Optional
from pydantic import BaseModel, Field


def parse_overload_cost(oracle_text: str) -> Optional[str]:
    """Extract the overload cost from oracle text.

    Handles: 'Overload {3}', 'Overload {2}{R}'
    Returns None if no overload keyword.
    """
    if not oracle_text:
        return None
    # Match "Overload" followed by one or more mana symbols {X}
    m = re.search(r"Overload\s+((?:\{[^}]+\})+)", oracle_text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def has_overload(oracle_text: str) -> bool:
    """Check if a card has the overload keyword."""
    if not oracle_text:
        return False
    return "overload" in oracle_text.lower()


class OverloadModel(BaseModel):
    name: str = ""
    overload_cost: Optional[str] = None
    type_line: str = ""
    oracle_text: str = ""
    overload_paid: bool = False

    @staticmethod
    def from_oracle_text(name: str, oracle_text: str, type_line: str) -> "OverloadModel":
        overload_cost = parse_overload_cost(oracle_text)
        return OverloadModel(
            name=name,
            overload_cost=overload_cost,
            type_line=type_line,
            oracle_text=oracle_text,
        )

    @property
    def is_overloaded(self) -> bool:
        return self.overload_paid and self.overload_cost is not None


def get_overload_targets(oracle_text: str, game_state) -> list[str]:
    """Get all valid targets for an overloaded spell.

    For overloaded spells, target ALL appropriate permanents/players instead of just one.
    """
    if not oracle_text:
        return []

    # Determine what the spell targets
    targets = []
    oracle_lower = oracle_text.lower()

    if "destroy target creature" in oracle_lower or "destroy all creatures" in oracle_lower:
        # Target all creatures on battlefield
        targets = [p.id for p in game_state.battlefield if "creature" in p.card.type_line.lower()]

    elif "target opponent" in oracle_lower:
        # For overloaded, target all opponents
        for player in game_state.players:
            if player.name != game_state.active_player:
                targets.append(player.name)

    elif "target permanent" in oracle_lower:
        # Target all permanents on battlefield
        targets = [p.id for p in game_state.battlefield]

    return targets

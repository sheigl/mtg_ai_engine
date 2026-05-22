"""Shroud keyword (CR 702.36).

Shroud is a static ability that prevents all targeting:
- A permanent with shroud can't be the target of any spell or ability,
  including its own controller's.
"""
from mtg_engine.ability.keywords.base import PassiveKeyword


class Shroud(PassiveKeyword):
    """Shroud keyword ability (CR 702.36).

    CR 702.36b: A permanent with shroud can't be the target of spells
    or abilities. Neither opponent nor controller can target it.
    """

    name = "shroud"

    @staticmethod
    def has_shroud(keywords: list[str]) -> bool:
        """Check if a card has the shroud keyword."""
        return "shroud" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains shroud keyword."""
        if not oracle_text:
            return False
        return "shroud" in oracle_text.lower()

    @staticmethod
    def can_be_targeted(target_keywords: list[str]) -> bool:
        """Check if the permanent can be targeted by anyone.

        A shrouded permanent can never be targeted.
        CR 702.36b.

        Args:
            target_keywords: Keywords of the target permanent.

        Returns:
            True if the permanent can be legally targeted (always False if shrouded).
        """
        return not Shroud.has_shroud(target_keywords)

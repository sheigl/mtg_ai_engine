"""Hexproof keyword (CR 702.15).

Hexproof is a static ability that prevents targeting:
- A permanent with hexproof can't be the target of spells or abilities
  an opponent controls.
- The permanent's controller can still target it.
"""
from mtg_engine.ability.keywords.base import PassiveKeyword


class Hexproof(PassiveKeyword):
    """Hexproof keyword ability (CR 702.15).

    CR 702.15b: A permanent with hexproof can't be the target of spells
    or abilities that players other than its controller control.
    """

    name = "hexproof"

    @staticmethod
    def has_hexproof(keywords: list[str]) -> bool:
        """Check if a card has the hexproof keyword."""
        return "hexproof" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains hexproof keyword."""
        if not oracle_text:
            return False
        return "hexproof" in oracle_text.lower()

    @staticmethod
    def can_be_targeted(
        target_keywords: list[str],
        source_controller: str,
        target_controller: str,
    ) -> bool:
        """Check if the permanent can be targeted.

        A hexproof permanent can only be targeted by its own controller.
        CR 702.15b.

        Args:
            target_keywords: Keywords of the target permanent.
            source_controller: Name of the controller of the spell/ability.
            target_controller: Name of the controller of the target permanent.

        Returns:
            True if the permanent can be legally targeted.
        """
        if not Hexproof.has_hexproof(target_keywords):
            return True
        return source_controller == target_controller

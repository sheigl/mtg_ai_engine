"""Lifelink keyword (CR 702.15).

Lifelink is a static ability that modifies damage events:
- Whenever a source with lifelink deals damage, its controller gains that much life.
- Applies to combat damage and non-combat damage equally.
"""
from mtg_engine.ability.keywords.base import PassiveKeyword


class Lifelink(PassiveKeyword):
    """Lifelink keyword ability (CR 702.15).

    CR 702.15b: Whenever a source you control with lifelink deals damage,
    you gain that much life.
    """

    name = "lifelink"

    @staticmethod
    def has_lifelink(keywords: list[str]) -> bool:
        """Check if a card has the lifelink keyword."""
        return "lifelink" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains lifelink keyword."""
        if not oracle_text:
            return False
        return "lifelink" in oracle_text.lower()

    @staticmethod
    def apply_lifelink_gain(controller_life: int, damage: int) -> int:
        """Calculate life gain from lifelink.

        Args:
            controller_life: Current life total of the source's controller.
            damage: Amount of damage dealt by the lifelink source.

        Returns:
            New life total after gaining life equal to damage.
        """
        return controller_life + damage

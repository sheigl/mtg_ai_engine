"""Deathtouch keyword (CR 702.2).

Deathtouch is a static ability that modifies damage marking:
- Any nonzero amount of damage from a source with deathtouch is considered lethal.
- The damaged creature is destroyed by state-based actions (CR 704.5h).
"""
from mtg_engine.ability.keywords.base import PassiveKeyword


class Deathtouch(PassiveKeyword):
    """Deathtouch keyword ability (CR 702.2).

    CR 702.2b: Any amount of damage greater than 0 that's dealt to a creature
    by a source with deathtouch is considered to be lethal damage.
    CR 702.2c: The damage marked on that creature is considered to be lethal
    regardless of toughness.
    """

    name = "deathtouch"

    @staticmethod
    def has_deathtouch(keywords: list[str]) -> bool:
        """Check if a card has the deathtouch keyword."""
        return "deathtouch" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains deathtouch keyword."""
        if not oracle_text:
            return False
        return "deathtouch" in oracle_text.lower()

    @staticmethod
    def is_lethal(damage: int, target_toughness: int) -> bool:
        """Check if damage is lethal given deathtouch.

        With deathtouch, any nonzero damage is lethal regardless of toughness.
        CR 702.2c.

        Args:
            damage: Amount of damage dealt by the deathtouch source.
            target_toughness: Toughness of the damaged creature (unused with deathtouch).

        Returns:
            True if the damage is lethal (always true for damage > 0).
        """
        return damage > 0

    @staticmethod
    def min_lethal_damage() -> int:
        """Return minimum damage needed to be lethal with deathtouch.

        With deathtouch, 1 damage is always lethal.
        """
        return 1

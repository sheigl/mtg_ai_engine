"""Menace keyword (CR 702.45).

Menace is a static ability that modifies blocking rules:
- A creature with menace can't be blocked by fewer than two creatures.
"""
from mtg_engine.ability.keywords.base import PassiveKeyword


class Menace(PassiveKeyword):
    """Menace keyword ability (CR 702.45).

    CR 702.45b: An attacking creature with menace can't be blocked unless
    it's blocked by at least two creatures.
    """

    name = "menace"

    @staticmethod
    def has_menace(keywords: list[str]) -> bool:
        """Check if a card has the menace keyword."""
        return "menace" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains menace keyword."""
        if not oracle_text:
            return False
        return "menace" in oracle_text.lower()

    @staticmethod
    def min_blockers() -> int:
        """Return minimum number of blockers required for a creature with menace.

        A creature with menace must be blocked by at least 2 creatures.
        CR 702.45b.
        """
        return 2

    @staticmethod
    def is_block_legal(attacker_keywords: list[str], num_blockers: int) -> bool:
        """Check if a blocking declaration is legal given menace.

        Args:
            attacker_keywords: Keywords of the attacking creature.
            num_blockers: Number of creatures blocking this attacker.

        Returns:
            True if the block is legal (either no menace or 2+ blockers).
        """
        if not Menace.has_menace(attacker_keywords):
            return True
        return num_blockers >= Menace.min_blockers()

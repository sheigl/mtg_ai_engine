"""Reach keyword (CR 702.160).

Reach is a static ability that modifies blocking rules:
- A creature with reach can block creatures with flying.
- Without reach, only creatures with flying can block other flying creatures.
"""
from mtg_engine.ability.keywords.base import PassiveKeyword


class Reach(PassiveKeyword):
    """Reach keyword ability (CR 702.160).

    CR 702.160b: Creatures with flying or reach can block creatures with flying,
    ignoring the normal restriction that only flying creatures can block flying creatures.
    """

    name = "reach"

    @staticmethod
    def has_reach(keywords: list[str]) -> bool:
        """Check if a card has the reach keyword."""
        return "reach" in [k.lower() for k in keywords]

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains reach keyword."""
        if not oracle_text:
            return False
        return "reach" in oracle_text.lower()

    @staticmethod
    def can_block_flying(blocker_keywords: list[str]) -> bool:
        """Check if a blocker can block a flying creature.

        A creature can block flying if it has flying or reach.
        CR 702.9b, CR 702.160b.

        Args:
            blocker_keywords: Keywords of the blocking creature.

        Returns:
            True if the blocker can block a flying creature.
        """
        kw_lower = [k.lower() for k in blocker_keywords]
        return "flying" in kw_lower or "reach" in kw_lower

import re
from typing import Optional
from pydantic import BaseModel, Field


class InfectKeyword:
    """Infect keyword (CR 702.90).

    Infect is a static ability that modifies how damage is dealt:
    - Damage to creatures causes -1/-1 counters instead of marked damage
    - Damage to players causes poison counters instead of life loss
    - Damage to planeswalkers reduces loyalty normally (infect doesn't affect this)
    """

    NAME = "infect"

    @staticmethod
    def has_infect(keywords: list[str]) -> bool:
        """Check if a card has the infect keyword."""
        return InfectKeyword.NAME in keywords

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains infect keyword."""
        if not oracle_text:
            return False
        return "infect" in oracle_text.lower()


class WitherKeyword:
    """Wither keyword (CR 702.129).

    Wither is similar to infect but only applies to creatures:
    - Damage to creatures causes -1/-1 counters instead of marked damage
    - Damage to players is normal (life loss, not poison)
    - Damage to planeswalkers reduces loyalty normally
    """

    NAME = "wither"

    @staticmethod
    def has_wither(keywords: list[str]) -> bool:
        """Check if a card has the wither keyword."""
        return WitherKeyword.NAME in keywords

    @staticmethod
    def from_oracle_text(oracle_text: str) -> bool:
        """Check if oracle text contains wither keyword."""
        if not oracle_text:
            return False
        return "wither" in oracle_text.lower()


class PoisonousKeyword(BaseModel):
    """Poisonous keyword (CR 702.118).

    Poisonous N — Whenever this creature deals combat damage to a player,
    that player gets N poison counters.
    """

    name: str = "poisonous"
    poison_amount: int = 0

    @staticmethod
    def from_oracle_text(oracle_text: str) -> Optional["PoisonousKeyword"]:
        """Parse poisonous N from oracle text."""
        if not oracle_text:
            return None
        m = re.search(r"poisonous\s+(\d+)", oracle_text.lower())
        if m:
            return PoisonousKeyword(poison_amount=int(m.group(1)))
        return None

    def apply(self, game_state, source_id: str, target_player_name: str) -> None:
        """Apply poisonous effect - add poison counters to player."""
        for player in game_state.players:
            if player.name == target_player_name:
                old_count = player.poison_counters
                player.poison_counters += self.poison_amount
                if player.poison_counters >= 10:
                    player.has_lost = True

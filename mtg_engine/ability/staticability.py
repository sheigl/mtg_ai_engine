"""
Static abilities - continuous effects that modify game state.

Phase STA: Like Forge's StaticAbility system.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Permanent

logger = logging.getLogger(__name__)


class StaticAbility(ABC):
    """Base class for static abilities.
    
    Static abilities modify game state continuously without triggers.
    Examples:
    - "Creatures can't attack" (Ghostly Prison)
    - "Creatures you control have hexproof" (Archetype of Endurance)
    - "+2/+2 to all creatures" (Giant Growth)
    """
    
    @abstractmethod
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this static ability applies to the permanent.
        
        Args:
            game_state: Current game state
            permanent: Permanent to check
            
        Returns:
            True if ability affects this permanent
        """
        ...
    
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> None:
        """Apply this static ability's effect to the permanent.
        
        Args:
            game_state: Current game state
            permanent: Permanent to modify
        """
        ...


class CantAttackBlock(StaticAbility):
    """Static ability preventing attack/block.
    
    Examples:
    - "Creatures can't attack you"
    - "Creatures can't block"
    - "Creatures your opponents control can't block"
    """
    
    def __init__(self, restriction: str = "attack"):
        """Initialize with restriction type.
        
        Args:
            restriction: "attack", "block", or "both"
        """
        self.restriction = restriction
    
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if restriction applies."""
        return True  # Override with source/target checking
    
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> None:
        """Apply cant attack/block flags."""
        # This is handled by constraints system, not direct modification
        pass


class ContinuousPump(StaticAbility):
    """Static ability providing P/T pump.
    
    Examples:
    - "Other creatures you control get +1/+1"
    - "All creatures get +2/+2"
    """
    
    def __init__(self, power_bonus: int = 0, toughness_bonus: int = 0):
        self.power_bonus = power_bonus
        self.toughness_bonus = toughness_bonus
    
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        # Override with controller/owner checking
        return True
    
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> None:
        permanent.power_bonus = (
            permanent.power_bonus or 0
        ) + self.power_bonus
        permanent.toughness_bonus = (
            permanent.toughness_bonus or 0
        ) + self.toughness_bonus


class HexproofGrant(StaticAbility):
    """Static ability granting hexproof.
    
    Example: "Creatures you control have hexproof"
    """
    
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        return True
    
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> None:
        # Hexproof is a keyword - handled elsewhere
        pass


class IndestructibleGrant(StaticAbility):
    """Static ability granting indestructible.
    
    Example: "Creatures you control are indestructible"
    """
    
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        return True
    
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> None:
        # Indestructible is a keyword - handled elsewhere
        pass


class ContinuousEffect(StaticAbility):
    """Generic continuous effect from text.
    
    Parses "as though" effects, "is treated as", etc.
    """
    
    def __init__(self, effect_text: str):
        self.effect_text = effect_text
    
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        return True
    
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> None:
        logger.debug("Applying continuous effect: %s", self.effect_text)


# Static ability registry
STATIC_ABILITY_REGISTRY: dict[str, type[StaticAbility]] = {
    "cant_attack": CantAttackBlock,
    "cant_block": lambda: CantAttackBlock("block"),
    "pump": ContinuousPump,
    "hexproof": HexproofGrant,
    "indestructible": IndestructibleGrant,
}


def create_static_ability(ability_type: str, **kwargs) -> StaticAbility | None:
    """Create static ability by type.
    
    Args:
        ability_type: Type of static ability
        **kwargs: Additional arguments
        
    Returns:
        StaticAbility instance or None
    """
    ability_class = STATIC_ABILITY_REGISTRY.get(ability_type)
    if ability_class:
        return ability_class(**kwargs)
    return None
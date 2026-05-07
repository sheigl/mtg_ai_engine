"""
Keyword ability base class hierarchy.

KW-01: Base class for all keyword abilities, providing the apply() interface
that integrates with the engine's trigger and effect resolution system.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card, Permanent

logger = logging.getLogger(__name__)


class KeywordAbility(ABC):
    """Base class for all keyword abilities.

    Keyword abilities are special abilities with names (e.g., flying, deathtouch,
    toxic) that have standardized rules text. This class provides the interface
    for implementing keyword behavior in the engine.
    """

    name: str = ""

    @abstractmethod
    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        """Check if this keyword ability applies to the given permanent.

        Args:
            game_state: Current game state.
            permanent: Permanent to check.

        Returns:
            True if the keyword is active on this permanent.
        """
        ...

    @abstractmethod
    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        """Apply this keyword ability's effect.

        Args:
            game_state: Current game state.
            permanent: Source permanent with the keyword.
            target: Optional target permanent affected by the keyword.

        Returns:
            Modified game state after applying the keyword effect.
        """
        ...

    def get_trigger_description(self) -> str:
        """Get human-readable description of the keyword's trigger effect."""
        return f"{self.name} keyword active"

    def matches_keyword(self, keyword_name: str) -> bool:
        """Check if this keyword matches the given name."""
        return self.name.lower() == keyword_name.lower()


class PassiveKeyword(KeywordAbility):
    """Base class for passive keywords that modify rules (flying, trample, etc.).

    Passive keywords don't trigger abilities but modify how game rules apply.
    """

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        keywords = permanent.card.keywords or []
        return self.name.lower() in [k.lower() for k in keywords]

    def apply(
        self,
        game_state: "GameState",
        permanent: "Permanent",
        target: "Permanent | None" = None,
    ) -> "GameState":
        logger.debug("Passive keyword %s active on %s", self.name, permanent.card.name)
        return game_state


class TriggeredKeyword(KeywordAbility):
    """Base class for keywords that create triggered abilities (ETB, LTB, etc.).

    Triggered keywords create abilities that fire when specific events occur.
    """

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        keywords = permanent.card.keywords or []
        return self.name.lower() in [k.lower() for k in keywords]


class CostKeyword(KeywordAbility):
    """Base class for keywords that add alternative costs (kicker, escalate, etc.).

    Cost keywords modify how spells can be cast.
    """

    def applies(
        self,
        game_state: "GameState",
        permanent: "Permanent",
    ) -> bool:
        keywords = permanent.card.keywords or []
        return self.name.lower() in [k.lower() for k in keywords]


# Keyword registry
KEYWORD_REGISTRY: dict[str, type[KeywordAbility]] = {}


def register_keyword(name: str, keyword_class: type[KeywordAbility]) -> None:
    """Register a keyword class by name."""
    KEYWORD_REGISTRY[name.lower()] = keyword_class


def get_keyword(name: str) -> type[KeywordAbility] | None:
    """Get keyword class by name."""
    return KEYWORD_REGISTRY.get(name.lower())


def create_keyword(name: str, **kwargs) -> KeywordAbility | None:
    """Create keyword instance by name."""
    keyword_class = get_keyword(name)
    if keyword_class:
        return keyword_class(**kwargs)
    return None

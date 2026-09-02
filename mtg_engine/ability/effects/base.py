"""
Ability effects class hierarchy.

Phase REFACTOR: Replaces regex-based effect handling in stack.py with
dedicated effect classes like Forge's SpellAbilityEffect system.
"""
from __future__ import annotations
import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_engine.models.game import GameState, Card

logger = logging.getLogger(__name__)


# Helper functions to avoid import cycle issues
def _get_permanent(game_state: "GameState", perm_id: str):
    """Get permanent by ID."""
    for perm in game_state.battlefield:
        if perm.id == perm_id:
            return perm
    return None


def _get_player(game_state: "GameState", name: str):
    """Get player by name."""
    for player in game_state.players:
        if player.name == name:
            return player
    return None


class Effect(ABC):
    """Base class for all card effects."""
    
    @abstractmethod
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        """Execute the effect.
        
        Args:
            game_state: Current game state
            source: Source card triggering the effect
            targets: List of target IDs
            controller_name: Player controlling the effect
        """
        ...
    
    def can_target(
        self,
        game_state: "GameState",
        source: "Card",
        target: str,
    ) -> bool:
        """Check if target is valid."""
        return _get_permanent(game_state, target) is not None
    
    def get_valid_targets(
        self,
        game_state: "GameState",
        source: "Card",
    ) -> list[str]:
        """Get list of valid target IDs."""
        valid = []
        for perm in game_state.battlefield:
            if self.can_target(game_state, source, perm.id):
                valid.append(perm.id)
        return valid


class DamageEffect(Effect):
    """Effect that deals damage."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        if not targets:
            return game_state
        
        for target_id in targets:
            target_perm = _get_permanent(game_state, target_id)
            target_player = _get_player(game_state, target_id)
            
            amount = self._get_damage_amount(source)
            
            if target_perm:
                if self._has_wither(source):
                    counters = dict(target_perm.counters or {})
                    counters["-1/-1"] = counters.get("-1/-1", 0) + amount
                    target_perm.counters = counters
                else:
                    target_perm.damage_marked = target_perm.damage_marked + amount
                logger.info("%s deals %d damage to %s", source.name, amount, target_perm.card.name)
            elif target_player:
                target_player.life = target_player.life - amount
                logger.info("%s deals %d damage to %s", source.name, amount, target_player.name)
        
        return game_state
    
    def _get_damage_amount(self, source: "Card") -> int:
        oracle = source.oracle_text or ""
        match = re.search(r"deals? (\d+) damage", oracle)
        if match:
            return int(match.group(1))
        return 1
    
    def _has_wither(self, source: "Card") -> bool:
        return "withertouch" in (source.keywords or []) or "wither" in (source.keywords or [])


class DestroyEffect(Effect):
    """Effect that destroys target."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        if not targets:
            return game_state
        
        controller = _get_player(game_state, controller_name) if controller_name else None
        
        for target_id in targets:
            target_perm = _get_permanent(game_state, target_id)
            if not target_perm:
                continue
            
            keywords = target_perm.card.keywords or []
            if "indestructible" in keywords:
                logger.info("%s is indestructible - not destroyed", target_perm.card.name)
                continue
            
            if controller:
                controller.graveyard.append(target_perm.card)
            
            game_state.battlefield = [p for p in game_state.battlefield if p.id != target_perm.id]
            logger.info("%s destroyed by %s", target_perm.card.name, source.name)
        
        return game_state
    
    def can_target(
        self,
        game_state: "GameState",
        source: "Card",
        target: str,
    ) -> bool:
        target_perm = _get_permanent(game_state, target)
        if not target_perm:
            return False
        type_lower = target_perm.card.type_line.lower()
        return any(t in type_lower for t in ["creature", "enchantment", "artifact", "planeswalker"])


class DrawEffect(Effect):
    """Effect that draws cards."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        from mtg_engine.engine.zones import draw_card
        
        draw_count = self._get_draw_count(source)
        player = _get_player(game_state, controller_name) if controller_name else None
        if not player:
            return game_state
        
        for _ in range(draw_count):
            game_state, _ = draw_card(game_state, player.name)
        
        logger.info("%s draws %d cards", player.name, draw_count)
        return game_state
    
    def _get_draw_count(self, source: "Card") -> int:
        oracle = source.oracle_text or ""
        match = re.search(r"draw (\w+) cards?", oracle)
        if match:
            word = match.group(1)
            num_map = {"one": 1, "two": 2, "three": 3, "four": 4}
            return num_map.get(word, 1)
        match = re.search(r"draw (\d+) cards?", oracle)
        if match:
            return int(match.group(1))
        return 1


class SearchEffect(Effect):
    """Effect that searches library."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        player = _get_player(game_state, controller_name) if controller_name else None
        if player:
            logger.info("%s searches their library", player.name)
        return game_state
    
    def get_valid_targets(self, game_state: "GameState", source: "Card") -> list[str]:
        return []


class ExileEffect(Effect):
    """Effect that exiles target."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        if not targets:
            return game_state
        
        for target_id in targets:
            target_perm = _get_permanent(game_state, target_id)
            if not target_perm:
                continue
            
            # Move to exile zone (use controller's exile if available)
            controller = _get_player(game_state, controller_name) if controller_name else None
            if controller:
                controller.exile.append(target_perm.card)
            
            game_state.battlefield = [p for p in game_state.battlefield if p.id != target_perm.id]
            logger.info("%s exiled by %s", target_perm.card.name, source.name)
        
        return game_state
    
    def can_target(
        self,
        game_state: "GameState",
        source: "Card",
        target: str,
    ) -> bool:
        return _get_permanent(game_state, target) is not None


class CreateTokenEffect(Effect):
    """Effect that creates token."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        from mtg_engine.engine.zones import put_permanent_onto_battlefield
        
        player = _get_player(game_state, controller_name) if controller_name else None
        if not player:
            return game_state
        
        token_count = self._get_token_count(source)
        card = source

        # Wire: Token Trigger (CR 704.5c) — "whenever you create a token" /
        # "whenever a token enters the battlefield". check_token_triggers is the
        # single owner of token triggers (the zone listener skips them). Fire once
        # PER token created so each token is a separate event (CR 110.6).
        from mtg_engine.engine.triggers import check_token_triggers as _check_token

        for _ in range(token_count):
            game_state, _ = put_permanent_onto_battlefield(
                game_state, card, player.name, is_token=True
            )
            # One "token created" event per token (CR 110.6).
            game_state = _check_token(game_state, player.name)

        logger.info("%s creates %d token(s)", player.name, token_count)
        return game_state
    
    def _get_token_count(self, source: "Card") -> int:
        oracle = source.oracle_text or ""
        match = re.search(r"create (\w+) (?:token|1/1)", oracle)
        if match:
            word = match.group(1)
            num_map = {"one": 1, "two": 2, "three": 3}
            return num_map.get(word, 1)
        match = re.search(r"create (\d+)", oracle)
        if match:
            return int(match.group(1))
        return 1


class GainLifeEffect(Effect):
    """Effect that gains life."""
    
    def resolve(
        self,
        game_state: "GameState",
        source: "Card",
        targets: list[str] | None = None,
        controller_name: str | None = None,
    ) -> "GameState":
        player = _get_player(game_state, controller_name) if controller_name else None
        if not player:
            return game_state
        
        life_change = self._get_life_change(source)
        player.life = player.life + life_change
        logger.info("%s gains %d life", player.name, life_change)
        return game_state
    
    def _get_life_change(self, source: "Card") -> int:
        oracle = source.oracle_text or ""
        match = re.search(r"gain (\w+) life", oracle)
        if match:
            word = match.group(1)
            num_map = {"one": 1, "two": 2, "three": 3}
            return num_map.get(word, 1)
        match = re.search(r"gain (\d+) life", oracle)
        if match:
            return int(match.group(1))
        return 1


# Effect registry
EFFECT_REGISTRY: dict[str, type[Effect]] = {
    "damage": DamageEffect,
    "destroy": DestroyEffect,
    "draw": DrawEffect,
    "search": SearchEffect,
    "exile": ExileEffect,
    "create_token": CreateTokenEffect,
    "gain_life": GainLifeEffect,
}


def get_effect(effect_name: str) -> type[Effect] | None:
    """Get effect class by name."""
    return EFFECT_REGISTRY.get(effect_name)


def create_effect(effect_name: str) -> Effect | None:
    """Create effect instance."""
    effect_class = get_effect(effect_name)
    if effect_class:
        return effect_class()
    return None
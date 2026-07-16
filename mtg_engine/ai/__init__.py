"""
AI decision framework (AI-01).

Re-exports the heuristic and LLM AI players from the ai_client package,
providing a stable public API at ``mtg_engine.ai``.

Usage::

    from mtg_engine.ai import HeuristicAI, AIFramework

    ai = AIFramework(player_name="Alice", personality="default")
    index, reasoning = ai.decide(prompt, legal_actions, game_state)
"""
from typing import Optional

from ai_client.heuristic_player import HeuristicPlayer
from ai_client.ai_player import AIPlayer
from ai_client.models import AIMemory, AiPersonalityProfile, PlayerConfig


class HeuristicAI:
    """
    Score-based AI player that evaluates every legal action and picks the best.

    Wraps ``HeuristicPlayer`` from ``ai_client``.
    """

    def __init__(
        self,
        player_name: str,
        personality: Optional[AiPersonalityProfile] = None,
    ) -> None:
        self._name = player_name
        self._profile = personality or AiPersonalityProfile.DEFAULT
        self._memory = AIMemory()
        config = PlayerConfig(
            name=player_name,
            player_type="heuristic",
            personality=self._profile,
        )
        self._player = HeuristicPlayer(config)

    @property
    def memory(self) -> AIMemory:
        return self._memory

    @property
    def name(self) -> str:
        return self._name

    def decide(
        self,
        prompt: str,
        legal_actions: list[dict],
        game_state: dict,
    ) -> tuple[int, str]:
        """
        Evaluate all legal actions and return (index, reasoning) of the best one.
        """
        return self._player.decide(prompt, legal_actions, game_state, self._memory)

    def evaluate_mulligan(self, hand: list[dict], hand_size: int) -> bool:
        """Return True if the hand is worth keeping."""
        return self._player.evaluate_mulligan(hand, hand_size)

    def select_attackers(
        self, action: dict, game_state: dict, my_name: str
    ) -> list[str]:
        """Select which creatures to attack with."""
        return self._player.select_attackers(action, game_state, my_name)


class LLMAI:
    """
    LLM-based AI player that queries an OpenAI-compatible endpoint.

    Wraps ``AIPlayer`` from ``ai_client``.
    """

    def __init__(self, config: PlayerConfig) -> None:
        self._player = AIPlayer(config)
        self._name = config.name

    @property
    def name(self) -> str:
        return self._name

    def decide(
        self,
        prompt: str,
        legal_actions: Optional[list[dict]] = None,
        game_state: Optional[dict] = None,
    ) -> tuple[int, str]:
        return self._player.decide(prompt, legal_actions, game_state)


class AIFramework:
    """
    Convenience factory that creates the right AI type based on a type string.

    Usage::

        ai = AIFramework.for_type("heuristic", player_name="Alice")
        ai = AIFramework.for_type("llm", player_name="Bob", model="gpt-4")
    """

    @staticmethod
    def for_type(
        ai_type: str,
        player_name: str = "",
        model: str = "",
        base_url: str = "",
        personality: Optional[AiPersonalityProfile] = None,
    ) -> HeuristicAI | LLMAI:
        if ai_type == "heuristic":
            return HeuristicAI(player_name, personality)
        if ai_type == "llm":
            config = PlayerConfig(
                name=player_name,
                base_url=base_url,
                model=model,
                player_type="llm",
            )
            return LLMAI(config)
        msg = f"Unknown AI type: {ai_type!r}. Use 'heuristic' or 'llm'."
        raise ValueError(msg)

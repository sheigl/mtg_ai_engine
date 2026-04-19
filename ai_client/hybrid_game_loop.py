"""Hybrid game loop: drives AI turns automatically, waits for human input on human turns."""
import time
from .game_loop import GameLoop


class HybridGameLoop(GameLoop):
    """Extends GameLoop to support one human-controlled seat.

    When the human player holds priority, the loop sleeps and polls rather than
    calling the AI — the human submits their action directly via the frontend API.
    """

    def __init__(self, human_player_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._human_player_name = human_player_name

    def _skip_player_turn(self, priority_player: str, legal_data: dict) -> bool:
        """Return True (and sleep) when the human player holds priority."""
        if priority_player == self._human_player_name:
            time.sleep(0.5)
            return True
        return False

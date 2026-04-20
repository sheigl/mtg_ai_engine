"""Hybrid game loop: drives AI turns automatically, waits for human input on human turns."""
import time
from .game_loop import GameLoop, _has_floating_mana


class HybridGameLoop(GameLoop):
    """Extends GameLoop to support one human-controlled seat.

    When the human player holds priority, the loop sleeps and polls rather than
    calling the AI — the human submits their action directly via the frontend API.
    After the human acts, the observer AI is triggered just like for AI actions.
    """

    def __init__(self, human_player_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._human_player_name = human_player_name
        self._human_prev_state_hash: str | None = None
        self._human_prev_gs: dict = {}
        self._human_prev_legal_data: dict = {}

    def _skip_player_turn(self, priority_player: str, legal_data: dict) -> bool:
        if priority_player != self._human_player_name:
            # AI has priority — reset human tracking state
            self._human_prev_state_hash = None
            return False

        game_id = self._current_game_id
        if game_id is None:
            time.sleep(0.5)
            return True

        # First time seeing human priority for this window — record the baseline
        if self._human_prev_state_hash is None:
            try:
                gs = self._engine.get_game_state(game_id)
                self._human_prev_state_hash = gs.get("state_hash", "")
                self._human_prev_gs = gs
                self._human_prev_legal_data = legal_data
            except Exception:
                pass
            time.sleep(0.5)
            return True

        # Poll and check whether the human has acted (state hash changed)
        try:
            gs = self._engine.get_game_state(game_id)
        except Exception:
            time.sleep(0.5)
            return True

        new_hash = gs.get("state_hash", "")
        if new_hash != self._human_prev_state_hash:
            # Human submitted an action — fire the observer if configured
            prev_gs = self._human_prev_gs
            prev_legal_data = self._human_prev_legal_data
            action_desc = self._engine.get_last_transcript_desc(game_id) or "Human player action"

            # Only observe non-pass actions (mirrors AI observer filter)
            prev_legal_actions = prev_legal_data.get("legal_actions", [])
            _is_pass = action_desc.lower().startswith("pass") or action_desc == "Human player action"
            _should_observe = not _is_pass or _has_floating_mana(prev_gs, priority_player)
            if _should_observe:
                self._observe_action(
                    action_desc=action_desc,
                    legal_actions=prev_legal_actions,
                    gs=prev_gs,
                    priority_player=priority_player,
                    turn_number=prev_gs.get("turn", 1),
                    phase=prev_legal_data.get("phase", "?"),
                    step=prev_legal_data.get("step", "?"),
                    snapshot_id=prev_legal_data.get("snapshot_id"),
                    player_entry_id=None,
                )

            # Update baseline for next action in the same priority window
            self._human_prev_state_hash = new_hash
            self._human_prev_gs = gs
            self._human_prev_legal_data = legal_data

        time.sleep(0.5)
        return True

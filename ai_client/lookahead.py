"""
LookaheadSimulator — depth-1 future-state evaluation for the heuristic AI.

Architecture:
  - Makes a deep copy of the current game_state dict (no engine API calls)
  - Applies the chosen action to the copy
  - Scores all resulting actions the AI would see on the next decision
  - Returns a bonus (0–30) to add to the current action's heuristic score

Performance budget: ≤15 legal actions × ≤15 next actions × O(20 permanents) = ~4 500 ops.
"""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .heuristic_player import HeuristicPlayer
    from .models import AIMemory


class LookaheadSimulator:
    """
    Depth-1 lookahead simulator.

    Usage:
        sim = LookaheadSimulator(heuristic_player)
        bonus = sim.evaluate_bonus(current_action, game_state, memory)
    """

    def __init__(self, heuristic_player: "HeuristicPlayer", max_depth: int = 1) -> None:
        self._player = heuristic_player
        self._max_depth = max_depth  # currently only depth=1 is used

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def evaluate_bonus(
        self,
        current_action: dict,
        game_state: dict,
        memory: "AIMemory | None" = None,
    ) -> float:
        """
        Return a bonus float (0.0–30.0) representing the best future outcome
        the AI expects after taking current_action.

        Returns 0.0 on any error so the main scorer is never disrupted.
        """
        try:
            return self._evaluate(current_action, game_state, memory)
        except Exception:  # pragma: no cover — defensive
            return 0.0

    # ------------------------------------------------------------------
    # Internal implementation
    # ------------------------------------------------------------------

    def _evaluate(
        self,
        current_action: dict,
        game_state: dict,
        memory: "AIMemory | None",
    ) -> float:
        next_state = self._apply_action_to_state(current_action, game_state)
        my_name = next_state.get("priority_player", "")

        # Build a set of plausible next actions the AI might face
        next_actions = self._synthesize_next_actions(next_state, my_name)
        if not next_actions:
            return 0.0

        best_future = max(
            self._player._score_action(a, next_state, my_name)
            for a in next_actions
        )

        # Scale to the 0–30 bonus range
        return min(30.0, max(0.0, best_future * 0.15))

    def _apply_action_to_state(self, action: dict, state: dict) -> dict:
        """
        Return a deep-copied, lightly-mutated game state after applying action.
        Handles: play_land, cast (creature / non-creature), pass.
        Does NOT implement full rules resolution — approximation only.
        """
        next_state = copy.deepcopy(state)
        action_type = action.get("action_type", "pass")
        my_name = next_state.get("priority_player", "")

        if action_type == "play_land":
            # Remove land from hand, increment lands_played, add to battlefield
            card_id = action.get("card_id", "")
            for player in next_state.get("players", []):
                if player.get("name") == my_name:
                    player["hand"] = [
                        c for c in player.get("hand", [])
                        if c.get("id") != card_id
                    ]
                    player["lands_played"] = player.get("lands_played", 0) + 1
                    break
            # Add a placeholder land permanent (simplified)
            next_state.setdefault("battlefield", []).append({
                "id": f"__la_{card_id}",
                "controller": my_name,
                "card": {"type_line": "Land", "mana_cost": "", "oracle_text": ""},
                "tapped": False,
                "summoning_sick": False,
            })

        elif action_type == "cast":
            card_id = action.get("card_id", "")
            for player in next_state.get("players", []):
                if player.get("name") == my_name:
                    card = next(
                        (c for c in player.get("hand", []) if c.get("id") == card_id),
                        None,
                    )
                    player["hand"] = [
                        c for c in player.get("hand", [])
                        if c.get("id") != card_id
                    ]
                    # If it's a creature, add a simplified permanent to battlefield
                    if card and "creature" in (card.get("type_line") or "").lower():
                        next_state.setdefault("battlefield", []).append({
                            "id": f"__la_{card_id}",
                            "controller": my_name,
                            "card": card,
                            "tapped": False,
                            "summoning_sick": True,
                            "power_bonus": 0,
                            "toughness_bonus": 0,
                            "counters": {},
                        })
                    break

        elif action_type == "pass":
            # Advance step (simplified — just note it)
            pass

        return next_state

    def _synthesize_next_actions(self, state: dict, my_name: str) -> list[dict]:
        """
        Build a representative set of next-turn actions from the projected state.
        Returns cast actions for cards still in hand + a pass option.
        """
        actions: list[dict] = [{"action_type": "pass"}]
        for player in state.get("players", []):
            if player.get("name") == my_name:
                for card in player.get("hand", []):
                    actions.append({
                        "action_type": "cast",
                        "card_id": card.get("id", ""),
                        "card_name": card.get("name", ""),
                        "mana_options": [{"mana_cost": card.get("mana_cost", "")}],
                        "valid_targets": [],
                        "description": f"cast {card.get('name', '?')}",
                    })
        return actions

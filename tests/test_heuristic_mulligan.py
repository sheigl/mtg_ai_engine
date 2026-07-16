"""
Regression test for heuristic player mulligan bug (022).

Bug: _score_mulligan returned the same score for both "Keep hand" and "Mulligan"
actions, causing "Pass priority" (score 0) to win over "Keep hand" (score -50)
when the hand was keepable. The mulligan phase never resolved.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_client.heuristic_player import HeuristicPlayer
from ai_client.models import PlayerConfig

_PASS = {"action_type": "pass", "description": "Pass priority"}
_MULLIGAN = {"action_type": "declare_mulligan", "description": "Mulligan (draw 6)"}
_KEEP = {"action_type": "declare_mulligan", "description": "Keep hand"}


def _make_player() -> HeuristicPlayer:
    cfg = PlayerConfig(name="Test", base_url="", model="", player_type="heuristic")
    return HeuristicPlayer(cfg)


def _keepable_hand() -> list[dict]:
    """Mixed hand with 3 lands + 4 spells — clearly worth keeping."""
    land = {"type_line": "Basic Land — Forest", "name": "Forest", "mana_cost": "", "cmc": 0}
    spell = {"type_line": "Creature — Elf", "name": "Llanowar Elves", "mana_cost": "{G}", "cmc": 1}
    return [land] * 3 + [spell] * 4


def _zero_land_hand() -> list[dict]:
    """All spells — should always mulligan."""
    spell = {"type_line": "Creature — Elf", "name": "Elvish Warrior", "mana_cost": "{G}{G}", "cmc": 2}
    return [spell] * 7


def _make_gs(hand: list[dict], my_name: str = "Test") -> dict:
    return {
        "priority_player": my_name,
        "phase": "beginning",
        "step": "untap",
        "players": [{"name": my_name, "hand": hand, "life": 20}],
        "battlefield": [],
        "stack": [],
    }


def test_keepable_hand_selects_keep():
    """When hand is worth keeping, decide() must pick 'Keep hand', not 'pass'."""
    player = _make_player()
    hand = _keepable_hand()
    gs = _make_gs(hand)
    legal = [_PASS, _MULLIGAN, _KEEP]
    idx, _ = player.decide("", legal_actions=legal, game_state=gs)
    assert legal[idx]["description"] == "Keep hand", (
        f"Expected 'Keep hand' but got '{legal[idx]['description']}' (index {idx}). "
        "Heuristic player must not pass during mulligan when hand is keepable."
    )


def test_no_land_hand_selects_mulligan():
    """When hand has zero lands, decide() must pick the 'Mulligan' action."""
    player = _make_player()
    hand = _zero_land_hand()
    gs = _make_gs(hand)
    legal = [_PASS, _MULLIGAN, _KEEP]
    idx, _ = player.decide("", legal_actions=legal, game_state=gs)
    assert legal[idx]["description"] == "Mulligan (draw 6)", (
        f"Expected 'Mulligan' but got '{legal[idx]['description']}' (index {idx}). "
        "Heuristic player must mulligan a zero-land hand."
    )


def test_pass_never_chosen_during_mulligan_with_keepable_hand():
    """'Pass priority' must never win over a committed keep/mulligan decision."""
    player = _make_player()
    hand = _keepable_hand()
    gs = _make_gs(hand)
    legal = [_PASS, _MULLIGAN, _KEEP]
    idx, _ = player.decide("", legal_actions=legal, game_state=gs)
    assert legal[idx]["action_type"] == "declare_mulligan", (
        "Heuristic player must not pass during mulligan — must commit to keep or mulligan."
    )

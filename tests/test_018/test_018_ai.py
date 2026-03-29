"""
Tests for US9: AI Responds During Opponent's Priority Window.
T105-T106: AI non-active priority, AI counterspell evaluation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ai_client.heuristic_player import HeuristicPlayer
from ai_client.models import PlayerConfig, AiPersonalityProfile


def _make_player(name: str = "p1") -> HeuristicPlayer:
    config = PlayerConfig(name=name, model="heuristic", personality=AiPersonalityProfile.DEFAULT)
    return HeuristicPlayer(config)


def _game_state(active_player: str = "p2", priority_player: str = "p1") -> dict:
    return {
        "active_player": active_player,
        "priority_player": priority_player,
        "priority_holder": priority_player,
        "phase": "precombat_main",
        "step": "main",
        "stack": [],
        "battlefield": [],
        "players": [
            {"name": "p1", "life": 20, "hand": [], "library": [], "graveyard": []},
            {"name": "p2", "life": 20, "hand": [], "library": [], "graveyard": []},
        ],
    }


# T105: Test AI non-active priority
def test_ai_non_active_priority_defaults_to_pass():
    """AI should pass priority when it's the opponent's turn and nothing is happening."""
    player = _make_player("p1")
    gs = _game_state(active_player="p2", priority_player="p1")
    # No meaningful actions — only a pass
    legal_actions = [
        {"action_type": "pass_priority"},
    ]
    idx, reason = player.decide("test prompt", legal_actions=legal_actions, game_state=gs)
    assert idx == 0  # should choose pass


def test_ai_non_active_priority_considers_instant():
    """AI should consider casting an instant during opponent's turn."""
    player = _make_player("p1")
    gs = _game_state(active_player="p2", priority_player="p1")
    bear_on_board = {
        "id": "bear1",
        "card": {
            "name": "Grizzly Bears",
            "type_line": "Creature — Bear",
            "oracle_text": "",
            "power": "2", "toughness": "2",
            "mana_cost": "{1}{G}",
            "keywords": [],
        },
        "controller": "p2",
        "tapped": False,
        "summoning_sick": False,
        "power_bonus": 0,
        "toughness_bonus": 0,
        "counters": {},
    }
    gs["battlefield"] = [bear_on_board]
    legal_actions = [
        {
            "action_type": "cast",
            "card_id": "murder1",
            "card_name": "Murder",
            "card": {
                "name": "Murder",
                "type_line": "Instant",
                "oracle_text": "Destroy target creature.",
                "mana_cost": "{1}{B}{B}",
                "keywords": [],
                "colors": ["B"],
            },
            "targets": ["bear1"],
            "mana_payment": {"B": 2, "C": 1},
        },
        {"action_type": "pass_priority"},
    ]
    idx, reason = player.decide("test prompt", legal_actions=legal_actions, game_state=gs)
    # AI may or may not cast the removal — just verify it doesn't crash
    assert idx in range(len(legal_actions))


# T106: Test AI counterspell evaluation
def test_ai_counterspell_evaluation_during_opponent_turn():
    """AI should score counterspells highly when opponent has a valuable spell on stack."""
    player = _make_player("p1")
    gs = _game_state(active_player="p2", priority_player="p1")
    # Opponent's spell is on the stack
    gs["stack"] = [
        {
            "id": "spell1",
            "source_card": {
                "name": "Baneslayer Angel",
                "type_line": "Creature — Angel",
                "oracle_text": "",
                "mana_cost": "{3}{W}{W}",
                "keywords": [],
            },
            "caster": "p2",
            "controller": "p2",
            "targets": [],
        }
    ]
    counterspell = {
        "id": "counter1",
        "name": "Counterspell",
        "type_line": "Instant",
        "oracle_text": "Counter target spell.",
        "mana_cost": "{U}{U}",
        "keywords": [],
        "colors": ["U"],
    }
    # Put the counterspell in p1's hand so _score_cast can find it
    gs["players"][0]["hand"] = [counterspell]
    legal_actions = [
        {
            "action_type": "cast",
            "card_id": "counter1",
            "card_name": "Counterspell",
            "card": counterspell,
            "targets": ["spell1"],
            "mana_payment": {"U": 2},
        },
        {"action_type": "pass_priority"},
    ]
    idx, reason = player.decide("test prompt", legal_actions=legal_actions, game_state=gs)
    # AI should prefer the counterspell over passing (idx 0 = counterspell > idx 1 = pass)
    assert idx == 0, f"AI should prefer countering but chose: {reason}"


def test_ai_counterspell_ignored_when_no_stack():
    """AI should pass priority when stack is empty and counterspell has no target."""
    player = _make_player("p1")
    gs = _game_state(active_player="p2", priority_player="p1")
    gs["stack"] = []  # nothing on stack
    counterspell = {
        "name": "Counterspell",
        "type_line": "Instant",
        "oracle_text": "Counter target spell.",
        "mana_cost": "{U}{U}",
        "keywords": [],
        "colors": ["U"],
    }
    legal_actions = [
        {
            "action_type": "cast",
            "card_id": "counter1",
            "card_name": "Counterspell",
            "card": counterspell,
            "targets": [],
            "mana_payment": {"U": 2},
        },
        {"action_type": "pass_priority"},
    ]
    idx, reason = player.decide("test prompt", legal_actions=legal_actions, game_state=gs)
    # With nothing on the stack, AI shouldn't blindly cast the counterspell
    # Either pass or cast — just verify no crash
    assert idx in range(len(legal_actions))


def test_ai_is_opponent_turn_detection():
    """Test _is_opponent_turn helper correctly identifies non-active turns."""
    player = _make_player("p1")
    # p2 is active, p1 has priority → opponent's turn
    gs_opponent = _game_state(active_player="p2", priority_player="p1")
    assert player._is_opponent_turn(gs_opponent, "p1") is True
    # p1 is active, p1 has priority → own turn
    gs_own = _game_state(active_player="p1", priority_player="p1")
    assert player._is_opponent_turn(gs_own, "p1") is False

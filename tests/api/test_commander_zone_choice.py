"""API integration tests for CMD-01 commander zone replacement choice handlers.

Verifies that the `commander_zone_replace` and `commander_zone_stay` API endpoints
correctly move cards to their intended zones after a human player makes a choice.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.models.game import GameState, PlayerState, Card, ManaPool, Permanent

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    """Clear game manager between tests."""
    mgr = get_manager()
    mgr._games.clear()
    yield
    mgr._games.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_commander_player(name: str, **kwargs) -> PlayerState:
    return PlayerState(
        name=name, life=20, mana_pool=ManaPool(),
        commander_names=kwargs.get("commander_names", []),
        commander_cast_counts=kwargs.get("commander_cast_counts", {}),
        commander_damage=kwargs.get("commander_damage", {}),
    )


def _inject_game_state(game_id: str, gs: GameState):
    """Directly inject a game state into the manager for testing."""
    mgr = get_manager()
    mgr._games[game_id] = gs


# ── Tests: commander_zone_stay API handler ────────────────────────────────────

class TestCommanderZoneStayAPI:
    """Verify the API choice endpoint correctly handles commander_zone_stay.

    The fix (game.py line 1813-1834) replaced buggy move_card_to_zone call with
    direct zone append: getattr(player_obj, intended).append(card).
    """

    def test_commander_zone_stay_battlefield_to_graveyard(self):
        """Card must appear in graveyard when player chooses 'stay' for B→G."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-stay-b2g", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "graveyard",
                "from_zone": "battlefield",
            },
        )
        _inject_game_state("test-stay-b2g", gs)

        resp = client.post("/game/test-stay-b2g/choice", json={
            "choice_id": "commander_zone_stay",
        })
        assert resp.status_code == 200, resp.text

        # Verify card is in graveyard
        mgr = get_manager()
        result_gs = mgr._games["test-stay-b2g"]
        p1_result = next(p for p in result_gs.players if p.name == "p1")
        assert len(p1_result.graveyard) == 1, (
            f"Card lost! graveyard={len(p1_result.graveyard)}, "
            f"command_zone={len(p1_result.command_zone)}"
        )
        assert result_gs.pending_commander_zone_choice is None

    def test_commander_zone_stay_hand_to_exile(self):
        """Card must appear in exile when player chooses 'stay' for H→E."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-stay-h2e", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "exile",
                "from_zone": "hand",
            },
        )
        _inject_game_state("test-stay-h2e", gs)

        resp = client.post("/game/test-stay-h2e/choice", json={
            "choice_id": "commander_zone_stay",
        })
        assert resp.status_code == 200, resp.text

        mgr = get_manager()
        result_gs = mgr._games["test-stay-h2e"]
        p1_result = next(p for p in result_gs.players if p.name == "p1")
        assert len(p1_result.exile) == 1, (
            f"Card lost! exile={len(p1_result.exile)}, "
            f"command_zone={len(p1_result.command_zone)}"
        )
        assert result_gs.pending_commander_zone_choice is None

    def test_commander_zone_stay_clears_pending_choice(self):
        """After choosing stay, pending_commander_zone_choice must be cleared."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-stay-clear", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "graveyard",
                "from_zone": "battlefield",
            },
        )
        _inject_game_state("test-stay-clear", gs)

        resp = client.post("/game/test-stay-clear/choice", json={
            "choice_id": "commander_zone_stay",
        })
        assert resp.status_code == 200, resp.text

        mgr = get_manager()
        result_gs = mgr._games["test-stay-clear"]
        assert result_gs.pending_commander_zone_choice is None


class TestCommanderZoneReplaceAPI:
    """Verify the API choice endpoint correctly handles commander_zone_replace."""

    def test_commander_zone_replace_moves_to_command_zone(self):
        """Card must appear in command zone when player chooses 'replace'."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-replace", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "graveyard",
                "from_zone": "battlefield",
            },
        )
        _inject_game_state("test-replace", gs)

        resp = client.post("/game/test-replace/choice", json={
            "choice_id": "commander_zone_replace",
        })
        assert resp.status_code == 200, resp.text

        mgr = get_manager()
        result_gs = mgr._games["test-replace"]
        p1_result = next(p for p in result_gs.players if p.name == "p1")
        assert len(p1_result.command_zone) == 1
        assert len(p1_result.graveyard) == 0
        assert result_gs.pending_commander_zone_choice is None

    def test_commander_zone_replace_clears_pending_choice(self):
        """After choosing replace, pending_commander_zone_choice must be cleared."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-replace-clear", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "graveyard",
                "from_zone": "battlefield",
            },
        )
        _inject_game_state("test-replace-clear", gs)

        resp = client.post("/game/test-replace-clear/choice", json={
            "choice_id": "commander_zone_replace",
        })
        assert resp.status_code == 200, resp.text

        mgr = get_manager()
        result_gs = mgr._games["test-replace-clear"]
        assert result_gs.pending_commander_zone_choice is None


class TestCommanderZoneStayNoCardLoss:
    """Regression tests specifically for the card-loss bug."""

    def test_card_not_in_battlefield_after_stay(self):
        """Card must NOT remain on battlefield after stay choice."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-no-battlefield", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "graveyard",
                "from_zone": "battlefield",
            },
        )
        _inject_game_state("test-no-battlefield", gs)

        client.post("/game/test-no-battlefield/choice", json={
            "choice_id": "commander_zone_stay",
        })

        mgr = get_manager()
        result_gs = mgr._games["test-no-battlefield"]
        assert len(result_gs.battlefield) == 0

    def test_card_not_in_hand_after_stay(self):
        """Card must NOT remain in hand after stay choice for H→E path."""
        p1 = _make_commander_player("p1", commander_names=["Niv-Mizzet"])
        p2 = PlayerState(name="p2", life=20, mana_pool=ManaPool())
        card = Card(name="Niv-Mizzet")

        gs = GameState(
            game_id="test-no-hand", seed=1, active_player="p1", priority_holder="p1",
            players=[p1, p2], format="commander", human_player_name="p1",
            pending_commander_zone_choice={
                "player": "p1",
                "card": card,
                "intended_destination": "exile",
                "from_zone": "hand",
            },
        )
        _inject_game_state("test-no-hand", gs)

        client.post("/game/test-no-hand/choice", json={
            "choice_id": "commander_zone_stay",
        })

        mgr = get_manager()
        result_gs = mgr._games["test-no-hand"]
        p1_result = next(p for p in result_gs.players if p.name == "p1")
        assert len(p1_result.hand) == 0

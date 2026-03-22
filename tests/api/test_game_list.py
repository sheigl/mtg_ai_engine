"""Tests for GET /game (list active games) endpoint."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    mgr._recorders.clear()
    mgr._verbose_loggers.clear()
    yield
    mgr._games.clear()
    mgr._recorders.clear()
    mgr._verbose_loggers.clear()


def _make_deck(size: int = 60) -> list[str]:
    return ["Forest"] * size


def _create_game(p1: str = "Alice", p2: str = "Bob", fmt: str = "standard", seed: int = 42) -> dict:
    resp = client.post("/game", json={
        "player1_name": p1,
        "player2_name": p2,
        "deck1": _make_deck(),
        "deck2": _make_deck(),
        "seed": seed,
        "format": fmt,
    })
    assert resp.status_code == 200
    return resp.json()["data"]


def test_list_games_empty():
    resp = client.get("/game")
    assert resp.status_code == 200
    assert resp.json() == {"data": []}


def test_list_games_single():
    game = _create_game()
    resp = client.get("/game")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    summary = data[0]
    assert summary["game_id"] == game["game_id"]
    assert summary["player1_name"] == "Alice"
    assert summary["player2_name"] == "Bob"
    assert summary["format"] == "standard"
    assert summary["turn"] == 1
    assert "phase" in summary
    assert "step" in summary
    assert summary["is_game_over"] is False
    assert summary["winner"] is None


def test_list_games_multiple():
    _create_game("Alice", "Bob", seed=1)
    _create_game("Carol", "Dave", seed=2)
    resp = client.get("/game")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    names = {(s["player1_name"], s["player2_name"]) for s in data}
    assert ("Alice", "Bob") in names
    assert ("Carol", "Dave") in names


def test_list_games_includes_turn_phase():
    game = _create_game()
    resp = client.get("/game")
    data = resp.json()["data"]
    summary = data[0]
    assert isinstance(summary["turn"], int)
    assert isinstance(summary["phase"], str)
    assert isinstance(summary["step"], str)

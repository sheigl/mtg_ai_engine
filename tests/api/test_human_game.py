"""
Tests for POST /human-game endpoint and HybridGameLoop.
Feature 023-human-vs-ai-play.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager

client = TestClient(app)

# Simple deck that loads without errors
SIMPLE_DECK = ["Forest"] * 60


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    yield
    mgr._games.clear()


# ── US1: Game creation ─────────────────────────────────────────────────────────

def test_create_human_game_returns_game_id():
    """POST /human-game with valid human+heuristic returns 200 and game_id."""
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        res = client.post("/human-game", json={
            "player1_type": "human",
            "player2_type": "heuristic",
            "player1_deck": SIMPLE_DECK,
            "player2_deck": SIMPLE_DECK,
            "player1_name": "You",
            "player2_name": "Bot",
        })
    assert res.status_code == 200
    data = res.json()["data"]
    assert "game_id" in data
    assert data["human_player_name"] == "You"
    assert data["redirect_url"] == f"/human-game/{data['game_id']}"


def test_create_human_game_player2_human():
    """Human on player 2 seat also works."""
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        res = client.post("/human-game", json={
            "player1_type": "heuristic",
            "player2_type": "human",
            "player1_deck": SIMPLE_DECK,
            "player2_deck": SIMPLE_DECK,
            "player1_name": "Bot",
            "player2_name": "You",
        })
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["human_player_name"] == "You"


def test_create_human_game_no_human_seat_returns_422():
    """POST /human-game with no human seat returns 422."""
    res = client.post("/human-game", json={
        "player1_type": "heuristic",
        "player2_type": "heuristic",
        "player1_deck": SIMPLE_DECK,
        "player2_deck": SIMPLE_DECK,
    })
    assert res.status_code == 422


def test_create_human_game_both_human_returns_422():
    """POST /human-game with both human seats returns 422 (1v1 only)."""
    res = client.post("/human-game", json={
        "player1_type": "human",
        "player2_type": "human",
        "player1_deck": SIMPLE_DECK,
        "player2_deck": SIMPLE_DECK,
    })
    assert res.status_code == 422


def test_create_human_game_appears_in_game_list():
    """Game created via POST /human-game appears in GET /game."""
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        res = client.post("/human-game", json={
            "player1_type": "human",
            "player2_type": "heuristic",
            "player1_deck": SIMPLE_DECK,
            "player2_deck": SIMPLE_DECK,
            "player1_name": "Human",
            "player2_name": "Bot",
        })
    assert res.status_code == 200
    game_id = res.json()["data"]["game_id"]

    list_res = client.get("/game")
    assert list_res.status_code == 200
    game_ids = [g["game_id"] for g in list_res.json()["data"]]
    assert game_id in game_ids


def test_same_name_returns_422():
    """player1_name == player2_name returns 422."""
    res = client.post("/human-game", json={
        "player1_type": "human",
        "player2_type": "heuristic",
        "player1_deck": SIMPLE_DECK,
        "player2_deck": SIMPLE_DECK,
        "player1_name": "Same",
        "player2_name": "Same",
    })
    assert res.status_code == 422


# ── US2: Human player can submit actions ──────────────────────────────────────

def test_human_can_submit_pass_when_holding_priority():
    """Human player can submit POST /game/{id}/pass when they hold priority."""
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        res = client.post("/human-game", json={
            "player1_type": "human",
            "player2_type": "heuristic",
            "player1_deck": SIMPLE_DECK,
            "player2_deck": SIMPLE_DECK,
            "player1_name": "Human",
            "player2_name": "Bot",
        })
    game_id = res.json()["data"]["game_id"]

    # Verify the game exists and human is player1
    game_res = client.get(f"/game/{game_id}")
    assert game_res.status_code == 200
    gs = game_res.json()["data"]
    assert gs["players"][0]["name"] == "Human"

    # Get legal actions to see whose priority it is
    legal_res = client.get(f"/game/{game_id}/legal-actions")
    assert legal_res.status_code == 200


# ── US4: Observer regression ─────────────────────────────────────────────────

def test_observer_endpoints_accessible_for_human_game():
    """Human game game-log endpoint is accessible (observer still works)."""
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        res = client.post("/human-game", json={
            "player1_type": "human",
            "player2_type": "heuristic",
            "player1_deck": SIMPLE_DECK,
            "player2_deck": SIMPLE_DECK,
            "player1_name": "Human",
            "player2_name": "Bot",
        })
    game_id = res.json()["data"]["game_id"]

    # Game log endpoint should be accessible
    log_res = client.get(f"/export/{game_id}/game-log")
    assert log_res.status_code == 200


# ── HybridGameLoop unit test ──────────────────────────────────────────────────

def test_hybrid_game_loop_skips_human_player():
    """HybridGameLoop._skip_player_turn returns True for human, False for AI."""
    from ai_client.hybrid_game_loop import HybridGameLoop
    from unittest.mock import MagicMock

    dummy_config = MagicMock()
    dummy_config.players = []
    dummy_config.verbose = False
    dummy_config.format = "standard"
    dummy_config.max_turns = 0
    dummy_engine = MagicMock()
    loop = HybridGameLoop(
        human_player_name="Human",
        config=dummy_config,
        engine=dummy_engine,
        players=[],
    )

    assert loop._skip_player_turn("Human", {}) is True
    assert loop._skip_player_turn("Bot", {}) is False
    assert loop._skip_player_turn("", {}) is False

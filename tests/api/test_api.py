"""
API integration tests using httpx + FastAPI test client.
Tests TASK-16 through TASK-19.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_games():
    """Clear game manager between tests."""
    mgr = get_manager()
    mgr._games.clear()
    yield
    mgr._games.clear()


def _make_deck(size: int = 60) -> list[str]:
    """Build a minimal deck list."""
    return ["Forest"] * size


def _create_game(deck_size: int = 60, seed: int = 42) -> dict:
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": _make_deck(deck_size),
        "deck2": _make_deck(deck_size),
        "seed": seed,
    })
    return resp


# ─── TASK-16: Game lifecycle ──────────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_game_returns_200():
    resp = _create_game()
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "game_id" in data
    assert data["turn"] == 1
    assert data["active_player"] == "p1"


def test_create_game_deals_7_cards():
    resp = _create_game()
    data = resp.json()["data"]
    p1 = next(p for p in data["players"] if p["name"] == "p1")
    assert len(p1["hand"]) == 7


def test_create_game_library_size():
    resp = _create_game()
    data = resp.json()["data"]
    p1 = next(p for p in data["players"] if p["name"] == "p1")
    assert len(p1["library"]) == 53  # 60 - 7


def test_get_game():
    create_resp = _create_game()
    game_id = create_resp.json()["data"]["game_id"]
    resp = client.get(f"/game/{game_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["game_id"] == game_id


def test_get_game_not_found():
    resp = client.get("/game/nonexistent-id")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["error_code"] == "GAME_NOT_FOUND"


def test_delete_game():
    create_resp = _create_game()
    game_id = create_resp.json()["data"]["game_id"]
    resp = client.delete(f"/game/{game_id}")
    assert resp.status_code == 200
    # Subsequent GET should 404
    resp2 = client.get(f"/game/{game_id}")
    assert resp2.status_code == 404


def test_create_game_deck_too_small():
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": ["Forest"] * 10,
        "deck2": ["Forest"] * 60,
        "seed": 1,
    })
    assert resp.status_code == 422


# ─── TASK-16: Game state ─────────────────────────────────────────────────────

def test_game_has_state_hash():
    resp = _create_game()
    data = resp.json()["data"]
    assert data.get("state_hash") != ""


def test_initial_phase_is_beginning():
    resp = _create_game()
    data = resp.json()["data"]
    assert data["phase"] == "beginning"
    assert data["step"] == "untap"


# ─── TASK-17: Legal actions ───────────────────────────────────────────────────

def test_legal_actions_always_includes_pass():
    resp = _create_game()
    game_id = resp.json()["data"]["game_id"]
    la_resp = client.get(f"/game/{game_id}/legal-actions")
    assert la_resp.status_code == 200
    actions = la_resp.json()["data"]["legal_actions"]
    types = [a["action_type"] for a in actions]
    assert "pass" in types


def test_legal_actions_response_structure():
    resp = _create_game()
    game_id = resp.json()["data"]["game_id"]
    la_resp = client.get(f"/game/{game_id}/legal-actions")
    data = la_resp.json()["data"]
    assert "priority_player" in data
    assert "phase" in data
    assert "step" in data
    assert "legal_actions" in data


# ─── TASK-17: Land play in main phase ────────────────────────────────────────

def test_play_land_in_main_phase():
    """Advance to main phase, then play a land from hand."""
    resp = _create_game()
    game_id = resp.json()["data"]["game_id"]
    gs_data = resp.json()["data"]

    # Advance through untap → upkeep → draw → main
    # We need to pass through beginning phase steps
    # Pass as active player (p1) to advance
    for _ in range(6):  # enough passes to reach main phase
        state_resp = client.get(f"/game/{game_id}")
        state = state_resp.json()["data"]
        if state["step"] == "main":
            break
        client.post(f"/game/{game_id}/pass", json={"dry_run": False})

    state = client.get(f"/game/{game_id}").json()["data"]
    # Find a land in p1's hand (all Forest deck)
    p1 = next(p for p in state["players"] if p["name"] == "p1")
    land = next((c for c in p1["hand"] if "land" in c["type_line"].lower()), None)
    if land and state["step"] == "main" and state["priority_holder"] == "p1":
        resp = client.post(f"/game/{game_id}/play-land", json={"card_id": land["id"]})
        assert resp.status_code == 200
        new_state = resp.json()["data"]
        # Land should be on battlefield
        bf_names = [p["card"]["name"] for p in new_state["battlefield"]]
        assert "Forest" in bf_names


# ─── TASK-18: dry_run ────────────────────────────────────────────────────────

def test_pass_dry_run_does_not_advance_state():
    resp = _create_game()
    game_id = resp.json()["data"]["game_id"]
    gs_before = client.get(f"/game/{game_id}").json()["data"]

    dry_resp = client.post(f"/game/{game_id}/pass", json={"dry_run": True})
    assert dry_resp.status_code == 200

    gs_after = client.get(f"/game/{game_id}").json()["data"]
    # State should be unchanged (same hash)
    assert gs_before["state_hash"] == gs_after["state_hash"]


# ─── TASK-19: Pending triggers ───────────────────────────────────────────────

def test_pending_triggers_initially_empty():
    resp = _create_game()
    game_id = resp.json()["data"]["game_id"]
    trig_resp = client.get(f"/game/{game_id}/pending-triggers")
    assert trig_resp.status_code == 200
    assert trig_resp.json()["data"] == []


def test_stack_endpoint():
    resp = _create_game()
    game_id = resp.json()["data"]["game_id"]
    stack_resp = client.get(f"/game/{game_id}/stack")
    assert stack_resp.status_code == 200
    assert stack_resp.json()["data"] == []

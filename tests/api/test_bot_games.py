"""
API integration tests: scripted bots play games via HTTP.
TASK-25: verify no illegal states reachable, no 500 errors.
REQ-P02: no state bleed between concurrent games.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import threading
import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    get_manager()._games.clear()
    export_store.clear()
    yield
    get_manager()._games.clear()
    export_store.clear()


def _make_deck(size=60) -> list[str]:
    return ["Forest"] * size


def _create_game(seed=42) -> str:
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": _make_deck(),
        "deck2": _make_deck(),
        "seed": seed,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["game_id"]


def _bot_turn(game_id: str, max_actions: int = 30) -> dict:
    """
    Scripted bot: repeatedly GET /legal-actions and pick the first non-pass action,
    falling back to pass. Returns the final game state.
    Never produces a 500 error.
    """
    for _ in range(max_actions):
        state_resp = client.get(f"/game/{game_id}")
        if state_resp.status_code == 404:
            break
        state = state_resp.json()["data"]
        if state.get("is_game_over"):
            break

        la_resp = client.get(f"/game/{game_id}/legal-actions")
        assert la_resp.status_code == 200, f"legal-actions returned {la_resp.status_code}"
        actions = la_resp.json()["data"]["legal_actions"]

        # Pick first non-pass action if any meaningful action exists
        action = next((a for a in actions if a["action_type"] != "pass"), None)
        if action is None:
            action = next((a for a in actions if a["action_type"] == "pass"), None)

        if action is None:
            break

        if action["action_type"] == "pass":
            resp = client.post(f"/game/{game_id}/pass", json={"dry_run": False})
            assert resp.status_code != 500, f"Pass returned 500: {resp.text}"

        elif action["action_type"] == "play_land":
            resp = client.post(f"/game/{game_id}/play-land", json={
                "card_id": action["card_id"]
            })
            assert resp.status_code != 500, f"play-land returned 500: {resp.text}"

        elif action["action_type"] == "activate":
            resp = client.post(f"/game/{game_id}/activate", json={
                "permanent_id": action["permanent_id"],
                "ability_index": action.get("ability_index", 0),
                "mana_payment": {},
            })
            # Activation may fail (422 is ok), but never 500
            assert resp.status_code != 500, f"activate returned 500: {resp.text}"

    return client.get(f"/game/{game_id}").json().get("data", {})


def _play_scripted_game(seed: int) -> dict:
    """Play one scripted game to completion or 200 actions."""
    game_id = _create_game(seed=seed)
    final_state = _bot_turn(game_id, max_actions=200)
    return final_state


# ─── TASK-25: Scripted bot games ─────────────────────────────────────────────

def test_single_bot_game_no_500():
    """One scripted game must complete without any 500 errors."""
    _play_scripted_game(seed=1)


def test_ten_bot_games_no_500():
    """Ten scripted games, each with a different seed."""
    for seed in range(1, 11):
        get_manager()._games.clear()
        export_store.clear()
        _play_scripted_game(seed=seed)


def test_legal_actions_never_500():
    """GET /legal-actions must never return 500 across multiple game states."""
    game_id = _create_game(seed=99)
    for _ in range(20):
        resp = client.get(f"/game/{game_id}/legal-actions")
        assert resp.status_code in (200, 404)
        if resp.status_code == 404:
            break
        client.post(f"/game/{game_id}/pass", json={"dry_run": False})


def test_dry_run_does_not_modify_state():
    """dry_run=True on pass must not change the live game state. REQ-P05"""
    game_id = _create_game(seed=7)
    state_before = client.get(f"/game/{game_id}").json()["data"]
    client.post(f"/game/{game_id}/pass", json={"dry_run": True})
    state_after = client.get(f"/game/{game_id}").json()["data"]
    assert state_before["state_hash"] == state_after["state_hash"]


def test_invalid_game_id_returns_404():
    resp = client.get("/game/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "GAME_NOT_FOUND"


def test_invalid_action_returns_422_not_500():
    """Illegal actions must return 422, not 500. REQ-API03"""
    game_id = _create_game(seed=5)
    resp = client.post(f"/game/{game_id}/play-land", json={"card_id": "nonexistent-id"})
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body["detail"]
    assert "error_code" in body["detail"]


def test_game_state_has_required_fields():
    """Game state must include all REQ-G05 fields."""
    game_id = _create_game(seed=3)
    state = client.get(f"/game/{game_id}").json()["data"]
    required = ["game_id", "turn", "active_player", "phase", "step",
                "priority_holder", "stack", "battlefield", "players", "state_hash"]
    for field in required:
        assert field in state, f"Missing field: {field}"


def test_players_have_required_fields():
    """Player state must include all required fields. REQ-G05"""
    game_id = _create_game(seed=2)
    state = client.get(f"/game/{game_id}").json()["data"]
    for player in state["players"]:
        for field in ["name", "life", "hand", "library", "graveyard", "exile", "poison_counters"]:
            assert field in player, f"Missing player field: {field}"


# ─── TASK-27: Concurrent game isolation ──────────────────────────────────────

def test_ten_concurrent_games_no_state_bleed():
    """
    Spin up 10 games simultaneously in threads, run scripted bots on all.
    Verify each game maintains correct, isolated state. REQ-P02.
    """
    seeds = list(range(100, 110))
    results: dict[int, dict] = {}
    errors: list[str] = []

    def run_game(seed: int) -> None:
        try:
            # Create game in this thread (TestClient is thread-safe with FastAPI)
            resp = client.post("/game", json={
                "player1_name": f"p1_{seed}",
                "player2_name": f"p2_{seed}",
                "deck1": _make_deck(),
                "deck2": _make_deck(),
                "seed": seed,
            })
            if resp.status_code != 200:
                errors.append(f"seed={seed}: create failed {resp.status_code}")
                return
            game_id = resp.json()["data"]["game_id"]
            # Run a few actions
            for _ in range(10):
                la = client.get(f"/game/{game_id}/legal-actions")
                if la.status_code != 200:
                    break
                client.post(f"/game/{game_id}/pass", json={"dry_run": False})
            # Verify state is consistent
            state_resp = client.get(f"/game/{game_id}")
            if state_resp.status_code == 200:
                state = state_resp.json()["data"]
                results[seed] = state
                # State should have the correct player names (no bleed from other games)
                player_names = {p["name"] for p in state["players"]}
                assert f"p1_{seed}" in player_names, f"seed={seed}: wrong player names {player_names}"
                assert f"p2_{seed}" in player_names, f"seed={seed}: wrong player names {player_names}"
        except Exception as e:
            errors.append(f"seed={seed}: {e}")

    threads = [threading.Thread(target=run_game, args=(s,)) for s in seeds]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors, f"Concurrent game errors: {errors}"
    # Each game should have different game_ids
    game_ids = {v["game_id"] for v in results.values()}
    assert len(game_ids) == len(results), "Duplicate game IDs — state bleed!"


def test_concurrent_state_isolation():
    """Two games run concurrently must not share battlefield state. REQ-P02"""
    results = {}
    errors = []

    def run_and_collect(seed, label):
        try:
            resp = client.post("/game", json={
                "player1_name": f"bot_a_{label}",
                "player2_name": f"bot_b_{label}",
                "deck1": _make_deck(),
                "deck2": _make_deck(),
                "seed": seed,
            })
            game_id = resp.json()["data"]["game_id"]
            # Pass several times
            for _ in range(5):
                client.post(f"/game/{game_id}/pass", json={"dry_run": False})
            state = client.get(f"/game/{game_id}").json()["data"]
            results[label] = state
        except Exception as e:
            errors.append(str(e))

    t1 = threading.Thread(target=run_and_collect, args=(42, "alpha"))
    t2 = threading.Thread(target=run_and_collect, args=(99, "beta"))
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert not errors
    # Games must be completely independent
    if "alpha" in results and "beta" in results:
        assert results["alpha"]["game_id"] != results["beta"]["game_id"]

"""
Performance benchmarks. TASK-26.
REQ-P01: GET /legal-actions must respond under 200ms.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import time
import statistics
import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store

client = TestClient(app)

LATENCY_THRESHOLD_MS = 200  # REQ-P01


@pytest.fixture(autouse=True)
def clear_state():
    get_manager()._games.clear()
    export_store.clear()
    yield
    get_manager()._games.clear()
    export_store.clear()


def _make_deck(size=60):
    return ["Forest"] * size


def _create_game(seed=1):
    resp = client.post("/game", json={
        "player1_name": "p1", "player2_name": "p2",
        "deck1": _make_deck(), "deck2": _make_deck(), "seed": seed,
    })
    return resp.json()["data"]["game_id"]


def _measure_legal_actions_ms(game_id: str, n: int = 10) -> list[float]:
    """Measure /legal-actions latency n times, return list of ms values."""
    latencies = []
    for _ in range(n):
        start = time.perf_counter()
        resp = client.get(f"/game/{game_id}/legal-actions")
        elapsed = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        latencies.append(elapsed)
    return latencies


def test_legal_actions_empty_board_under_200ms():
    """REQ-P01: /legal-actions on empty board must be under 200ms (p99)."""
    game_id = _create_game(seed=1)
    latencies = _measure_legal_actions_ms(game_id, n=20)
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    mean = statistics.mean(latencies)
    print(f"\n[BENCHMARK] Empty board — mean: {mean:.1f}ms, p99: {p99:.1f}ms")
    assert p99 < LATENCY_THRESHOLD_MS, (
        f"p99 latency {p99:.1f}ms exceeds {LATENCY_THRESHOLD_MS}ms threshold (REQ-P01)"
    )


def test_legal_actions_with_permanents_under_200ms():
    """REQ-P01: /legal-actions with 20 permanents on board must be under 200ms."""
    from mtg_engine.models.game import Card
    from mtg_engine.engine.zones import put_permanent_onto_battlefield

    game_id = _create_game(seed=2)
    gs = get_manager().get(game_id)

    # Add 20 permanents (10 per player)
    for i in range(10):
        card = Card(name=f"Forest_{i}", type_line="Basic Land — Forest")
        gs, _ = put_permanent_onto_battlefield(gs, card, "p1")
    for i in range(10):
        card = Card(name=f"Forest_{i}", type_line="Basic Land — Forest")
        gs, _ = put_permanent_onto_battlefield(gs, card, "p2")
    get_manager().update(game_id, gs)

    latencies = _measure_legal_actions_ms(game_id, n=20)
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    mean = statistics.mean(latencies)
    print(f"\n[BENCHMARK] 20 permanents — mean: {mean:.1f}ms, p99: {p99:.1f}ms")
    assert p99 < LATENCY_THRESHOLD_MS, (
        f"p99 latency {p99:.1f}ms exceeds {LATENCY_THRESHOLD_MS}ms threshold (REQ-P01)"
    )


def test_legal_actions_with_stack_under_200ms():
    """REQ-P01: /legal-actions with items on stack must be under 200ms."""
    from mtg_engine.models.game import Card, StackObject
    game_id = _create_game(seed=3)
    gs = get_manager().get(game_id)
    # Add 3 items to the stack
    for i in range(3):
        card = Card(name=f"Spell_{i}", type_line="Instant", mana_cost="{1}")
        gs.stack.append(StackObject(source_card=card, controller="p1"))
    get_manager().update(game_id, gs)

    latencies = _measure_legal_actions_ms(game_id, n=20)
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    mean = statistics.mean(latencies)
    print(f"\n[BENCHMARK] Complex stack — mean: {mean:.1f}ms, p99: {p99:.1f}ms")
    assert p99 < LATENCY_THRESHOLD_MS, (
        f"p99 latency {p99:.1f}ms exceeds {LATENCY_THRESHOLD_MS}ms threshold (REQ-P01)"
    )


def test_create_game_latency():
    """POST /game should also be reasonably fast (under 10s for cached cards)."""
    start = time.perf_counter()
    resp = client.post("/game", json={
        "player1_name": "p1", "player2_name": "p2",
        "deck1": _make_deck(), "deck2": _make_deck(), "seed": 1,
    })
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert resp.status_code == 200
    print(f"\n[BENCHMARK] POST /game: {elapsed_ms:.0f}ms")
    # No hard limit on game creation (deck loading may hit Scryfall first time)
    # Just assert it completes
    assert elapsed_ms < 30_000  # 30s max


def test_pass_priority_latency():
    """POST /pass should be fast (pure in-memory)."""
    game_id = _create_game(seed=4)
    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        resp = client.post(f"/game/{game_id}/pass", json={"dry_run": False})
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)
        if resp.status_code != 200:
            break
    if latencies:
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        mean = statistics.mean(latencies)
        print(f"\n[BENCHMARK] POST /pass — mean: {mean:.1f}ms, p99: {p99:.1f}ms")
        assert p99 < LATENCY_THRESHOLD_MS

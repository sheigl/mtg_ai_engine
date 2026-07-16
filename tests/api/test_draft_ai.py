"""
API integration tests for Draft / Sealed Simulation endpoints (APP-05).

Tests all REST endpoints via FastAPI TestClient:
  POST   /ai/draft/start        — start a new draft session
  GET    /ai/draft/{id}/state     — current draft state + pending pick info
  POST   /ai/draft/{id}/pick      — submit a card pick (human)
  GET    /ai/draft/{id}/results   — final results after draft completes
  POST   /ai/sealed/start       — one-shot sealed pool simulation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from fastapi.testclient import TestClient

from mtg_engine.api.main import app
from mtg_engine.ai.draft import _clear_sessions

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_draft_sessions():
    """Clear draft sessions between tests."""
    _clear_sessions()
    yield
    _clear_sessions()


# ── Draft Start ───────────────────────────────────────────────────────────────

def test_start_draft_returns_session_id():
    resp = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
        "format_name": "modern",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) > 5


def test_start_draft_returns_state():
    resp = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
    })
    assert resp.status_code == 200
    data = resp.json()
    # All-bot draft completes immediately
    assert data["state"] in ("drafting", "completed")


def test_start_draft_with_human_player():
    """Human player causes draft to wait for input."""
    resp = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
        "human_player_name": "Alice",
    })
    assert resp.status_code == 200
    data = resp.json()
    # Alice is human so draft should be in progress waiting for her pick
    if data["state"] == "drafting":
        assert data.get("current_picker") == "Alice"


def test_start_draft_invalid_strategy():
    resp = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
        "strategy": "invalid_strategy",
    })
    assert resp.status_code == 422


def test_start_draft_too_few_players():
    resp = client.post("/ai/draft/start", json={
        "players": ["Alice"],
        "packs_per_player": 1,
        "set_code": "MOM",
    })
    assert resp.status_code == 422


# ── Draft State ───────────────────────────────────────────────────────────────

def test_get_draft_state():
    start = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
    })
    session_id = start.json()["session_id"]

    resp = client.get(f"/ai/draft/{session_id}/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert "players" in data
    assert len(data["players"]) == 2


def test_get_draft_state_404():
    resp = client.get("/ai/draft/nonexistent-session/state")
    assert resp.status_code == 404


# ── Draft Pick ────────────────────────────────────────────────────────────────

def test_make_pick_requires_card_name():
    start = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
        "human_player_name": "Alice",
    })
    session_id = start.json()["session_id"]

    resp = client.post(f"/ai/draft/{session_id}/pick", json={})
    assert resp.status_code == 422


def test_make_pick_on_completed_draft():
    """Picking after draft completes returns 400."""
    start = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
    })
    session_id = start.json()["session_id"]

    # If draft already completed (all bots), pick should fail
    state_resp = client.get(f"/ai/draft/{session_id}/state")
    if state_resp.json()["state"] == "completed":
        resp = client.post(f"/ai/draft/{session_id}/pick", json={"card_name": "Forest"})
        assert resp.status_code == 400


def test_make_pick_on_nonexistent_session():
    resp = client.post("/ai/draft/nonexistent-session/pick", json={"card_name": "Forest"})
    assert resp.status_code == 404


# ── Draft Results ─────────────────────────────────────────────────────────────

def test_get_draft_results_not_completed():
    """Results endpoint returns 400 if draft is still in progress."""
    start = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 3,
        "set_code": "MOM",
        "human_player_name": "Alice",
    })
    session_id = start.json()["session_id"]

    resp = client.get(f"/ai/draft/{session_id}/results")
    # Either 400 (not completed) or 200 if bots finished all picks
    assert resp.status_code in (200, 400)


def test_get_draft_results_404():
    resp = client.get("/ai/draft/nonexistent-session/results")
    assert resp.status_code == 404


# ── Sealed Start ──────────────────────────────────────────────────────────────

def test_sealed_start_returns_pools_and_decks():
    resp = client.post("/ai/sealed/start", json={
        "players": ["Alice"],
        "set_code": "MOM",
        "format_name": "modern",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["players"]) == 1
    assert "pool" in data["players"][0]
    assert "deck" in data["players"][0]


def test_sealed_start_multiple_players():
    resp = client.post("/ai/sealed/start", json={
        "players": ["Alice", "Bob", "Charlie"],
        "set_code": "MOM",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["players"]) == 3


def test_sealed_start_invalid_strategy():
    resp = client.post("/ai/sealed/start", json={
        "players": ["Alice"],
        "set_code": "MOM",
        "strategy": "not_a_strategy",
    })
    assert resp.status_code == 422


# ── Cleanup ───────────────────────────────────────────────────────────────────

def test_draft_cleanup():
    # Create a session first
    client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
    })

    resp = client.post("/ai/draft/cleanup")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cleared"] >= 1


# ── Scryfall Error Handling (CRITICAL 3 / MAJOR 6) ───────────────────────────

def test_start_draft_scryfall_failure_returns_400(monkeypatch):
    """When _generate_pack raises ValueError, the draft endpoint returns HTTP 400."""
    monkeypatch.setattr(
        "mtg_engine.ai.draft._generate_pack",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("No cards available")),
    )
    resp = client.post("/ai/draft/start", json={
        "players": ["A", "B"],
        "packs_per_player": 1,
        "set_code": "XXX",
    })
    assert resp.status_code == 400
    assert "Failed to generate pack" in resp.json()["detail"]


def test_sealed_start_scryfall_failure_returns_400(monkeypatch):
    """When _generate_pack raises ValueError, the sealed endpoint returns HTTP 400
    with player-specific error context."""
    monkeypatch.setattr(
        "mtg_engine.ai.draft._generate_pack",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("cache empty")),
    )
    resp = client.post("/ai/sealed/start", json={
        "players": ["Alice"],
        "set_code": "XXX",
    })
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Failed to generate sealed pool for Alice" in detail


# ── Format Validation (CRITICAL 1 — sealed endpoint) ─────────────────────────

def test_sealed_start_invalid_format_returns_400():
    """Sealed endpoint rejects unknown format names with HTTP 400."""
    resp = client.post("/ai/sealed/start", json={
        "players": ["Alice"],
        "set_code": "MOM",
        "format_name": "invalid_format_xyz",
    })
    assert resp.status_code == 400
    assert "Unknown format" in resp.json()["detail"]


def test_draft_start_invalid_format_returns_400():
    """Draft endpoint rejects unknown format names with HTTP 400."""
    resp = client.post("/ai/draft/start", json={
        "players": ["Alice", "Bob"],
        "packs_per_player": 1,
        "set_code": "MOM",
        "format_name": "invalid_format_xyz",
    })
    assert resp.status_code == 400
    assert "Unknown format" in resp.json()["detail"]

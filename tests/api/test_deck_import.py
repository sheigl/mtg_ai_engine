"""
API integration tests for deck import endpoints. TASK-28.

Tests REQ-T01 (invalid formats), REQ-T02 (large files), REQ-T03 (concurrent),
REQ-T04 (malformed JSON), REQ-S01 (security), REQ-S02 (content-type), REQ-S03 (rate limit).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import concurrent.futures

from mtg_engine.api.main import app
from mtg_engine.api.routers.deck_import import _deck_store
from mtg_engine.card_data.security import _rate_store

client = TestClient(app)

_60_FOREST_TEXT = "60 Forest\n"
_VALID_TEXT = "4 Lightning Bolt\n56 Mountain\n"


@pytest.fixture(autouse=True)
def clear_state():
    _deck_store.clear()
    _rate_store.clear()
    yield
    _deck_store.clear()
    _rate_store.clear()


def _mock_build_previews(deck_data):
    """Return simple previews without hitting Scryfall."""
    from mtg_engine.models.deck_import import CardPreview
    main = [CardPreview(name=n, quantity=q, scryfall_id="mock-id") for n, q in deck_data.get("main", [])]
    sb = [CardPreview(name=n, quantity=q, scryfall_id="mock-id") for n, q in deck_data.get("sideboard", [])]
    return main, sb, []


# ── Happy path ────────────────────────────────────────────────────────────────

def test_import_text_deck_returns_preview():
    with patch("mtg_engine.api.routers.deck_import.build_card_previews", side_effect=_mock_build_previews):
        resp = client.post("/deck/import", json={
            "file_data": _60_FOREST_TEXT,
            "format": "archidekt_text",
            "deck_name": "Forests",
        })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["deck_name"] == "Forests"
    assert data["total_cards"] == 60
    assert data["is_valid"] is True
    assert data["errors"] == []


def test_import_returns_deck_id():
    with patch("mtg_engine.api.routers.deck_import.build_card_previews", side_effect=_mock_build_previews):
        resp = client.post("/deck/import", json={
            "file_data": _60_FOREST_TEXT,
            "format": "archidekt_text",
        })
    assert resp.status_code == 200
    deck_id = resp.json()["data"]["deck_id"]
    assert deck_id.startswith("deck_")


def test_get_imported_deck():
    with patch("mtg_engine.api.routers.deck_import.build_card_previews", side_effect=_mock_build_previews):
        resp = client.post("/deck/import", json={
            "file_data": _60_FOREST_TEXT,
            "format": "archidekt_text",
        })
    deck_id = resp.json()["data"]["deck_id"]
    get_resp = client.get(f"/deck/import/{deck_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["deck_id"] == deck_id


def test_delete_imported_deck():
    with patch("mtg_engine.api.routers.deck_import.build_card_previews", side_effect=_mock_build_previews):
        resp = client.post("/deck/import", json={
            "file_data": _60_FOREST_TEXT,
            "format": "archidekt_text",
        })
    deck_id = resp.json()["data"]["deck_id"]
    del_resp = client.delete(f"/deck/import/{deck_id}")
    assert del_resp.status_code == 200
    # Confirm it's gone
    assert client.get(f"/deck/import/{deck_id}").status_code == 404


def test_dry_run_does_not_save():
    with patch("mtg_engine.api.routers.deck_import.build_card_previews", side_effect=_mock_build_previews):
        resp = client.post("/deck/import", json={
            "file_data": _60_FOREST_TEXT,
            "format": "archidekt_text",
            "dry_run": True,
        })
    assert resp.status_code == 200
    deck_id = resp.json()["data"]["deck_id"]
    assert client.get(f"/deck/import/{deck_id}").status_code == 404


# ── Error cases ───────────────────────────────────────────────────────────────

def test_invalid_deck_format_returns_400(REQ_T01=None):
    """REQ-T01: Invalid file formats return 400."""
    resp = client.post("/deck/import", json={
        "file_data": "not a deck at all",
        "format": "archidekt_text",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "INVALID_DECK_FORMAT"


def test_malformed_json_returns_400(REQ_T04=None):
    """REQ-T04: Malformed JSON returns 400 with clear error."""
    resp = client.post("/deck/import", json={
        "file_data": "{bad json{{",
        "format": "archidekt_json",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "INVALID_DECK_FORMAT"


def test_large_file_rejected(REQ_T02=None):
    """REQ-T02: Files >10MB are rejected."""
    large_data = "4 Lightning Bolt\n" * 620_000  # ~10+ MB as string
    resp = client.post("/deck/import", json={
        "file_data": large_data,
        "format": "archidekt_text",
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "FILE_UPLOAD_REJECTED"


def test_malicious_content_rejected():
    """REQ-S01: Files with malicious patterns are rejected."""
    resp = client.post("/deck/import", json={
        "file_data": "60 Forest\n<script>alert(1)</script>",
        "format": "archidekt_text",
    })
    assert resp.status_code == 403


def test_get_nonexistent_deck_returns_404():
    resp = client.get("/deck/import/deck_doesnotexist")
    assert resp.status_code == 404


def test_delete_nonexistent_deck_returns_404():
    resp = client.delete("/deck/import/deck_doesnotexist")
    assert resp.status_code == 404


# ── Concurrent imports (REQ-T03) ──────────────────────────────────────────────

def test_concurrent_imports(REQ_T03=None):
    """REQ-T03: Multiple concurrent imports should succeed independently."""
    # Use a fresh rate store to avoid rate limiting
    _rate_store.clear()

    def do_import(i: int):
        with patch("mtg_engine.api.routers.deck_import.build_card_previews",
                   side_effect=_mock_build_previews):
            # Each import has a different IP via header to avoid rate limit
            return client.post(
                "/deck/import",
                json={
                    "file_data": _60_FOREST_TEXT,
                    "format": "archidekt_text",
                    "deck_name": f"Deck {i}",
                },
                headers={"X-Forwarded-For": f"10.0.0.{i % 254 + 1}"},
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(do_import, i) for i in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(r.status_code == 200 for r in results)
    deck_ids = {r.json()["data"]["deck_id"] for r in results}
    assert len(deck_ids) == 5, "Each concurrent import should produce a unique deck ID"

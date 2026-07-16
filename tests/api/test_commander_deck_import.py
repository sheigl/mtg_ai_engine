"""
Regression tests for Commander deck import bug fix (021).

Bug: load_commander_deck expected the commander to be inside the 100-card list,
but DEFAULT_COMMANDER_DECK and natural API usage pass 99 non-commander cards
with the commander specified separately via the commander1/commander2 fields.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.models.game import Card

client = TestClient(app)

COMMANDER_NAME = "Ghalta, Primal Hunger"
_DECK_99 = ["Forest"] * 99  # 99 cards, commander NOT included


def _make_commander_card(name: str = COMMANDER_NAME) -> Card:
    return Card(
        id="cmd-id",
        name=name,
        mana_cost="{10}{G}{G}",
        cmc=12,
        type_line="Legendary Creature — Dinosaur",
        oracle_text="Trample",
        power="12",
        toughness="12",
        color_identity=["G"],
    )


def _make_library_card(name: str, color_identity=None) -> Card:
    return Card(
        id=f"card-{name[:4]}",
        name=name,
        mana_cost="{G}",
        cmc=1,
        type_line="Creature — Elf",
        oracle_text="",
        power="1",
        toughness="1",
        color_identity=color_identity or ["G"],
    )


@pytest.fixture(autouse=True)
def clear_games():
    mgr = get_manager()
    mgr._games.clear()
    yield
    mgr._games.clear()


def _mock_load_commander_deck(card_names, commander_name, db_path=None):
    """Mock that validates our normalisation: commander must be in card_names."""
    if commander_name not in card_names:
        raise ValueError(f"Commander '{commander_name}' not found in deck")
    remaining = [_make_library_card(n) for n in card_names if n != commander_name][:99]
    if len(remaining) != 99:
        raise ValueError(f"Commander deck must contain 99 cards (plus commander), got {len(remaining)}")
    return remaining, _make_commander_card(commander_name)


@patch("mtg_engine.api.routers.game.load_commander_deck", side_effect=_mock_load_commander_deck)
def test_commander_game_with_99_card_list_no_commander(mock_load):
    """99-card list (commander NOT in list) — the fix appends it before calling load_commander_deck."""
    assert len(_DECK_99) == 99
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": _DECK_99,
        "deck2": _DECK_99,
        "format": "commander",
        "commander1": COMMANDER_NAME,
        "commander2": COMMANDER_NAME,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["players"][0]["life"] == 40
    assert data["players"][1]["life"] == 40
    assert any(c["name"] == COMMANDER_NAME for c in data["players"][0]["command_zone"])
    assert any(c["name"] == COMMANDER_NAME for c in data["players"][1]["command_zone"])


@patch("mtg_engine.api.routers.game.load_commander_deck", side_effect=_mock_load_commander_deck)
def test_commander_game_with_100_card_list_including_commander(mock_load):
    """100-card list (commander IS in list) — should still work (no double-append)."""
    deck_100 = _DECK_99 + [COMMANDER_NAME]
    assert len(deck_100) == 100
    resp = client.post("/game", json={
        "player1_name": "p1",
        "player2_name": "p2",
        "deck1": deck_100,
        "deck2": deck_100,
        "format": "commander",
        "commander1": COMMANDER_NAME,
        "commander2": COMMANDER_NAME,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["players"][0]["life"] == 40
    assert any(c["name"] == COMMANDER_NAME for c in data["players"][0]["command_zone"])

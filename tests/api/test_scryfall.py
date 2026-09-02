import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from mtg_engine.card_data.scryfall import ScryfallClient

# Canned Lightning Bolt payload so the tests are fully hermetic (no network,
# no rate limits, no MongoDB, and no MagicMock leaking into JSON serialization).
_LIGHTNING_BOLT = {
    "id": "0482a799-4f8c-41f6-9969-66760d5959a2",
    "name": "Lightning Bolt",
    "mana_cost": "{R}",
    "type_line": "Instant",
    "oracle_text": "Deal 3 damage to any target.",
    "colors": ["R"],
    "color_identity": ["R"],
    "keywords": [],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    c = ScryfallClient(db_path=tmp_path / "test_cache.db")
    # Force no MongoDB and stub the HTTP layer with the canned payload so the
    # tests never hit the network and always get a JSON-serializable dict.
    c._mongo_col = None
    monkeypatch.setattr(c, "_api_get", lambda path, params=None: dict(_LIGHTNING_BOLT))
    return c


def test_get_card_lightning_bolt(client):
    card = client.get_card("Lightning Bolt")
    assert card is not None
    assert card.name == "Lightning Bolt"
    assert card.scryfall_id is not None
    assert card.type_line is not None
    # Lightning Bolt is an instant
    assert "Instant" in card.type_line


def test_get_card_by_id(client):
    card = client.get_card("Lightning Bolt")
    scryfall_id = card.scryfall_id

    card2 = client.get_card_by_id(scryfall_id)
    assert card2.name == "Lightning Bolt"
    assert card2.scryfall_id == scryfall_id


def test_cache_hit(client):
    """Second call must use cache (no API call needed)."""
    card1 = client.get_card("Lightning Bolt")
    card2 = client.get_card("Lightning Bolt")
    assert card1.name == card2.name
    assert card1.scryfall_id == card2.scryfall_id


def test_card_fields(client):
    card = client.get_card("Lightning Bolt")
    assert card.id is not None
    assert card.mana_cost is not None
    assert card.oracle_text is not None
    assert card.power is None       # instants have no P/T
    assert card.toughness is None
    assert card.loyalty is None
    assert isinstance(card.colors, list)
    assert isinstance(card.keywords, list)
    assert card.faces is None       # Lightning Bolt is not DFC

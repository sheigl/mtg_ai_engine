import pytest
from card_data.scryfall import ScryfallClient
from models import CardModel

@pytest.fixture
def scryfall_client():
    return ScryfallClient()

def test_get_card_by_name(scryfall_client):
    card = scryfall_client.get_card("Lightning Bolt")
    assert card is not None
    assert card.name == "Lightning Bolt"
    assert card.mana_cost == "{1}{R}"
    assert card.type_line == "Instant"
    assert card.oracle_text == "Deal 3 damage to any target."

def test_get_card_by_id(scryfall_client):
    # Get the ID from the first test's result
    card = scryfall_client.get_card("Lightning Bolt")
    scryfall_id = card.id
    
    card_by_id = scryfall_client.get_card_by_id(scryfall_id)
    assert card_by_id is not None
    assert card_by_id.name == "Lightning Bolt"
    assert card_by_id.id == scryfall_id

def test_cache_usage(scryfall_client):
    # First call should hit API
    card1 = scryfall_client.get_card("Lightning Bolt")
    
    # Second call should hit cache
    card2 = scryfall_client.get_card("Lightning Bolt")
    assert card2 is not None
    assert card2.name == "Lightning Bolt"

def test_card_model_mapping(scryfall_client):
    card = scryfall_client.get_card("Lightning Bolt")
    assert card.id is not None
    assert card.name is not None
    assert card.mana_cost is not None
    assert card.type_line is not None
    assert card.oracle_text is not None
    assert card.power is None
    assert card.toughness is None
    assert card.loyalty is None
    assert card.colors is not None
    assert card.keywords is not None
    assert card.faces is None
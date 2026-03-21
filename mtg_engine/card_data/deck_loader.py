import time
import uuid
from mtg_engine.card_data.scryfall import ScryfallClient
from mtg_engine.models.game import Card


def load_deck(card_names: list[str], db_path: str | None = None) -> list[Card]:
    """
    Resolve card names via ScryfallClient and return a list of Card instances
    with unique instance IDs. Validates 60-card minimum. REQ-G01
    """
    kwargs = {"db_path": db_path} if db_path else {}
    client = ScryfallClient(**kwargs)
    cards: list[Card] = []

    for name in card_names:
        card = client.get_card(name)
        # Assign a fresh unique instance ID for each copy
        card = card.model_copy(update={"id": str(uuid.uuid4())})
        cards.append(card)

    if len(cards) < 60:
        raise ValueError(f"Deck must contain at least 60 cards, got {len(cards)}")

    return cards

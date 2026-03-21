import time
import uuid
from mtg_engine.card_data.scryfall import ScryfallClient
from mtg_engine.models.game import Card

_BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}


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


def load_commander_deck(
    card_names: list[str],
    commander_name: str,
    db_path: str | None = None,
) -> tuple[list[Card], Card]:
    """
    Resolve and validate a Commander-format deck.

    Returns (deck_cards, commander_card) where deck_cards is the 99-card library
    (commander removed) and commander_card is the resolved commander Card.

    Raises ValueError with a specific message on any violation:
      - Commander not found in deck
      - Commander is not a legendary creature
      - Deck is not exactly 99 cards after removing commander
      - Singleton violation (duplicate non-basic-land card)
      - Color identity violation
    """
    kwargs = {"db_path": db_path} if db_path else {}
    client = ScryfallClient(**kwargs)

    cards: list[Card] = []
    for name in card_names:
        card = client.get_card(name)
        card = card.model_copy(update={"id": str(uuid.uuid4())})
        cards.append(card)

    # Find and remove the commander from the deck
    commander_card: Card | None = None
    remaining: list[Card] = []
    found = False
    for card in cards:
        if not found and card.name == commander_name:
            commander_card = card
            found = True
        else:
            remaining.append(card)

    if commander_card is None:
        raise ValueError(f"Commander '{commander_name}' not found in deck")

    # Validate commander is a legendary creature
    tl = commander_card.type_line.lower()
    if "legendary" not in tl or "creature" not in tl:
        raise ValueError(
            f"Commander must be a legendary creature; '{commander_name}' has type '{commander_card.type_line}'"
        )

    # Validate deck size: must be exactly 99 cards after removing the commander
    if len(remaining) != 99:
        raise ValueError(
            f"Commander deck must contain 99 cards (plus commander), got {len(remaining)}"
        )

    # Validate singleton (no duplicates among non-basic lands)
    name_counts: dict[str, int] = {}
    for card in remaining:
        if card.name not in _BASIC_LAND_NAMES:
            name_counts[card.name] = name_counts.get(card.name, 0) + 1
    for name, count in name_counts.items():
        if count > 1:
            raise ValueError(
                f"Singleton violation: '{name}' appears {count} times in the deck"
            )

    # Validate color identity
    commander_identity = set(commander_card.color_identity)
    for card in remaining:
        card_identity = set(card.color_identity)
        if not card_identity.issubset(commander_identity):
            extra = card_identity - commander_identity
            raise ValueError(
                f"Color identity violation: '{card.name}' has colors {sorted(extra)} "
                f"not in commander identity {sorted(commander_identity)}"
            )

    return remaining, commander_card

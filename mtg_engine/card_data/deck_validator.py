"""
Deck validation: card resolution and format legality checks.

REQ-P01: Cache card lookups, batch resolution
"""

import logging
import uuid

from mtg_engine.card_data.scryfall import ScryfallClient
from mtg_engine.models.game import Card
from mtg_engine.models.deck_import import CardPreview

logger = logging.getLogger(__name__)

_client: ScryfallClient | None = None


def _get_client() -> ScryfallClient:
    global _client
    if _client is None:
        _client = ScryfallClient()
    return _client


def resolve_cards(
    card_names: list[str],
) -> tuple[list[Card], list[str]]:
    """
    Resolve card names via ScryfallClient.

    Returns (resolved_cards, unresolved_names).
    Each resolved card gets a unique instance ID.
    """
    client = _get_client()
    resolved: list[Card] = []
    unresolved: list[str] = []

    for name in card_names:
        try:
            card = client.get_card(name)
            card = card.model_copy(update={"id": str(uuid.uuid4())})
            resolved.append(card)
        except Exception as exc:
            logger.warning("Could not resolve card %r: %s", name, exc)
            unresolved.append(name)

    return resolved, unresolved


def validate_deck_format(
    deck_data: dict,
) -> tuple[bool, list[str]]:
    """
    Validate deck structure from parsed deck_data dict
    ({"main": [(name, qty)], "sideboard": [(name, qty)]}).

    Returns (is_valid, error_list).
    """
    errors: list[str] = []
    main = deck_data.get("main", [])
    sideboard = deck_data.get("sideboard", [])

    total_main = sum(qty for _, qty in main)
    if total_main < 60:
        errors.append(f"Main deck has {total_main} cards; minimum is 60.")

    total_sb = sum(qty for _, qty in sideboard)
    if total_sb > 15:
        errors.append(f"Sideboard has {total_sb} cards; maximum is 15.")

    return len(errors) == 0, errors


def build_card_previews(
    deck_data: dict,
) -> tuple[list[CardPreview], list[CardPreview], list[str]]:
    """
    Resolve all cards in deck_data and build CardPreview lists.

    Returns (main_previews, sideboard_previews, unresolved_names).
    Unresolved cards are still included in previews with is_legal=False.
    """
    client = _get_client()
    main_previews: list[CardPreview] = []
    sideboard_previews: list[CardPreview] = []
    unresolved: list[str] = []

    def _resolve_preview(name: str, qty: int) -> CardPreview:
        try:
            card = client.get_card(name)
            return CardPreview(
                name=card.name,
                quantity=qty,
                scryfall_id=card.id,
                is_legal=True,
            )
        except Exception as exc:
            logger.warning("Cannot resolve %r: %s", name, exc)
            unresolved.append(name)
            return CardPreview(name=name, quantity=qty, is_legal=False)

    for name, qty in deck_data.get("main", []):
        main_previews.append(_resolve_preview(name, qty))

    for name, qty in deck_data.get("sideboard", []):
        sideboard_previews.append(_resolve_preview(name, qty))

    return main_previews, sideboard_previews, unresolved

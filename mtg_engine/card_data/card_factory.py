"""
Card factory for creating Card objects from oracle text and type_line.
CRD-02: Cards can be created from oracle text without Scryfall API.
"""
import re
import uuid
from typing import Optional

from mtg_engine.models.game import Card, CardFace


def create_card(
    name: str,
    oracle_text: str = "",
    type_line: str = "",
    mana_cost: str = "",
    power: Optional[str] = None,
    toughness: Optional[str] = None,
    loyalty: Optional[str] = None,
    colors: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    faces: Optional[list[CardFace]] = None,
    card_layout: str = "normal",
) -> Card:
    """
    Create a Card object with all fields populated from minimal input.
    Colors and CMC are derived from mana_cost if not provided.
    Keywords are extracted from oracle_text using the known keyword list.
    """
    _colors = _derive_colors(mana_cost) if colors is None else list(colors)
    _keywords = list(keywords) if keywords is not None else _extract_keywords(oracle_text)
    _cmc = _compute_cmc(mana_cost)

    return Card(
        id=str(uuid.uuid4()),
        name=name,
        mana_cost=mana_cost or None,
        type_line=type_line,
        oracle_text=oracle_text or None,
        power=power,
        toughness=toughness,
        loyalty=loyalty,
        colors=_colors,
        color_identity=list(_colors),
        keywords=_keywords,
        cmc=_cmc,
        card_layout=card_layout,
        faces=list(faces) if faces else None,
    )


def _derive_colors(mana_cost: str) -> list[str]:
    """Extract color identity from a mana cost string."""
    color_symbols = {"W", "U", "B", "R", "G"}
    found: list[str] = []
    for sym in re.findall(r"\{([^}]+)\}", mana_cost or ""):
        if sym in color_symbols and sym not in found:
            found.append(sym)
        elif "/" in sym:
            for part in sym.split("/"):
                if part in color_symbols and part not in found:
                    found.append(part)
    return found


def _compute_cmc(mana_cost: str) -> float:
    """Compute converted mana cost from a mana cost string."""
    from mtg_engine.engine.mana import parse_mana_cost
    parsed = parse_mana_cost(mana_cost or "")
    total = 0.0
    for sym, count in parsed.items():
        if sym == "generic":
            total += count
        elif sym == "X":
            pass  # X counts as 0 for CMC purposes in most contexts
        elif "/" in sym:
            total += count  # hybrid = 1 regardless of which half is paid
        else:
            total += count
    return total


def _extract_keywords(oracle_text: str) -> list[str]:
    """
    Extract known keywords from oracle text.
    Uses the KEYWORDS frozenset from ability_parser.
    """
    from mtg_engine.card_data.ability_parser import KEYWORDS
    text = (oracle_text or "").lower()
    found: list[str] = []
    for kw in sorted(KEYWORDS, key=len, reverse=True):
        if kw in text:
            found.append(kw)
    return found


def make_creature(
    name: str,
    power: str,
    toughness: str,
    oracle_text: str = "",
    type_line: str = "Creature",
    mana_cost: str = "",
    keywords: Optional[list[str]] = None,
    colors: Optional[list[str]] = None,
) -> Card:
    """Shortcut to create a creature card."""
    return create_card(
        name=name,
        oracle_text=oracle_text,
        type_line=type_line,
        mana_cost=mana_cost,
        power=power,
        toughness=toughness,
        keywords=keywords,
        colors=colors,
    )


def make_basic_land(
    name: str = "Mountain",
    color: str = "R",
) -> Card:
    """Shortcut to create a basic land card."""
    mana_symbol = {"W": "{W}", "U": "{U}", "B": "{B}", "R": "{R}", "G": "{G}"}
    return create_card(
        name=name,
        type_line="Basic Land — Mountain" if name == "Mountain" else f"Basic Land — {name}",
        mana_cost="",
        colors=[color],
        keywords=[],
        card_layout="normal",
    )


def make_instant_or_sorcery(
    name: str,
    oracle_text: str,
    mana_cost: str = "",
    card_type: str = "Instant",
    colors: Optional[list[str]] = None,
) -> Card:
    """Shortcut to create an instant or sorcery card."""
    return create_card(
        name=name,
        oracle_text=oracle_text,
        type_line=card_type,
        mana_cost=mana_cost,
        colors=colors or _derive_colors(mana_cost),
    )


def make_enchantment(
    name: str,
    oracle_text: str = "",
    type_line: str = "Enchantment",
    mana_cost: str = "",
    colors: Optional[list[str]] = None,
) -> Card:
    """Shortcut to create an enchantment card."""
    return create_card(
        name=name,
        oracle_text=oracle_text,
        type_line=type_line,
        mana_cost=mana_cost,
        colors=colors or _derive_colors(mana_cost),
    )


def make_artifact(
    name: str,
    oracle_text: str = "",
    type_line: str = "Artifact",
    mana_cost: str = "",
    colors: Optional[list[str]] = None,
) -> Card:
    """Shortcut to create an artifact card."""
    return create_card(
        name=name,
        oracle_text=oracle_text,
        type_line=type_line,
        mana_cost=mana_cost,
        colors=colors or [],
    )

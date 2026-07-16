"""
Format rules engine (FMT-01).

Dispatcher + per-format validators for deck legality checks.
All functions are pure — no side effects.
"""
import logging
from collections.abc import Callable
from typing import Optional, Union

from mtg_engine.engine.formats.banned import is_banned, is_restricted
from mtg_engine.models.game import Card

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legality windows per format (set codes)
# Only sets listed here are legal; empty set means no window restriction.
# Representative samples for MVP — production would use a comprehensive list.
# ---------------------------------------------------------------------------

LEGAL_SETS: dict[str, set[str]] = {
    "standard": {"MKM", "LTC", "BLI", "MH1", "BMR", "TRK"},
    "pioneer": {
        # RNA onward — representative sample
        "RNA", "MOM", "MID", "XIN", "KHC", "STR", "STX", "AFR",
        "CMM", "DGM", "DMU", "JOU", "BLB", "MOM2", "ONE", "MOM3",
    },
    "modern": {
        # 8ED onward — representative sample
        "8ED", "M19", "GRN", "RNA", "MOM", "MID", "XIN", "KHC",
        "STR", "STX", "AFR", "CMM", "DGM", "DMU", "JOU", "BLB",
    },
    "legacy": set(),   # no legality window
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def validate_deck(
    cards: list[Card],
    format_name: str,
    commanders: Optional[list[Card]] = None,
) -> tuple[bool, list[str]]:
    """
    Validate a deck for the given format.

    Returns (is_valid, violations). An empty violation list means the deck is legal.
    Unknown formats return False with a descriptive error.
    """
    fmt = format_name.lower().strip()

    validator = FORMAT_VALIDATORS.get(fmt)
    if validator is None:
        return False, [f"Unknown format: {format_name}"]

    # Commander and Brawl receive the commanders list; others ignore it
    if fmt in ("commander", "brawl"):
        return validator(cards, commanders or [])
    else:
        return validator(cards)


# ---------------------------------------------------------------------------
# Format validators
# ---------------------------------------------------------------------------

def _validate_standard(cards: list[Card]) -> tuple[bool, list[str]]:
    """Standard: min 60 cards, banned list, legality window via set_code."""
    violations: list[str] = []

    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, must have at least 60")

    for card in cards:
        if is_banned(card.name, "standard"):
            violations.append(f"{card.name} is banned in Standard")

    # Legality window check (only flag cards with a set_code outside the window)
    legal = LEGAL_SETS.get("standard", set())
    legal_upper = {s.upper() for s in legal}
    for card in cards:
        if card.set_code and card.set_code.upper() not in legal_upper:
            violations.append(
                f"{card.name} (set {card.set_code}) is not legal in Standard"
            )

    return len(violations) == 0, violations


def _validate_pioneer(cards: list[Card]) -> tuple[bool, list[str]]:
    """Pioneer: min 60 cards, banned list, legality window via set_code."""
    violations: list[str] = []

    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, must have at least 60")

    for card in cards:
        if is_banned(card.name, "pioneer"):
            violations.append(f"{card.name} is banned in Pioneer")

    legal = LEGAL_SETS.get("pioneer", set())
    legal_upper = {s.upper() for s in legal}
    for card in cards:
        if card.set_code and card.set_code.upper() not in legal_upper:
            violations.append(
                f"{card.name} (set {card.set_code}) is not legal in Pioneer"
            )

    return len(violations) == 0, violations


def _validate_modern(cards: list[Card]) -> tuple[bool, list[str]]:
    """Modern: min 60 cards, banned list, legality window via set_code."""
    violations: list[str] = []

    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, must have at least 60")

    for card in cards:
        if is_banned(card.name, "modern"):
            violations.append(f"{card.name} is banned in Modern")

    legal = LEGAL_SETS.get("modern", set())
    legal_upper = {s.upper() for s in legal}
    for card in cards:
        if card.set_code and card.set_code.upper() not in legal_upper:
            violations.append(
                f"{card.name} (set {card.set_code}) is not legal in Modern"
            )

    return len(violations) == 0, violations


def _validate_legacy(cards: list[Card]) -> tuple[bool, list[str]]:
    """Legacy: min 60 cards, banned list only — no legality window."""
    violations: list[str] = []

    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, must have at least 60")

    for card in cards:
        if is_banned(card.name, "legacy"):
            violations.append(f"{card.name} is banned in Legacy")

    return len(violations) == 0, violations


def _validate_vintage(cards: list[Card]) -> tuple[bool, list[str]]:
    """Vintage: min 60 cards, banned + restricted (max 1 copy of restricted)."""
    violations: list[str] = []

    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, must have at least 60")

    # Count card names for restricted check
    name_counts: dict[str, int] = {}
    for card in cards:
        key = card.name.lower()
        name_counts[key] = name_counts.get(key, 0) + 1

    for card in cards:
        if is_banned(card.name, "vintage"):
            violations.append(f"{card.name} is banned in Vintage")

    # Restricted check — report each unique restricted card only once
    restricted_reported: set[str] = set()
    for card in cards:
        key = card.name.lower()
        if is_restricted(card.name) and key not in restricted_reported:
            restricted_reported.add(key)
            count = name_counts[key]
            if count > 1:
                violations.append(
                    f"{card.name} is restricted (max 1 copy, found {count})"
                )

    return len(violations) == 0, violations


def _validate_commander(
    cards: list[Card],
    commanders: list[Card],
) -> tuple[bool, list[str]]:
    """Commander: delegates to existing commander.py validator + banned list."""
    from mtg_engine.engine.formats.commander import validate_deck_for_commander

    is_valid, violations = validate_deck_for_commander(cards, commanders)

    # Additional banned-list check on top of commander rules
    for card in cards:
        if is_banned(card.name, "commander"):
            violations.append(f"{card.name} is banned in Commander")

    return len(violations) == 0, violations


def _validate_brawl(
    cards: list[Card],
    commanders: list[Card],
) -> tuple[bool, list[str]]:
    """Brawl: exactly 60 cards, legendary creature/PW commander, Standard legality."""
    violations: list[str] = []

    if len(cards) != 60:
        violations.append(f"Deck has {len(cards)} cards, must have exactly 60")

    # Commander must be a legendary creature or planeswalker
    for cmd in commanders:
        tl = (cmd.type_line or "").lower()
        is_legendary_creature = "legendary" in tl and "creature" in tl
        is_planeswalker = "planeswalker" in tl
        if not (is_legendary_creature or is_planeswalker):
            violations.append(
                f"{cmd.name} ({cmd.type_line}) is not a legendary creature or planeswalker"
            )

    # Standard legality window + both brawl and standard banned lists
    legal = LEGAL_SETS.get("standard", set())
    legal_upper = {s.upper() for s in legal}
    for card in cards:
        if is_banned(card.name, "brawl") or is_banned(card.name, "standard"):
            violations.append(f"{card.name} is banned in Brawl")

        if card.set_code and card.set_code.upper() not in legal_upper:
            violations.append(
                f"{card.name} (set {card.set_code}) is not legal in Brawl"
            )

    return len(violations) == 0, violations


def _validate_pauper(cards: list[Card]) -> tuple[bool, list[str]]:
    """Pauper: min 60 cards, all cards must be common rarity."""
    violations: list[str] = []

    if len(cards) < 60:
        violations.append(f"Deck has {len(cards)} cards, must have at least 60")

    for card in cards:
        # Cards without a rarity set are silently skipped per design doc
        if card.rarity is not None and card.rarity.lower() not in ("c", "common"):
            violations.append(
                f"{card.name} (rarity {card.rarity}) is not common"
            )

    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_FormatValidator = Union[
    Callable[[list["Card"]], tuple[bool, list[str]]],
    Callable[[list["Card"], list["Card"]], tuple[bool, list[str]]],
]

FORMAT_VALIDATORS: dict[str, _FormatValidator] = {
    "standard": _validate_standard,
    "pioneer": _validate_pioneer,
    "modern": _validate_modern,
    "legacy": _validate_legacy,
    "vintage": _validate_vintage,
    "commander": _validate_commander,
    "brawl": _validate_brawl,
    "pauper": _validate_pauper,
}

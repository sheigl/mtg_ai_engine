"""
Archidekt and standard MTG deck format parsers.

Supports:
  - Archidekt JSON API (URL-based)
  - Archidekt/standard text format (e.g. "4 Lightning Bolt")
  - Scryfall text export format

All parsers return: {"main": [(name, qty), ...], "sideboard": [(name, qty), ...]}
"""

import logging
import re
from collections import defaultdict

import httpx

logger = logging.getLogger(__name__)

_BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest",
                "Wastes", "Snow-Covered Plains", "Snow-Covered Island",
                "Snow-Covered Swamp", "Snow-Covered Mountain", "Snow-Covered Forest"}

# Archidekt deck URLs look like: https://archidekt.com/decks/12345/deck-name
_ARCHIDEKT_URL_RE = re.compile(r"archidekt\.com/decks/(\d+)", re.IGNORECASE)


def _extract_archidekt_id(url: str) -> str:
    m = _ARCHIDEKT_URL_RE.search(url)
    if not m:
        raise ValueError(f"Cannot extract deck ID from Archidekt URL: {url!r}")
    return m.group(1)


def parse_archidekt_json(url: str) -> dict:
    """
    Fetch an Archidekt deck by URL and parse its JSON API response.

    Returns {"main": [(name, qty), ...], "sideboard": [(name, qty), ...]}
    """
    deck_id = _extract_archidekt_id(url)
    api_url = f"https://archidekt.com/api/decks/{deck_id}/"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(api_url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()

    main: list[tuple[str, int]] = []
    sideboard: list[tuple[str, int]] = []

    for card_entry in data.get("cards", []):
        qty = card_entry.get("quantity", 1)
        card_info = card_entry.get("card", {})
        # Archidekt nests name under oracleCard or card directly
        oracle = card_info.get("oracleCard", {})
        name = oracle.get("name") or card_info.get("name", "")
        if not name:
            logger.warning("Skipping Archidekt card entry with no name: %s", card_entry)
            continue

        categories = card_entry.get("categories", [])
        if "Sideboard" in categories:
            sideboard.append((name, qty))
        else:
            main.append((name, qty))

    _validate_parsed(main, sideboard)
    return {"main": main, "sideboard": sideboard}


def parse_archidekt_text(content: str) -> dict:
    """
    Parse a standard MTG decklist text format.

    Accepted line formats:
      4 Lightning Bolt
      4x Lightning Bolt
      Lightning Bolt x4

    Sideboard section starts after an empty line or a line containing "Sideboard".
    """
    main, sideboard = _parse_text_format(content)
    _validate_parsed(main, sideboard)
    return {"main": main, "sideboard": sideboard}


def parse_scryfall_txt(content: str) -> dict:
    """
    Parse a Scryfall text export format.

    Same as standard text format; Scryfall exports "4 Lightning Bolt" style.
    """
    main, sideboard = _parse_text_format(content)
    _validate_parsed(main, sideboard)
    return {"main": main, "sideboard": sideboard}


# ── Internal helpers ──────────────────────────────────────────────────────────

_LINE_RE = re.compile(
    r"^(?:(\d+)[xX]?\s+(.+?)|(.+?)\s+[xX](\d+))$"
)
_SIMPLE_RE = re.compile(r"^(\d+)[xX]?\s+(.+)$")


def _parse_line(line: str) -> tuple[str, int] | None:
    """Return (name, qty) from a decklist line, or None if unparseable."""
    line = line.strip()
    if not line or line.startswith("//") or line.startswith("#"):
        return None
    m = _SIMPLE_RE.match(line)
    if m:
        return m.group(2).strip(), int(m.group(1))
    # Try "Name x4" format
    m2 = re.match(r"^(.+?)\s+[xX](\d+)$", line)
    if m2:
        return m2.group(1).strip(), int(m2.group(2))
    # Single card with no quantity
    return line, 1


def _parse_text_format(content: str) -> tuple[list, list]:
    main: list[tuple[str, int]] = []
    sideboard: list[tuple[str, int]] = []
    in_sideboard = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            # An empty line may mark the start of the sideboard section
            continue
        low = line.lower()
        if low in ("sideboard", "sideboard:", "// sideboard", "## sideboard"):
            in_sideboard = True
            continue
        parsed = _parse_line(line)
        if parsed is None:
            continue
        name, qty = parsed
        if in_sideboard:
            sideboard.append((name, qty))
        else:
            main.append((name, qty))

    return main, sideboard


def _validate_parsed(
    main: list[tuple[str, int]],
    sideboard: list[tuple[str, int]],
) -> None:
    """Validate deck size and per-card copy limits. Raises ValueError on failure."""
    total_main = sum(qty for _, qty in main)
    if total_main < 60:
        raise ValueError(
            f"Main deck must contain at least 60 cards; got {total_main}"
        )

    total_sb = sum(qty for _, qty in sideboard)
    if total_sb > 15:
        raise ValueError(
            f"Sideboard must contain at most 15 cards; got {total_sb}"
        )

    # Check 4-copy limit (basic lands are exempt)
    counts: dict[str, int] = defaultdict(int)
    for name, qty in main + sideboard:
        counts[name] += qty

    for name, total in counts.items():
        if name not in _BASIC_LANDS and total > 4:
            raise ValueError(
                f"Deck contains {total} copies of {name!r}; maximum is 4"
            )

"""MTGGoldfish metagame deck scraper and cache. Feature 033-deck-randomizer.

Fetches competitive deck lists from MTGGoldfish metagame pages and caches them
in MongoDB for fast retrieval.
"""
import logging
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# MTGGoldfish metagame URLs
_METAGAME_URLS = {
    "standard": "https://www.mtggoldfish.com/metagame/standard#paper",
    "commander": "https://www.mtggoldfish.com/metagame/commander#paper",
}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class MetagameDeck:
    """Represents a scraped deck from MTGGoldfish."""

    def __init__(
        self,
        name: str,
        format: str,
        cards: list[dict],  # [{"name": str, "quantity": int}, ...]
        commander: Optional[str] = None,
    ):
        self.name = name
        self.format = format
        self.cards = cards
        self.commander = commander

    def to_card_names(self) -> list[str]:
        """Expand cards into a flat list of card names (for deck_loader)."""
        result: list[str] = []
        for c in self.cards:
            result.extend([c["name"]] * c["quantity"])
        return result

    def to_mongo_doc(self) -> dict:
        return {
            "name": self.name,
            "format": self.format,
            "cards": self.cards,
            "commander": self.commander,
            "fetched_at": datetime.now(timezone.utc),
        }

    @classmethod
    def from_mongo_doc(cls, doc: dict) -> "MetagameDeck":
        return cls(
            name=doc["name"],
            format=doc["format"],
            cards=doc["cards"],
            commander=doc.get("commander"),
        )


def _http_get(url: str) -> str:
    """Fetch URL with a browser-like User-Agent."""
    headers = {"User-Agent": _USER_AGENT}
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.text


def scrape_metagame_list(format: str, limit: int = 15) -> list[tuple[str, str]]:
    """
    Scrape the MTGGoldfish metagame page for deck names and URLs.
    Returns list of (deck_name, deck_url) tuples.
    """
    url = _METAGAME_URLS.get(format.lower())
    if not url:
        raise ValueError(f"Unsupported format: {format}")

    html = _http_get(url)
    soup = BeautifulSoup(html, "html.parser")

    decks: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    # MTGGoldfish metagame page links to archetypes
    # Try multiple selectors for robustness
    selectors = [
        ".archetype-tile a[href^='/archetype/']",
        "a[href^='/archetype/']",
        ".deck-tile a[href^='/deck/']",
    ]

    for selector in selectors:
        for link in soup.select(selector):
            href = link.get("href", "")
            name = link.get_text(strip=True)
            if not href or not name:
                continue
            # Normalize URL — strip fragment and deduplicate
            base_href = href.split("#")[0]
            if base_href.startswith("/"):
                base_href = f"https://www.mtggoldfish.com{base_href}"
            if not base_href.startswith("http"):
                continue
            # Strip trailing fragment for dedup
            clean_url = base_href.split("#")[0]
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            # Use the clean URL (paper variant)
            decks.append((name, clean_url))
            if len(decks) >= limit:
                break
        if len(decks) >= limit:
            break

    logger.info("Scraped %d decks from MTGGoldfish %s metagame", len(decks), format)
    return decks[:limit]


def scrape_deck_page(deck_url: str) -> tuple[list[dict], Optional[str]]:
    """
    Scrape a single MTGGoldfish deck page for card list.
    Returns (cards, commander_name).
    """
    html = _http_get(deck_url)
    soup = BeautifulSoup(html, "html.parser")

    cards: list[dict] = []
    commander: Optional[str] = None

    # Primary: grab the hidden input#deck_input_deck which contains the full deck list
    deck_input = soup.find("input", id="deck_input_deck")
    if deck_input and deck_input.get("value"):
        raw = deck_input["value"]
        in_sideboard = False
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.lower() == "sideboard":
                in_sideboard = True
                continue
            if in_sideboard:
                continue  # skip sideboard cards for now
            parts = line.split(None, 1)
            if len(parts) == 2:
                try:
                    qty = int(parts[0])
                    name = parts[1].strip()
                    cards.append({"name": name, "quantity": qty})
                except ValueError:
                    continue
    else:
        # Fallback: try table-based scraping
        for selector in ["#deck-table", ".deck-table", ".table-decklist"]:
            table = soup.select_one(selector)
            if table:
                for row in table.select("tr"):
                    cells = row.select("td")
                    if len(cells) >= 2:
                        qty_text = cells[0].get_text(strip=True)
                        name_text = cells[1].get_text(strip=True)
                        try:
                            qty = int(qty_text)
                        except ValueError:
                            continue
                        if name_text:
                            cards.append({"name": name_text, "quantity": qty})
                if cards:
                    break

        # Last resort: textarea
        if not cards:
            textarea = soup.select_one("textarea#deck_input, textarea.deck-input")
            if textarea:
                for line in textarea.get_text().strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        try:
                            qty = int(parts[0])
                            name = parts[1].strip()
                            cards.append({"name": name, "quantity": qty})
                        except ValueError:
                            continue

    # Try to find commander
    cmd_input = soup.find("input", id="deck_input_commander")
    if cmd_input and cmd_input.get("value"):
        cmd_val = cmd_input["value"].strip()
        if cmd_val:
            commander = cmd_val
    if not commander:
        for header in soup.find_all(["h3", "h4", "h5"]):
            text = header.get_text(strip=True).lower()
            if "commander" in text:
                next_el = header.find_next_sibling()
                if next_el:
                    card_name = next_el.get_text(strip=True)
                    if card_name:
                        commander = card_name
                        break
    if not commander and "commander" in deck_url.lower() and cards:
        commander = cards[0]["name"]

    logger.info("Scraped deck %s: %d cards, commander=%s", deck_url, len(cards), commander)
    return cards, commander


class DeckCache:
    """Cache for metagame decks. Uses MongoDB when available, in-memory dict otherwise."""

    _CACHE_TTL_DAYS = 7

    def __init__(self) -> None:
        self._col = None
        self._memory: dict[str, list[MetagameDeck]] = {}
        try:
            import pymongo
            url = os.environ.get("MONGODB_URL", "")
            if not url.strip():
                url = "mongodb://root:whatever@sheigl-ms-7a38.tailc63ae8.ts.net"
            mc = pymongo.MongoClient(url, serverSelectionTimeoutMS=3000)
            db_name = os.environ.get("MONGODB_DATABASE", "mtg_training")
            col = mc[db_name]["metagame_decks"]
            col.find_one({})
            col.create_index("format")
            col.create_index([("format", 1), ("name", 1)], unique=True)
            self._col = col
            logger.info("DeckCache: MongoDB connected for metagame_decks")
        except Exception as exc:
            logger.warning("DeckCache: MongoDB unavailable, using in-memory cache: %s", exc)

    def _is_configured(self) -> bool:
        return self._col is not None

    def needs_refresh(self, format: str) -> bool:
        """Return True if we should re-fetch decks for this format."""
        fmt = format.lower()
        if self._is_configured():
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=self._CACHE_TTL_DAYS)
                newest = self._col.find_one(
                    {"format": fmt},
                    sort=[("fetched_at", -1)],
                )
                if newest is None:
                    return True
                return newest.get("fetched_at", cutoff) < cutoff
            except Exception:
                return True
        # No MongoDB — check in-memory cache
        if fmt not in self._memory or not self._memory[fmt]:
            return True
        return False

    def save_decks(self, format: str, decks: list[MetagameDeck]) -> None:
        """Store decks in MongoDB and in-memory cache."""
        fmt = format.lower()
        self._memory[fmt] = decks
        if not self._is_configured():
            return
        for deck in decks:
            try:
                doc = deck.to_mongo_doc()
                self._col.update_one(
                    {"format": doc["format"], "name": doc["name"]},
                    {"$set": doc},
                    upsert=True,
                )
            except Exception:
                logger.warning("Failed to cache deck %s", deck.name, exc_info=True)

    def get_decks(self, format: str) -> list[MetagameDeck]:
        """Return all cached decks for a format."""
        fmt = format.lower()
        if fmt in self._memory and self._memory[fmt]:
            return self._memory[fmt]
        if not self._is_configured():
            return []
        try:
            docs = list(self._col.find({"format": fmt}))
            decks = [MetagameDeck.from_mongo_doc(d) for d in docs]
            if decks:
                self._memory[fmt] = decks
            return decks
        except Exception:
            logger.warning("Failed to load cached decks for %s", format, exc_info=True)
            return []

    def get_random_deck(self, format: str) -> Optional[MetagameDeck]:
        """Return a random cached deck for a format."""
        decks = self.get_decks(format)
        if not decks:
            return None
        return random.choice(decks)

    def refresh(self, format: str, limit: int = 15) -> list[MetagameDeck]:
        """Fetch fresh decks from MTGGoldfish and cache them."""
        logger.info("Refreshing deck cache for %s...", format)
        deck_list = scrape_metagame_list(format, limit=limit)
        decks: list[MetagameDeck] = []
        seen_names: set[str] = set()
        for name, url in deck_list:
            try:
                cards, commander = scrape_deck_page(url)
                if not cards:
                    continue
                # Deduplicate by name
                clean_name = name.split("\n")[0].strip()
                if clean_name in seen_names:
                    continue
                seen_names.add(clean_name)
                decks.append(MetagameDeck(
                    name=clean_name,
                    format=format.lower(),
                    cards=cards,
                    commander=commander,
                ))
            except Exception:
                logger.warning("Failed to scrape deck %s", url, exc_info=True)
                continue
        if decks:
            self.save_decks(format, decks)
        logger.info("Cached %d decks for %s", len(decks), format)
        return decks


# Module-level singleton
_cache: Optional[DeckCache] = None


def get_deck_cache() -> DeckCache:
    global _cache
    if _cache is None:
        _cache = DeckCache()
    return _cache


def get_random_deck(format: str) -> Optional[MetagameDeck]:
    """High-level helper: get a random deck, scraping if needed."""
    cache = get_deck_cache()
    deck = cache.get_random_deck(format)
    if deck is None:
        try:
            decks = cache.refresh(format)
            deck = random.choice(decks) if decks else None
        except Exception:
            logger.exception("Failed to fetch random deck for %s", format)
    return deck


def get_decks_for_format(format: str) -> list[MetagameDeck]:
    """High-level helper: list all cached decks for a format."""
    cache = get_deck_cache()
    decks = cache.get_decks(format)
    if not decks:
        try:
            decks = cache.refresh(format)
        except Exception:
            logger.exception("Failed to list decks for %s", format)
    return decks


def get_named_deck(format: str, name: str) -> Optional[MetagameDeck]:
    """Return a specific cached deck by format and name."""
    cache = get_deck_cache()
    decks = cache.get_decks(format)
    for d in decks:
        if d.name == name:
            return d
    return None

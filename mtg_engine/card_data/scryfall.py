import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

from mtg_engine.models.game import Card, CardFace

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent / "cache.db"


class ScryfallClient:
    """Fetches card data from Scryfall API with local SQLite cache. REQ-C04"""

    BASE_URL = "https://api.scryfall.com"
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests per Scryfall guidelines

    def __init__(self, db_path: Path | str = _DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    scryfall_id TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    data_json   TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name)")
            conn.commit()

    # --- Public API ---

    def get_card(self, name: str) -> Card:
        """Fetch card by exact name; uses cache on second call. REQ-C01"""
        cached = self._cache_get_by_name(name)
        if cached:
            return self._build_card(cached)
        raw = self._api_get(f"/cards/named", params={"exact": name})
        self._cache_put(raw)
        return self._build_card(raw)

    def get_card_by_id(self, scryfall_id: str) -> Card:
        """Fetch card by Scryfall UUID; uses cache on second call."""
        cached = self._cache_get_by_id(scryfall_id)
        if cached:
            return self._build_card(cached)
        raw = self._api_get(f"/cards/{scryfall_id}")
        self._cache_put(raw)
        return self._build_card(raw)

    # --- Cache helpers ---

    def _cache_get_by_name(self, name: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data_json FROM cards WHERE name = ?", (name,)
            ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def _cache_get_by_id(self, scryfall_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data_json FROM cards WHERE scryfall_id = ?", (scryfall_id,)
            ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def _cache_put(self, raw: dict) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cards (scryfall_id, name, data_json) VALUES (?, ?, ?)",
                (raw["id"], raw["name"], json.dumps(raw)),
            )
            conn.commit()

    # --- Scryfall API ---

    def _api_get(self, path: str, params: dict | None = None) -> dict:
        time.sleep(self.RATE_LIMIT_DELAY)
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    # --- Card builder ---

    def _build_card(self, raw: dict) -> Card:
        """Map Scryfall JSON → Card model. REQ-C05 (DFC, split, adventure, MDFC)"""
        faces: Optional[list[CardFace]] = None
        if "card_faces" in raw:
            faces = [
                CardFace(
                    name=f.get("name", ""),
                    mana_cost=f.get("mana_cost"),
                    type_line=f.get("type_line", ""),
                    oracle_text=f.get("oracle_text"),
                    power=f.get("power"),
                    toughness=f.get("toughness"),
                    loyalty=f.get("loyalty"),
                    colors=f.get("colors", []),
                )
                for f in raw["card_faces"]
            ]
        return Card(
            id=str(uuid.uuid4()),  # unique instance ID
            scryfall_id=raw.get("id"),
            name=raw.get("name", ""),
            mana_cost=raw.get("mana_cost"),
            type_line=raw.get("type_line", ""),
            oracle_text=raw.get("oracle_text"),
            power=raw.get("power"),
            toughness=raw.get("toughness"),
            loyalty=raw.get("loyalty"),
            colors=raw.get("colors", []),
            keywords=[k.lower() for k in raw.get("keywords", [])],
            faces=faces,
            cmc=float(raw.get("cmc", 0.0)),
        )

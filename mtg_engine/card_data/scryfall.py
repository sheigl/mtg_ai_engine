import json
import logging
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

from mtg_engine.models.game import Card, CardFace


# Valid MTG colors for filtering
VALID_COLORS = {"W", "U", "B", "R", "G", "C"}

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent / "cache.db"
_MONGO_URL = os.environ.get("MONGODB_URL", "mongodb://root:whatever@sheigl-ms-7a38.tailc63ae8.ts.net")


class ScryfallClient:
    """Fetches card data from Scryfall API with local SQLite cache and MongoDB bulk store. REQ-C04"""

    BASE_URL = "https://api.scryfall.com"
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests per Scryfall guidelines

    def __init__(self, db_path: Path | str = _DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._mongo_col = None
        try:
            import pymongo
            mc = pymongo.MongoClient(_MONGO_URL, serverSelectionTimeoutMS=3000)
            col = mc["scryfall"]["oracle_cards"]
            col.find_one({})  # validate connection
            col.create_index("name", background=True)
            self._mongo_col = col
        except Exception as exc:
            logger.debug("MongoDB card store unavailable: %s", exc)

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

    @staticmethod
    def _normalize_mongo(doc: dict) -> dict:
        """MongoDB oracle_cards uses 'card_id' where Scryfall API uses 'id'."""
        if "id" not in doc and "card_id" in doc:
            doc = {**doc, "id": doc["card_id"]}
        doc.pop("_id", None)
        return doc

    def preload(self, names: list[str]) -> None:
        """Batch-fetch uncached cards using /cards/collection (up to 75 per request).

        Calling this before a loop of get_card() turns N API calls into ceil(N/75).
        Cards already in cache are skipped. Fuzzy-matched names that don't come back
        under the same canonical name are silently left for individual get_card fallback.
        """
        unique = list(dict.fromkeys(names))
        uncached = [n for n in unique if not self._cache_get_by_name(n)]
        if not uncached:
            return

        # 1. Try MongoDB bulk lookup first (no rate limits, local network)
        still_uncached = list(uncached)
        if self._mongo_col is not None:
            try:
                docs = list(self._mongo_col.find({"name": {"$in": uncached}}))
                found = set()
                for doc in docs:
                    raw = self._normalize_mongo(doc)
                    self._cache_put(raw)
                    found.add(raw["name"])
                still_uncached = [n for n in uncached if n not in found]
                if found:
                    logger.debug("Preloaded %d/%d cards from MongoDB", len(found), len(uncached))
            except Exception as exc:
                logger.warning("MongoDB bulk preload failed: %s", exc)

        if not still_uncached:
            return

        # 2. Fall back to Scryfall /cards/collection for anything MongoDB didn't have
        for i in range(0, len(still_uncached), 75):
            batch = still_uncached[i:i + 75]
            time.sleep(self.RATE_LIMIT_DELAY)
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{self.BASE_URL}/cards/collection",
                        json={"identifiers": [{"name": n} for n in batch]},
                    )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2))
                    logger.warning("Scryfall 429 on collection batch; sleeping %ds", retry_after)
                    time.sleep(retry_after)
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.post(
                            f"{self.BASE_URL}/cards/collection",
                            json={"identifiers": [{"name": n} for n in batch]},
                        )
                resp.raise_for_status()
                for raw in resp.json().get("data", []):
                    self._cache_put(raw)
            except Exception as exc:
                logger.warning("Scryfall collection batch failed (will fall back to individual lookups): %s", exc)

    def get_card(self, name: str) -> Card:
        """Fetch card by exact name; uses SQLite cache, then MongoDB, then Scryfall API."""
        cached = self._cache_get_by_name(name)
        if cached:
            return self._build_card(cached)
        if self._mongo_col is not None:
            try:
                doc = self._mongo_col.find_one({"name": name})
                if doc:
                    raw = self._normalize_mongo(doc)
                    self._cache_put(raw)
                    return self._build_card(raw)
            except Exception as exc:
                logger.warning("MongoDB lookup failed for %r: %s", name, exc)
        raw = self._api_get("/cards/named", params={"exact": name})
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

    def search_cards(
        self,
        q: Optional[str] = None,
        type_line: Optional[str] = None,
        colors: Optional[list[str]] = None,
        cmc_min: Optional[float] = None,
        cmc_max: Optional[float] = None,
        mana_cost: Optional[str] = None,
        keyword: Optional[str] = None,
        rarity: Optional[str] = None,
        set_code: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> tuple[list[Card], int]:
        """Search cached cards by multiple filters. Returns (cards, total_count).

        All filters combine with AND logic. Operates entirely on the local SQLite cache.
        """
        if page < 1:
            raise ValueError("page must be >= 1")
        if per_page < 1 or per_page > 100:
            raise ValueError("per_page must be between 1 and 100")
        if sort_by not in ("name", "cmc"):
            raise ValueError(f"sort_by must be 'name' or 'cmc', got '{sort_by}'")
        if sort_order not in ("asc", "desc"):
            raise ValueError(f"sort_order must be 'asc' or 'desc', got '{sort_order}'")

        # Validate colors
        if colors:
            for c in colors:
                if c.upper() not in VALID_COLORS:
                    raise ValueError(f"Invalid color '{c}'; valid colors are {sorted(VALID_COLORS)}")
            colors = [c.upper() for c in colors]

        conditions: list[str] = []
        params: list = []

        # Free-text search (name + oracle_text)
        if q:
            conditions.append(
                "(LOWER(name) LIKE '%' || LOWER(?) || '%' "
                "OR LOWER(COALESCE(json_extract(data_json, '$.oracle_text'), '')) LIKE '%' || LOWER(?) || '%')"
            )
            params.extend([q, q])

        # Type line substring match
        if type_line:
            conditions.append("json_extract(data_json, '$.type_line') LIKE ?")
            params.append(f"%{type_line}%")

        # Colors — card must contain ALL specified colors (AND logic)
        if colors:
            for c in colors:
                conditions.append("json_extract(data_json, '$.colors') LIKE ?")
                params.append(f'%"{c}"%')

        # CMC range
        if cmc_min is not None:
            conditions.append("CAST(json_extract(data_json, '$.cmc') AS REAL) >= ?")
            params.append(cmc_min)
        if cmc_max is not None:
            conditions.append("CAST(json_extract(data_json, '$.cmc') AS REAL) <= ?")
            params.append(cmc_max)

        # Exact mana cost match
        if mana_cost:
            conditions.append("json_extract(data_json, '$.mana_cost') = ?")
            params.append(mana_cost)

        # Keyword — case-insensitive quoted keyword in JSON array
        if keyword:
            conditions.append("LOWER(json_extract(data_json, '$.keywords')) LIKE ?")
            params.append(f'%"{keyword.lower()}"%')

        # Rarity (case-insensitive)
        if rarity:
            conditions.append("LOWER(json_extract(data_json, '$.rarity')) = LOWER(?)")
            params.append(rarity)

        # Set code
        if set_code:
            conditions.append("json_extract(data_json, '$.set') = ?")
            params.append(set_code)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Sort clause
        dir_ = "ASC" if sort_order == "asc" else "DESC"
        if sort_by == "cmc":
            order_clause = f"ORDER BY CAST(json_extract(data_json, '$.cmc') AS REAL) {dir_}, name ASC"
        else:
            order_clause = f"ORDER BY name {dir_}"

        offset = (page - 1) * per_page

        with sqlite3.connect(self.db_path) as conn:
            # COUNT query for total
            count_sql = f"SELECT COUNT(*) FROM cards {where_clause}"
            total = conn.execute(count_sql, params).fetchone()[0]

            # SELECT query for page results
            select_sql = (
                f"SELECT data_json FROM cards {where_clause} "
                f"{order_clause} LIMIT ? OFFSET ?"
            )
            rows = conn.execute(select_sql, params + [per_page, offset]).fetchall()

        cards: list[Card] = []
        for row in rows:
            raw = json.loads(row[0])
            cards.append(self._build_search_card(raw))

        return cards, total

    def _build_search_card(self, raw: dict) -> Card:
        """Map cached Scryfall JSON to a Card model for search results."""
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
            color_identity=raw.get("color_identity", []),
            keywords=[k.lower() for k in raw.get("keywords", [])],
            faces=faces,
            cmc=float(raw.get("cmc", 0.0)),
            rarity=raw.get("rarity"),
            set_code=raw.get("set"),
        )

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
        for attempt in range(4):
            time.sleep(self.RATE_LIMIT_DELAY if attempt == 0 else min(2 ** attempt, 16))
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{self.BASE_URL}{path}", params=params)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2))
                logger.warning("Scryfall 429; sleeping %ds (attempt %d/4)", retry_after, attempt + 1)
                time.sleep(retry_after)
                continue
            if resp.status_code == 404:
                name = (params or {}).get("exact") or (params or {}).get("fuzzy") or path
                raise ValueError(f"Card not found: '{name}'")
            resp.raise_for_status()
            return resp.json()
        raise ValueError(f"Scryfall rate-limited after 4 attempts: {path}")

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
            color_identity=raw.get("color_identity", []),
            keywords=[k.lower() for k in raw.get("keywords", [])],
            faces=faces,
            cmc=float(raw.get("cmc", 0.0)),
        )

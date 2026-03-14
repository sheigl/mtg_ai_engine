import sqlite3
import requests
from typing import Optional, List
from mtg_engine.models import Card

class ScryfallClient:
    def __init__(self, db_path: str = "card_data/cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS cards (
                scryfall_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                mana_cost TEXT,
                type_line TEXT,
                oracle_text TEXT,
                power TEXT,
                toughness TEXT,
                loyalty TEXT,
                colors TEXT,
                keywords TEXT,
                faces TEXT
            )""")
            conn.commit()

    def get_card(self, name: str) -> Optional[Card]:
        card = self._get_from_cache(name)
        if card:
            return card

        # Fallback to API call if not in cache
        card_data = self._fetch_from_api(name)
        if card_data:
            self._save_to_cache(card_data)
            return self._card_from_data(card_data)
        return None

    def get_card_by_id(self, scryfall_id: str) -> Optional[Card]:
        card = self._get_from_cache_by_id(scryfall_id)
        if card:
            return card

        # Fallback to API call if not in cache
        card_data = self._fetch_from_api_by_id(scryfall_id)
        if card_data:
            self._save_to_cache(card_data)
            return self._card_from_data(card_data)
        return None

    def _get_from_cache(self, name: str) -> Optional[Card]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cards WHERE name = ?", (name,))
            rows = cursor.fetchall()
            if rows:
                return self._card_from_data(rows[0])
        return None

    def _get_from_cache_by_id(self, scryfall_id: str) -> Optional[Card]:
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cards WHERE scryfall_id = ?", (scryfall_id,))
            row = cursor.fetchone()
            if row:
                return self._card_from_data(row)
        return None

    def _fetch_from_api(self, name: str) -> Optional[dict]:
        try:
            response = requests.get(f"https://api.scryfall.com/cards/named?exact={name}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def _fetch_from_api_by_id(self, scryfall_id: str) -> Optional[dict]:
        try:
            response = requests.get(f"https://api.scryfall.com/cards/{scryfall_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def _save_to_cache(self, card_data: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT OR REPLACE INTO cards (
                scryfall_id, name, mana_cost, type_line, oracle_text,
                power, toughness, loyalty, colors, keywords, faces
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    card_data.get('id'),
                    card_data.get('name'),
                    card_data.get('mana_cost'),
                    card_data.get('type_line'),
                    card_data.get('oracle_text'),
                    card_data.get('power'),
                    card_data.get('toughness'),
                    card_data.get('loyalty'),
                    ','.join(card_data.get('colors', [])),
                    ','.join(card_data.get('keywords', [])),
                    card_data.get('card_faces') and json.dumps(card_data['card_faces']) or None
                )
            )
            conn.commit()

    def _card_from_data(self, card_data: dict) -> Card:
        return Card(
            id=card_data.get('id'),
            name=card_data.get('name'),
            mana_cost=card_data.get('mana_cost'),
            type_line=card_data.get('type_line'),
            oracle_text=card_data.get('oracle_text'),
            power=card_data.get('power'),
            toughness=card_data.get('toughness'),
            loyalty=card_data.get('loyalty'),
            colors=card_data.get('colors', []),
            keywords=card_data.get('keywords', []),
            faces=card_data.get('card_faces')
        )
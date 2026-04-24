import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_MONGO_URL = os.environ.get("MONGODB_URL", "")
_MONGO_DB = os.environ.get("MONGODB_DATABASE", "mtg_training")


class GameStateStore:
    """Persists game state to MongoDB for crash recovery and resume."""

    def __init__(self) -> None:
        self._col = None
        try:
            import pymongo
            url = _MONGO_URL
            if not url.strip():
                url = "mongodb://root:whatever@sheigl-ms-7a38.tailc63ae8.ts.net"
            mc = pymongo.MongoClient(url, serverSelectionTimeoutMS=3000)
            db_name = _MONGO_DB
            col = mc[db_name]["game_states"]
            col.find_one({})
            col.create_index("game_id", unique=True)
            col.create_index("is_complete")
            self._col = col
            logger.info("GameStateStore: MongoDB connected")
        except Exception as exc:
            logger.warning("GameStateStore: MongoDB unavailable, persistence disabled: %s", exc)

    def _is_configured(self) -> bool:
        return self._col is not None

    def upsert(self, game_id: str, state_dict: dict, series_config: dict | None = None, is_complete: bool = False) -> None:
        if not self._is_configured():
            return
        try:
            doc = {
                "game_id": game_id,
                "state": state_dict,
                "series_config": series_config,
                "is_complete": is_complete,
                "updated_at": datetime.now(timezone.utc),
            }
            self._col.update_one(
                {"game_id": game_id},
                {"$set": doc},
                upsert=True,
            )
        except Exception:
            logger.warning("GameStateStore: failed to upsert %s", game_id, exc_info=True)

    def load(self, game_id: str) -> Optional[dict]:
        if not self._is_configured():
            return None
        try:
            doc = self._col.find_one({"game_id": game_id})
            if doc:
                return doc
            return None
        except Exception:
            logger.warning("GameStateStore: failed to load %s", game_id, exc_info=True)
            return None

    def load_all_active(self) -> list[dict]:
        if not self._is_configured():
            return []
        try:
            return list(self._col.find({"is_complete": False}))
        except Exception:
            logger.warning("GameStateStore: failed to load active games", exc_info=True)
            return []

    def delete(self, game_id: str) -> None:
        if not self._is_configured():
            return
        try:
            self._col.delete_one({"game_id": game_id})
        except Exception:
            logger.warning("GameStateStore: failed to delete %s", game_id, exc_info=True)

    def mark_complete(self, game_id: str) -> None:
        if not self._is_configured():
            return
        try:
            self._col.update_one(
                {"game_id": game_id},
                {"$set": {"is_complete": True, "updated_at": datetime.now(timezone.utc)}},
            )
        except Exception:
            logger.warning("GameStateStore: failed to mark complete %s", game_id, exc_info=True)


_store: Optional["GameStateStore"] = None


def get_game_state_store() -> GameStateStore:
    global _store
    if _store is None:
        _store = GameStateStore()
    return _store
"""
MongoDB client singleton for game data persistence. Feature 025.
All functions return None when MONGODB_URL is not set — MongoDB is optional.
"""
import logging
import os

logger = logging.getLogger(__name__)

_client = None
_collection = None
_decisions_collection = None
_rules_qa_collection = None
_transcript_collection = None
_initialized = False
_main_loop = None


def set_main_loop(loop) -> None:
    """Store the uvicorn event loop so sync threads can schedule async tasks."""
    global _main_loop
    _main_loop = loop


def get_main_loop():
    """Return the stored event loop, or None if not yet set."""
    return _main_loop


def _init() -> None:
    global _client, _collection, _decisions_collection, _rules_qa_collection, _transcript_collection, _initialized
    if _initialized:
        return
    _initialized = True

    url = os.environ.get("MONGODB_URL", "mongodb://root:whatever@sheigl-ms-7a38.tailc63ae8.ts.net").strip()

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        db_name = os.environ.get("MONGODB_DATABASE", "").strip()
        collection_name = os.environ.get("MONGODB_COLLECTION", "games").strip() or "games"

        # Parse db name from URL path if not overridden
        if not db_name:
            from urllib.parse import urlparse
            parsed_path = urlparse(url).path.strip("/")
            db_name = parsed_path if parsed_path else "mtg_training"

        _client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        _collection = _client[db_name][collection_name]
        _decisions_collection = _client[db_name]["decisions"]
        _rules_qa_collection = _client[db_name]["rules_qa"]
        _transcript_collection = _client[db_name]["transcript"]
        logger.info("MongoDB configured: %s / %s / %s", url, db_name, collection_name)
    except Exception:
        logger.exception("Failed to initialize MongoDB client")
        _client = None
        _collection = None
        _decisions_collection = None
        _rules_qa_collection = None
        _transcript_collection = None


def is_configured() -> bool:
    """Return True if MONGODB_URL is set and client initialized successfully."""
    _init()
    return _collection is not None


def get_games_collection():
    """Return the games AsyncIOMotorCollection, or None if not configured."""
    _init()
    return _collection


def get_decisions_collection():
    """Return the decisions AsyncIOMotorCollection, or None if not configured."""
    _init()
    return _decisions_collection


def get_rules_qa_collection():
    """Return the rules_qa AsyncIOMotorCollection, or None if not configured."""
    _init()
    return _rules_qa_collection


def get_transcript_collection():
    """Return the transcript AsyncIOMotorCollection, or None if not configured."""
    _init()
    return _transcript_collection


async def ensure_indexes() -> None:
    """Create all indexes for the normalized collections."""
    import pymongo
    try:
        col = get_decisions_collection()
        if col is not None:
            await col.create_index([("game_id", pymongo.ASCENDING), ("sequence_number", pymongo.ASCENDING)], background=True)
            await col.create_index([("game_id", pymongo.ASCENDING), ("active_player", pymongo.ASCENDING)], background=True)
            await col.create_index([("outcome_context.active_player_won", pymongo.ASCENDING)], background=True)
            await col.create_index([("observer_evaluation.rating", pymongo.ASCENDING)], background=True)

        col = get_rules_qa_collection()
        if col is not None:
            await col.create_index([("game_id", pymongo.ASCENDING), ("decision_id", pymongo.ASCENDING)], background=True)

        col = get_transcript_collection()
        if col is not None:
            await col.create_index([("game_id", pymongo.ASCENDING), ("sequence_number", pymongo.ASCENDING)], background=True)

        logger.info("MongoDB: normalized collection indexes created/verified")
    except Exception:
        logger.warning("MongoDB: failed to create normalized indexes", exc_info=True)


def get_client():
    """Return the AsyncIOMotorClient, or None if not configured."""
    _init()
    return _client

"""Async CRUD operations for player default settings. Feature 028.

All functions return None when MongoDB is not configured.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mtg_engine.persistence.mongo_client import get_player_defaults_collection
from mtg_engine.models.player_defaults import (
    VALID_PLAYER_TYPES,
    validate_settings_for_type,
    merge_with_defaults,
)


async def get_defaults(player_type: str) -> dict[str, Any] | None:
    """Retrieve saved default settings for a player type.

    Returns None if no defaults exist or MongoDB is not configured.
    """
    collection = get_player_defaults_collection()
    if collection is None:
        return None
    doc = await collection.find_one({"_id": player_type})
    if doc is None:
        return None
    return {
        "player_type": doc["player_type"],
        "settings": doc["settings"],
        "updated_at": doc["updated_at"],
    }


async def save_defaults(
    player_type: str,
    settings: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Create or replace default settings for a player type.

    Returns a tuple of (saved_document, created) where created is True if
    the document did not previously exist.

    Raises ValueError if player_type is invalid or settings do not conform.
    Raises RuntimeError if MongoDB is not configured.
    """
    collection = get_player_defaults_collection()
    if collection is None:
        raise RuntimeError("MongoDB not configured")

    validated = validate_settings_for_type(player_type, settings)
    now = datetime.now(timezone.utc)
    doc = {
        "_id": player_type,
        "player_type": player_type,
        "settings": validated,
        "updated_at": now,
    }
    result = await collection.replace_one(
        {"_id": player_type},
        doc,
        upsert=True,
    )
    created = result.upserted_id is not None
    return {
        "player_type": player_type,
        "settings": validated,
        "updated_at": now,
    }, created


async def delete_defaults(player_type: str) -> bool:
    """Delete default settings for a player type.

    Returns True if a document was deleted, False if none existed.
    """
    collection = get_player_defaults_collection()
    if collection is None:
        return False
    result = await collection.delete_one({"_id": player_type})
    return result.deleted_count > 0


async def list_defaults() -> list[dict[str, Any]]:
    """List all configured default settings.

    Returns an empty list if none exist or MongoDB is not configured.
    """
    collection = get_player_defaults_collection()
    if collection is None:
        return []
    cursor = collection.find().sort("player_type", 1)
    results = []
    async for doc in cursor:
        results.append({
            "player_type": doc["player_type"],
            "settings": doc["settings"],
            "updated_at": doc["updated_at"],
        })
    return results


async def get_merged_player_settings(
    player_type: str,
    request_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch defaults from MongoDB and merge with request values.

    This is the core helper used by game creation endpoints. If defaults
    exist in MongoDB, they are merged with any explicit request values
    (request values take precedence).

    Args:
        player_type: The player type key (human, ai, heuristic).
        request_values: Explicit values from the game creation request.

    Returns:
        Merged settings dict (may be empty if no defaults and no request values).
    """
    defaults = await get_defaults(player_type)
    defaults_settings = defaults["settings"] if defaults else None
    return merge_with_defaults(player_type, request_values, defaults_settings)


def get_merged_player_settings_sync(
    player_type: str,
    request_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper around get_merged_player_settings for use in sync endpoints.

    Creates a new event loop if one is not already running. Falls back to
    request_values unchanged if MongoDB is not configured or an error occurs.
    """
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're in an async context — caller should use async version
        return merge_with_defaults(player_type, request_values, None)

    try:
        return asyncio.run(_merge_sync(player_type, request_values))
    except RuntimeError:
        return merge_with_defaults(player_type, request_values, None)


async def _merge_sync(
    player_type: str,
    request_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Internal coroutine for sync wrapper."""
    defaults = await get_defaults(player_type)
    defaults_settings = defaults["settings"] if defaults else None
    return merge_with_defaults(player_type, request_values, defaults_settings)

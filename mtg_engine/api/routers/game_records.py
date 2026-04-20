"""
Game records query endpoints. Feature 025/026.
Requires MongoDB to be configured; returns 503 otherwise.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["game-records"])


def _require_games_collection():
    from mtg_engine.persistence.mongo_client import is_configured, get_games_collection
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={"error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED"},
        )
    return get_games_collection()


def _require_decisions_collection():
    from mtg_engine.persistence.mongo_client import is_configured, get_decisions_collection
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={"error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED"},
        )
    return get_decisions_collection()


def _require_rules_qa_collection():
    from mtg_engine.persistence.mongo_client import is_configured, get_rules_qa_collection
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={"error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED"},
        )
    return get_rules_qa_collection()


def _require_transcript_collection():
    from mtg_engine.persistence.mongo_client import is_configured, get_transcript_collection
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail={"error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED"},
        )
    return get_transcript_collection()


def _strip_id(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ── Game list / metadata endpoints ────────────────────────────────────────────

@router.get("/games/records")
async def list_game_records(
    format: Optional[str] = Query(None),
    has_human_player: Optional[bool] = Query(None),
    is_complete: Optional[bool] = Query(True),
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=1000),
    fields: Optional[str] = Query(None),
) -> dict:
    """
    Query game records from MongoDB.

    - `fields`: comma-separated list of top-level fields to include.
      By default `_id` is excluded. All fields are metadata only (no embedded arrays).
    """
    collection = _require_games_collection()

    query: dict = {}
    if format is not None:
        query["format"] = format
    if has_human_player is not None:
        query["has_human_player"] = has_human_player
    if is_complete is not None:
        query["is_complete"] = is_complete
    if from_dt is not None or to_dt is not None:
        dt_filter: dict = {}
        if from_dt is not None:
            dt_filter["$gte"] = from_dt
        if to_dt is not None:
            dt_filter["$lte"] = to_dt
        query["created_at"] = dt_filter

    projection: dict | None = None
    if fields is not None:
        requested = {f.strip() for f in fields.split(",") if f.strip()}
        projection = {f: 1 for f in requested}
        projection["_id"] = 0
    else:
        projection = {"_id": 0}

    cursor = collection.find(query, projection).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"data": {"records": docs, "count": len(docs)}}


@router.get("/games/records/{game_id}")
async def get_game_record(game_id: str) -> dict:
    """Return the game metadata document for a specific game_id."""
    collection = _require_games_collection()
    doc = await collection.find_one({"_id": game_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game record not found", "error_code": "RECORD_NOT_FOUND"},
        )
    return {"data": doc}


# ── Decisions endpoints ───────────────────────────────────────────────────────

@router.get("/games/records/{game_id}/decisions")
async def get_game_decisions(
    game_id: str,
    active_player: Optional[str] = Query(None),
    won: Optional[bool] = Query(None),
    observer_rating: Optional[str] = Query(None),
) -> dict:
    """Return all decision documents for a game, optionally filtered."""
    collection = _require_decisions_collection()

    query: dict = {"game_id": game_id}
    if active_player is not None:
        query["active_player"] = active_player
    if won is not None:
        query["outcome_context.active_player_won"] = won
    if observer_rating is not None:
        query["observer_evaluation.rating"] = observer_rating

    cursor = collection.find(query, {"_id": 0}).sort("sequence_number", 1)
    docs = await cursor.to_list(length=10000)
    if not docs and active_player is None and won is None and observer_rating is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "No decisions found for game", "error_code": "DECISIONS_NOT_FOUND"},
        )
    return {"data": {"game_id": game_id, "decisions": docs, "count": len(docs)}}


@router.get("/games/decisions")
async def list_decisions(
    active_player: Optional[str] = Query(None),
    won: Optional[bool] = Query(None),
    observer_rating: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=10000),
) -> dict:
    """Return decisions across all games, optionally filtered."""
    collection = _require_decisions_collection()

    query: dict = {}
    if active_player is not None:
        query["active_player"] = active_player
    if won is not None:
        query["outcome_context.active_player_won"] = won
    if observer_rating is not None:
        query["observer_evaluation.rating"] = observer_rating

    cursor = collection.find(query, {"_id": 0}).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"data": {"decisions": docs, "count": len(docs)}}


# ── Rules Q&A endpoint ────────────────────────────────────────────────────────

@router.get("/games/records/{game_id}/rules-qa")
async def get_game_rules_qa(game_id: str) -> dict:
    """Return all rules Q&A entries for a game, sorted by decision_id."""
    collection = _require_rules_qa_collection()
    cursor = collection.find({"game_id": game_id}, {"_id": 0}).sort("decision_id", 1)
    docs = await cursor.to_list(length=10000)
    return {"data": {"game_id": game_id, "rules_qa": docs, "count": len(docs)}}


# ── Transcript endpoint ───────────────────────────────────────────────────────

@router.get("/games/records/{game_id}/transcript")
async def get_game_transcript(game_id: str) -> dict:
    """Return all transcript entries for a game, sorted by sequence_number."""
    collection = _require_transcript_collection()
    cursor = collection.find({"game_id": game_id}, {"_id": 0}).sort("sequence_number", 1)
    docs = await cursor.to_list(length=100000)
    return {"data": {"game_id": game_id, "transcript": docs, "count": len(docs)}}

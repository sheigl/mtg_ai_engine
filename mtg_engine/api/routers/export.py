"""Export endpoints. TASK-23. REQ-D01–REQ-D10."""
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import get_export_store, delete_export_store
from mtg_engine.export.outcome import build_outcome

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])


def _get_store(game_id: str):
    store = get_export_store(game_id)
    return store


@router.get("/{game_id}/snapshots")
def export_snapshots(game_id: str) -> PlainTextResponse:
    """GET /export/{game_id}/snapshots → JSONL of all snapshots."""
    store = _get_store(game_id)
    return PlainTextResponse(store.snapshots.to_jsonl(), media_type="application/x-ndjson")


@router.get("/{game_id}/transcript")
def export_transcript(game_id: str) -> dict:
    """GET /export/{game_id}/transcript → JSON array of transcript events."""
    store = _get_store(game_id)
    return {"data": store.transcript.to_json()}


@router.get("/{game_id}/rules-qa")
def export_rules_qa(game_id: str) -> dict:
    """GET /export/{game_id}/rules-qa → JSON array of Q&A pairs."""
    store = _get_store(game_id)
    return {"data": store.rules_qa.to_json()}


@router.get("/{game_id}/outcome")
def export_outcome(game_id: str) -> dict:
    """GET /export/{game_id}/outcome → single outcome JSON object."""
    mgr = get_manager()
    try:
        gs = mgr.get(game_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"})

    store = _get_store(game_id)
    outcome = build_outcome(
        gs,
        snapshot_count=len(store.snapshots.get_all()),
        transcript_length=len(store.transcript.get_all()),
    )
    return {"data": outcome.model_dump()}

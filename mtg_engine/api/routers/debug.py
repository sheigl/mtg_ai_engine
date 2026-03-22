"""
Debug log endpoints. Feature 011-observer-ai-commentary.
Prefix: /game  (same as game router; FastAPI merges them cleanly)
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import get_export_store
from mtg_engine.models.debug import DebugEntry, DebugEntryPatch

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/game", tags=["debug"])


def _get_recorder(game_id: str):
    """Return the DebugLogRecorder for a game, raising 404 if the game is unknown."""
    try:
        get_manager().get(game_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )
    return get_export_store(game_id).debug_log


# ── POST /game/{game_id}/debug/entry ────────────────────────────────────────

@router.post("/{game_id}/debug/entry")
async def create_debug_entry(game_id: str, entry: DebugEntry) -> dict:
    """Append a new debug entry (prompt or commentary) to a game's log."""
    recorder = _get_recorder(game_id)
    recorder.append_entry(entry)
    return {"data": {"entry_id": entry.entry_id}}


# ── PATCH /game/{game_id}/debug/entry/{entry_id} ─────────────────────────────

@router.patch("/{game_id}/debug/entry/{entry_id}")
async def patch_debug_entry(game_id: str, entry_id: str, patch: DebugEntryPatch) -> dict:
    """Append streaming tokens to an in-progress entry."""
    recorder = _get_recorder(game_id)
    updated = recorder.patch_entry(entry_id, patch.response_chunk, patch.is_complete)
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Entry not found", "error_code": "ENTRY_NOT_FOUND"},
        )
    return {"data": {"entry_id": entry_id, "is_complete": updated.is_complete}}


# ── GET /game/{game_id}/debug ─────────────────────────────────────────────────

@router.get("/{game_id}/debug")
def get_debug_log(game_id: str) -> dict:
    """Return the full debug log, sorted by timestamp."""
    recorder = _get_recorder(game_id)
    entries = sorted(recorder.get_all(), key=lambda e: e.timestamp)
    return {"data": {"game_id": game_id, "entries": [e.model_dump() for e in entries]}}


# ── GET /game/{game_id}/debug/stream (SSE) ────────────────────────────────────

@router.get("/{game_id}/debug/stream")
async def stream_debug_log(game_id: str) -> StreamingResponse:
    """
    Server-Sent Events stream for live debug panel.
    - Replays existing entries on connect (for late-joining clients).
    - Pushes new/patched entries as they arrive.
    - Sends :keepalive every 15s to prevent proxy timeouts.
    - Sends event: game_over when the game ends, then closes.
    """
    try:
        get_manager().get(game_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    recorder = get_export_store(game_id).debug_log
    queue: asyncio.Queue[DebugEntry] = asyncio.Queue()

    def _listener(entry: DebugEntry) -> None:
        queue.put_nowait(entry)

    recorder.register_listener(_listener)

    async def _event_generator():
        try:
            # Replay existing entries in timestamp order
            for entry in sorted(recorder.get_all(), key=lambda e: e.timestamp):
                yield f"data: {entry.model_dump_json()}\n\n"

            # Stream new entries
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {entry.model_dump_json()}\n\n"
                    # Check game-over after each entry
                    try:
                        gs = get_manager().get(game_id)
                        if gs.is_game_over:
                            yield f"event: game_over\ndata: {json.dumps({'game_id': game_id})}\n\n"
                            break
                    except KeyError:
                        yield f"event: game_over\ndata: {json.dumps({'game_id': game_id})}\n\n"
                        break
                except asyncio.TimeoutError:
                    yield ":keepalive\n\n"
                    # Also check game-over during keepalive
                    try:
                        gs = get_manager().get(game_id)
                        if gs.is_game_over:
                            yield f"event: game_over\ndata: {json.dumps({'game_id': game_id})}\n\n"
                            break
                    except KeyError:
                        yield f"event: game_over\ndata: {json.dumps({'game_id': game_id})}\n\n"
                        break
        finally:
            recorder.unregister_listener(_listener)

    return StreamingResponse(_event_generator(), media_type="text/event-stream")

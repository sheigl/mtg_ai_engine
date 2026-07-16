"""Game Replay API endpoints. APP-03."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mtg_engine.export.store import get_export_store
from mtg_engine.export.replay_engine import (
    game_has_export_data,
    get_replay_info,
    paginate_events,
    step_to_event,
    build_timeline,
    reconstruct_board_state_at,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/replay", tags=["replay"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ReplayInfoResponse(BaseModel):
    """Response for GET /replay/{game_id}/info."""
    game_id: str
    total_events: int
    turns: int
    winner: Optional[str] = None
    loser: Optional[str] = None
    format: Optional[str] = "standard"


class EventWithBoardState(BaseModel):
    """Single event with reconstructed board state."""
    seq: int
    event_type: str
    description: str
    data: dict = Field(default_factory=dict)
    turn: int = 0
    phase: Optional[str] = None
    step: Optional[str] = None
    board_state: dict = Field(default_factory=dict)


class PaginatedEventsResponse(BaseModel):
    """Response for GET /replay/{game_id}/events."""
    events: list[EventWithBoardState]
    total_count: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class StepRequest(BaseModel):
    """Request body for POST /replay/{game_id}/step."""
    direction: str = Field(..., description="Either 'forward' or 'backward'")
    from_event_seq: int = Field(default=0, description="Current sequence number (0 = before game starts)")


class StepResponse(BaseModel):
    """Response for POST /replay/{game_id}/step."""
    event: EventWithBoardState
    direction: str
    from_seq: int
    to_seq: int


class TimelinePhaseSegment(BaseModel):
    """One phase/step segment in the timeline."""
    phase: str
    step: Optional[str] = None
    event_count: int
    first_event_seq: int
    last_event_seq: int


class TimelineTurn(BaseModel):
    """One turn entry in the timeline."""
    turn: int
    phases: list[TimelinePhaseSegment]


class TimelineResponse(BaseModel):
    """Response for GET /replay/{game_id}/timeline."""
    game_id: str
    total_events: int
    turns: list[TimelineTurn]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{game_id}/info")
def replay_info(game_id: str) -> dict:
    """GET /replay/{game_id}/info — Replay metadata. REQ-R01"""
    if not game_has_export_data(game_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    store = get_export_store(game_id)
    info = get_replay_info(store)
    return {"data": ReplayInfoResponse(**info).model_dump()}


@router.get("/{game_id}/events")
def replay_events(
    game_id: str,
    page: int = 1,
    per_page: int = 25,
) -> dict:
    """GET /replay/{game_id}/events — Paginated event list with board state. REQ-R02"""
    if not game_has_export_data(game_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    store = get_export_store(game_id)
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 25

    events_raw, total_count = paginate_events(store, page, per_page)

    has_next = page * per_page < total_count
    has_prev = page > 1

    # Attach board state to each event
    events_out = []
    for e in events_raw:
        seq = e["seq"]
        board_state = {}
        try:
            board_state = reconstruct_board_state_at(store, seq)
        except Exception:
            logger.warning("Failed to reconstruct board state at seq %d", seq, exc_info=True)

        events_out.append(EventWithBoardState(
            seq=seq,
            event_type=e.get("event_type", ""),
            description=e.get("description", ""),
            data=e.get("data", {}),
            turn=e.get("turn", 0),
            phase=e.get("phase"),
            step=e.get("step"),
            board_state=board_state,
        ))

    return {"data": PaginatedEventsResponse(
        events=events_out,
        total_count=total_count,
        page=page,
        per_page=per_page,
        has_next=has_next,
        has_prev=has_prev,
    ).model_dump()}


@router.post("/{game_id}/step")
def replay_step(game_id: str, req: StepRequest) -> dict:
    """POST /replay/{game_id}/step — Step forward/backward one event. REQ-R03"""
    if not game_has_export_data(game_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    store = get_export_store(game_id)
    if req.direction not in ("forward", "backward"):
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid direction: {req.direction}", "error_code": "INVALID_DIRECTION"},
        )

    result = step_to_event(store, req.direction, req.from_event_seq)

    if result is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Cannot step {req.direction} from seq {req.from_event_seq}",
                "error_code": "OUT_OF_BOUNDS",
            },
        )

    event_raw, board_state, from_seq, to_seq = result

    return {"data": StepResponse(
        event=EventWithBoardState(
            seq=event_raw["seq"],
            event_type=event_raw.get("event_type", ""),
            description=event_raw.get("description", ""),
            data=event_raw.get("data", {}),
            turn=event_raw.get("turn", 0),
            phase=event_raw.get("phase"),
            step=event_raw.get("step"),
            board_state=board_state,
        ),
        direction=req.direction,
        from_seq=from_seq,
        to_seq=to_seq,
    ).model_dump()}


@router.get("/{game_id}/timeline")
def replay_timeline(game_id: str) -> dict:
    """GET /replay/{game_id}/timeline — Condensed timeline grouped by turn/phase. REQ-R04"""
    if not game_has_export_data(game_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    store = get_export_store(game_id)
    timeline_raw = build_timeline(store)

    # Count total events from transcript
    entries = store.transcript.to_json()
    total_events = len(entries)

    # Convert to Pydantic models
    turns_out = []
    for turn_entry in timeline_raw:
        phases_out = []
        for seg in turn_entry["phases"]:
            phases_out.append(TimelinePhaseSegment(**seg))
        turns_out.append(TimelineTurn(
            turn=turn_entry["turn"],
            phases=phases_out,
        ))

    return {"data": TimelineResponse(
        game_id=game_id,
        total_events=total_events,
        turns=turns_out,
    ).model_dump()}

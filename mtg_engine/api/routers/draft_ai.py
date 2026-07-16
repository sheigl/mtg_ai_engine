"""
APP-05: Draft / Sealed Simulation — REST endpoints.

Endpoints:
  POST   /ai/draft/start        — start a new draft session
  GET    /ai/draft/{session_id}/state     — current draft state + pending pick info
  POST   /ai/draft/{session_id}/pick      — submit a card pick (human or bot)
  GET    /ai/draft/{session_id}/results   — final results after draft completes
  POST   /ai/sealed/start       — one-shot sealed pool simulation
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["draft-sealed"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class DraftStartRequest(BaseModel):
    """POST /ai/draft/start request body."""
    players: list[str] = Field(min_length=2, max_length=8)
    packs_per_player: int = Field(ge=1, le=8, default=3)
    set_code: str
    format_name: str = "modern"
    strategy: str = "midrange"
    human_player_name: Optional[str] = None
    seed: Optional[int] = None

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        allowed = {"aggro", "control", "midrange", "combo"}
        if v.lower() not in allowed:
            raise ValueError(f"Strategy must be one of {allowed}, got '{v}'")
        return v.lower()

    model_config = {"json_schema_extra": {
        "examples": [{
            "players": ["Alice", "Bob", "Charlie"],
            "packs_per_player": 3,
            "set_code": "MOM",
            "format_name": "modern",
            "strategy": "aggro",
            "human_player_name": "Alice",
        }]
    }}


class DraftPickResponse(BaseModel):
    """POST /ai/draft/{session_id}/pick response body."""
    session_id: str
    state: str
    round_number: int
    picks_this_round: int
    players: list[str]
    picked_card: Optional[str] = None
    current_picker: Optional[str] = None
    available_cards: list[str] = Field(default_factory=list)


class DraftStartResponse(BaseModel):
    """POST /ai/draft/start response body."""
    session_id: str
    state: str
    round_number: int
    picks_this_round: int
    players: list[str]
    current_picker: Optional[str] = None
    available_cards: list[str] = Field(default_factory=list)


class DraftPickRequest(BaseModel):
    """POST /ai/draft/{session_id}/pick request body."""
    card_name: str

    model_config = {"json_schema_extra": {
        "examples": [{
            "card_name": "Lightning Bolt",
        }]
    }}


class DraftStateResponse(BaseModel):
    """GET /ai/draft/{session_id}/state response body."""
    session_id: str
    state: str
    round_number: int
    picks_this_round: int
    total_picks: int
    players: list[dict]  # [{name, drafted_cards: [...], is_human}]
    current_picker: Optional[str] = None
    available_cards: list[str] = Field(default_factory=list)


class DraftResultsResponse(BaseModel):
    """GET /ai/draft/{session_id}/results response body."""
    session_id: str
    state: str
    player_decks: dict[str, dict]  # {name: {deck: [...], sideboard: [...]}}
    draft_stats: dict[str, dict]


class SealedStartRequest(BaseModel):
    """POST /ai/sealed/start request body."""
    players: list[str] = Field(min_length=1, max_length=8)
    set_code: str
    format_name: str = "modern"
    strategy: str = "midrange"
    seed: Optional[int] = None

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        allowed = {"aggro", "control", "midrange", "combo"}
        if v.lower() not in allowed:
            raise ValueError(f"Strategy must be one of {allowed}, got '{v}'")
        return v.lower()

    model_config = {"json_schema_extra": {
        "examples": [{
            "players": ["Alice"],
            "set_code": "MOM",
            "format_name": "modern",
        }]
    }}


class SealedPlayerResult(BaseModel):
    """Per-player sealed result."""
    name: str
    pool: list[str]
    deck: list[dict]  # [{name, quantity}]
    sideboard: list[dict]


class SealedStartResponse(BaseModel):
    """POST /ai/sealed/start response body."""
    players: list[SealedPlayerResult]
    set_code: str
    format_name: str


# ---------------------------------------------------------------------------
# Helper: build current picker info from session
# ---------------------------------------------------------------------------

def _build_picker_info(session) -> tuple[str | None, list[str]]:
    """Return (current_picker_name, available_cards) or (None, [])."""
    from mtg_engine.ai.draft import _get_current_pick_info

    pick_info = _get_current_pick_info(session)
    if pick_info is None:
        return None, []
    return pick_info.player_name, pick_info.available_cards


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/draft/start", response_model=DraftStartResponse)
async def start_draft(req: DraftStartRequest) -> dict:
    """
    POST /ai/draft/start — create a new draft session.

    Generates initial packs and returns the first pick info if it's a bot's turn,
    or waits for human input.
    """
    from mtg_engine.ai.draft import (
        _clear_sessions,
        _get_current_pick_info,
        _resolve_bot_picks,
        _start_draft_session,
    )

    try:
        session = _start_draft_session(
            players=req.players,
            packs_per_player=req.packs_per_player,
            set_code=req.set_code,
            format_name=req.format_name,
            strategy=req.strategy,
            human_player_name=req.human_player_name,
            seed=req.seed,
        )

        # Auto-resolve bot picks until a human needs to pick or draft completes
        session = _resolve_bot_picks(session)

        picker_name, available = None, []
        if session.state == "drafting":
            pick_info = _get_current_pick_info(session)
            if pick_info:
                picker_name = pick_info.player_name
                available = pick_info.available_cards

        return {
            "session_id": session.session_id,
            "state": session.state,
            "round_number": session.current_round,
            "picks_this_round": session.picks_this_round + 1 if session.state == "drafting" else len(session.players),
            "players": [p.player_name for p in session.players],
            "current_picker": picker_name,
            "available_cards": available,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/draft/{session_id}/state", response_model=DraftStateResponse)
async def get_draft_state(session_id: str) -> dict:
    """
    GET /ai/draft/{session_id}/state — current draft state and pending pick info.

    Returns the full session state including drafted cards per player,
    round number, and available cards for the current picker.
    """
    from mtg_engine.ai.draft import _get_current_pick_info, _resolve_bot_picks, _get_session

    try:
        session = _get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Auto-resolve any pending bot picks first
    session = _resolve_bot_picks(session)

    picker_name, available = None, []
    if session.state == "drafting":
        pick_info = _get_current_pick_info(session)
        if pick_info:
            picker_name = pick_info.player_name
            available = pick_info.available_cards

    return {
        "session_id": session.session_id,
        "state": session.state,
        "round_number": session.current_round,
        "picks_this_round": session.picks_this_round + 1 if session.state == "drafting" else len(session.players),
        "total_picks": session.total_picks,
        "players": [
            {
                "name": p.player_name,
                "is_human": p.is_human,
                "drafted_cards": [c.name for c in p.drafted_cards],
            }
            for p in session.players
        ],
        "current_picker": picker_name,
        "available_cards": available,
    }


@router.post("/draft/{session_id}/pick", response_model=DraftPickResponse)
async def make_draft_pick(session_id: str, req: DraftPickRequest) -> dict:
    """
    POST /ai/draft/{session_id}/pick — submit a card pick.

    The client specifies the card name to draft from the current pack.
    After processing, returns updated state and next picker info.
    """
    from mtg_engine.ai.draft import (
        _get_current_pick_info,
        _process_pick,
        _resolve_bot_picks,
        _get_session,
    )

    try:
        session = _get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if session.state != "drafting":
        raise HTTPException(
            status_code=400,
            detail=f"Draft is not in 'drafting' state (current: {session.state})",
        )

    # Determine who the current picker is — must be a human player
    pick_info = _get_current_pick_info(session)
    if pick_info is None:
        raise HTTPException(status_code=400, detail="No pending pick")

    player_name = pick_info.player_name
    ps = next((p for p in session.players if p.player_name == player_name), None)
    if ps is None or not ps.is_human:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit picks for bot player '{player_name}'. Use GET /state to check.",
        )

    try:
        session, picked_card = _process_pick(session_id, player_name, req.card_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Auto-resolve any pending bot picks after human pick
    session = _resolve_bot_picks(session)

    picker_name, available = None, []
    if session.state == "drafting":
        pi = _get_current_pick_info(session)
        if pi:
            picker_name = pi.player_name
            available = pi.available_cards

    return {
        "session_id": session.session_id,
        "state": session.state,
        "round_number": session.current_round,
        "picks_this_round": session.picks_this_round + 1 if session.state == "drafting" else len(session.players),
        "players": [p.player_name for p in session.players],
        "picked_card": picked_card.name if picked_card is not None else None,
        "current_picker": picker_name,
        "available_cards": available,
    }


@router.get("/draft/{session_id}/results", response_model=DraftResultsResponse)
async def get_draft_results(session_id: str) -> dict:
    """
    GET /ai/draft/{session_id}/results — final draft results.

    Returns constructed decks and sideboards for each player, plus draft stats.
    Only available after the draft is completed.
    """
    from mtg_engine.ai.draft import _get_session

    try:
        session = _get_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if session.state != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Draft not yet completed (current state: {session.state})",
        )

    results = session.results
    if results is None:
        raise HTTPException(status_code=500, detail="Results data missing")

    return {
        "session_id": session.session_id,
        "state": session.state,
        "player_decks": results.player_decks,
        "draft_stats": results.draft_stats,
    }


@router.post("/sealed/start", response_model=SealedStartResponse)
async def start_sealed(req: SealedStartRequest) -> dict:
    """
    POST /ai/sealed/start — one-shot sealed pool simulation.

    Each player gets a 15-card pack (sealed pool), then decks are built
    automatically via APP-02's build_deck(). Returns immediate results.
    """
    from mtg_engine.ai.draft import _start_sealed_session

    try:
        result = _start_sealed_session(
            players=req.players,
            set_code=req.set_code,
            format_name=req.format_name,
            strategy=req.strategy,
            seed=req.seed,
        )

        return {
            "players": [SealedPlayerResult(**p) for p in result["players"]],
            "set_code": result["set_code"],
            "format_name": result["format_name"],
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Cleanup endpoint (for testing)
# ---------------------------------------------------------------------------

@router.post("/draft/cleanup")
async def cleanup_draft_sessions() -> dict:
    """Clear all draft sessions. Intended for test teardown."""
    from mtg_engine.ai.draft import _clear_sessions, _draft_sessions

    count = len(_draft_sessions)
    _clear_sessions()
    return {"cleared": count}

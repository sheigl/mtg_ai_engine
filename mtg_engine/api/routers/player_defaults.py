"""CRUD REST endpoints for player default settings. Feature 028.

Endpoints:
    GET    /player-defaults          — list all defaults
    GET    /player-defaults/{type}   — get defaults for a type
    PUT    /player-defaults/{type}   — create or replace defaults
    DELETE /player-defaults/{type}   — delete defaults for a type
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from mtg_engine.models.player_defaults import VALID_PLAYER_TYPES
from mtg_engine.persistence.mongo_client import is_configured as mongo_is_configured
from mtg_engine.persistence.player_defaults import (
    get_defaults,
    save_defaults,
    delete_defaults,
    list_defaults,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/player-defaults", tags=["player-defaults"])


def _check_mongo() -> None:
    """Raise 503 if MongoDB is not configured."""
    if not mongo_is_configured():
        raise HTTPException(
            status_code=503,
            detail={"error": "MongoDB not configured", "error_code": "MONGODB_NOT_CONFIGURED"},
        )


def _check_player_type(player_type: str) -> None:
    """Raise 422 if player_type is not valid."""
    if player_type not in VALID_PLAYER_TYPES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": f"player_type must be one of {VALID_PLAYER_TYPES}",
                "error_code": "INVALID_PLAYER_TYPE",
            },
        )


# ── GET /player-defaults ─────────────────────────────────────────────────────

@router.get("")
async def list_all_defaults() -> dict:
    """GET /player-defaults — list all configured default settings."""
    _check_mongo()
    defaults = await list_defaults()
    return {"data": {"defaults": defaults}}


# ── GET /player-defaults/{player_type} ───────────────────────────────────────

@router.get("/{player_type}")
async def get_default_by_type(player_type: str) -> dict:
    """GET /player-defaults/{player_type} — retrieve defaults for a type."""
    _check_player_type(player_type)
    _check_mongo()
    result = await get_defaults(player_type)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Default settings not found for player type '{player_type}'",
                "error_code": "DEFAULTS_NOT_FOUND",
            },
        )
    return {"data": result}


# ── PUT /player-defaults/{player_type} ───────────────────────────────────────

@router.put("/{player_type}")
async def save_default_by_type(player_type: str, body: dict) -> Response:
    """PUT /player-defaults/{player_type} — create or replace defaults.

    Returns 200 if updated or 201 if created (new document).
    """
    _check_player_type(player_type)
    if "settings" not in body:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Request body must include 'settings' field",
                "error_code": "INVALID_SETTINGS",
            },
        )
    settings = body["settings"]
    if not isinstance(settings, dict):
        raise HTTPException(
            status_code=422,
            detail={
                "error": f"Invalid settings for player type '{player_type}': settings must be an object",
                "error_code": "INVALID_SETTINGS",
            },
        )
    try:
        result, created = await save_defaults(player_type, settings)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": f"Invalid settings for player type '{player_type}': {e}",
                "error_code": "INVALID_SETTINGS",
            },
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": str(e), "error_code": "MONGODB_NOT_CONFIGURED"},
        )
    status_code = 201 if created else 200
    return JSONResponse(content={"data": result}, status_code=status_code)


# ── DELETE /player-defaults/{player_type} ────────────────────────────────────

@router.delete("/{player_type}", status_code=204)
async def delete_default_by_type(player_type: str) -> None:
    """DELETE /player-defaults/{player_type} — delete defaults for a type."""
    _check_player_type(player_type)
    _check_mongo()
    deleted = await delete_defaults(player_type)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Default settings not found for player type '{player_type}'",
                "error_code": "DEFAULTS_NOT_FOUND",
            },
        )

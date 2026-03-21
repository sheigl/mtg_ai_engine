"""
Deck import API endpoints.

REQ-U01: file selection → validation → preview → confirmation workflow
REQ-U02: Clear error messages for invalid deck formats
REQ-U03: Progress indicators handled client-side; server returns structured responses
REQ-D01: 400 on invalid deck format
REQ-S02: 403 on upload rejected
REQ-R01: 500 on internal rules engine error
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from mtg_engine.card_data.archidekt_parser import (
    parse_archidekt_json,
    parse_archidekt_text,
    parse_scryfall_txt,
)
from mtg_engine.card_data.deck_validator import (
    build_card_previews,
    validate_deck_format,
)
from mtg_engine.card_data.security import (
    check_rate_limit,
    sanitize_input,
    validate_file_upload,
)
from mtg_engine.models.deck_import import (
    DeckFormat,
    DeckImportRequest,
    DeckPreview,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deck", tags=["deck-import"])

# In-memory deck store with 24h TTL concept (simple dict; TTL not enforced in MVP)
_deck_store: dict[str, DeckPreview] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bad(msg: str, code: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": msg, "error_code": code})


def _detect_format(req: DeckImportRequest) -> DeckFormat:
    """Auto-detect format when not explicitly provided."""
    if req.format:
        return req.format
    if req.archidekt_url:
        return DeckFormat.ARCHIDEKT_JSON
    if req.file_name:
        name = req.file_name.lower()
        if name.endswith(".json"):
            return DeckFormat.ARCHIDEKT_JSON
        if name.endswith(".txt"):
            return DeckFormat.SCRYFALL_TXT
    return DeckFormat.ARCHIDEKT_TEXT


def _parse_deck(req: DeckImportRequest, fmt: DeckFormat) -> dict:
    """Parse deck data from request. Returns {"main": [...], "sideboard": [...]}."""
    if fmt == DeckFormat.ARCHIDEKT_JSON:
        if req.archidekt_url:
            return parse_archidekt_json(req.archidekt_url)
        if req.file_data is not None:
            import json
            try:
                data = json.loads(req.file_data)
                if "main" in data:
                    return data
                raise ValueError("JSON does not contain 'main' key")
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"Invalid Archidekt JSON: {e}") from e
        raise ValueError("ARCHIDEKT_JSON format requires archidekt_url or file_data")

    if fmt == DeckFormat.ARCHIDEKT_TEXT:
        if req.file_data is None:
            raise ValueError("ARCHIDEKT_TEXT format requires file_data")
        return parse_archidekt_text(req.file_data)

    if fmt == DeckFormat.SCRYFALL_TXT:
        if req.file_data is None:
            raise ValueError("SCRYFALL_TXT format requires file_data")
        return parse_scryfall_txt(req.file_data)

    raise ValueError(f"Unsupported format: {fmt}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/import")
async def import_deck(req: DeckImportRequest, request: Request) -> dict:
    """
    POST /deck/import — import deck from URL or file upload.

    REQ-U01: Step 1-3 of import workflow (parse → validate → preview)
    Returns DeckPreview with validation results.
    """
    ip = _client_ip(request)

    # REQ-S03: Rate limiting
    allowed, rate_msg = check_rate_limit(ip)
    if not allowed:
        raise _bad(rate_msg, "RATE_LIMIT_EXCEEDED", 429)

    # REQ-S01, REQ-S02: Security validation for file uploads
    if req.file_data is not None:
        content_type = "text/plain"
        if req.file_name and req.file_name.lower().endswith(".json"):
            content_type = "application/json"
        file_bytes = req.file_data.encode("utf-8")
        ok, reason = validate_file_upload(file_bytes, content_type)
        if not ok:
            raise _bad(reason, "FILE_UPLOAD_REJECTED", 403)

    # Sanitize optional deck name
    deck_name = sanitize_input(req.deck_name or "") or "Imported Deck"

    # Detect format and parse
    fmt = _detect_format(req)
    try:
        deck_data = _parse_deck(req, fmt)
    except ValueError as e:
        # REQ-D01: 400 for invalid deck format, REQ-U02: clear error message
        raise _bad(str(e), "INVALID_DECK_FORMAT", 400)
    except Exception as e:
        logger.exception("Unexpected error parsing deck")
        raise _bad(f"Internal error: {e}", "INTERNAL_ERROR", 500)

    # Validate deck structure
    is_valid, errors = validate_deck_format(deck_data)

    # Resolve cards and build previews
    try:
        main_previews, sb_previews, unresolved = build_card_previews(deck_data)
    except Exception as e:
        logger.exception("Card resolution error")
        raise _bad(f"Card resolution failed: {e}", "CARD_RESOLVE_ERROR", 500)

    warnings: list[str] = []
    if unresolved:
        warnings.append(f"Could not resolve {len(unresolved)} card(s): {', '.join(unresolved[:5])}")
        is_valid = False
        errors.append(f"Unresolved cards: {', '.join(unresolved)}")

    deck_id = f"deck_{uuid.uuid4().hex[:12]}"
    preview = DeckPreview(
        deck_id=deck_id,
        deck_name=deck_name,
        main_deck=main_previews,
        sideboard=sb_previews,
        total_cards=sum(c.quantity for c in main_previews),
        sideboard_count=sum(c.quantity for c in sb_previews),
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    if not req.dry_run:
        _deck_store[deck_id] = preview

    return {"data": preview.model_dump()}


@router.get("/import/{deck_id}")
def get_imported_deck(deck_id: str) -> dict:
    """GET /deck/import/{deck_id} — retrieve a previously imported deck."""
    preview = _deck_store.get(deck_id)
    if preview is None:
        raise _bad("Deck not found", "DECK_NOT_FOUND", 404)
    return {"data": preview.model_dump()}


@router.delete("/import/{deck_id}")
def delete_imported_deck(deck_id: str) -> dict:
    """DELETE /deck/import/{deck_id} — remove an imported deck."""
    if deck_id not in _deck_store:
        raise _bad("Deck not found", "DECK_NOT_FOUND", 404)
    del _deck_store[deck_id]
    return {"data": {"deck_id": deck_id, "status": "deleted"}}

"""
Pydantic v2 models for Archidekt deck import feature.

REQ-P01, REQ-P02, REQ-P03: Performance requirements
REQ-S01, REQ-S02, REQ-S03: Security requirements
REQ-U01, REQ-U02, REQ-U03: UX requirements
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DeckFormat(str, Enum):
    ARCHIDEKT_JSON = "archidekt_json"
    ARCHIDEKT_TEXT = "archidekt_text"
    SCRYFALL_TXT = "scryfall_txt"


class CardPreview(BaseModel):
    name: str
    quantity: int = Field(..., ge=1)
    scryfall_id: Optional[str] = None
    is_legal: bool = True


class DeckPreview(BaseModel):
    """REQ-U01: Preview step before final import."""
    deck_id: str
    deck_name: str
    main_deck: list[CardPreview]
    sideboard: list[CardPreview] = []
    total_cards: int
    sideboard_count: int
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    created_at: str

    @field_validator("total_cards")
    @classmethod
    def validate_total(cls, v: int, info) -> int:
        if info.data.get("main_deck"):
            expected = sum(c.quantity for c in info.data["main_deck"])
            if v != expected:
                raise ValueError("total_cards does not match main deck quantity sum")
        return v


class DeckImportRequest(BaseModel):
    """REQ-S01, REQ-S02: Validated import request."""
    archidekt_url: Optional[str] = None
    file_data: Optional[str] = None  # raw text content (UTF-8)
    file_name: Optional[str] = None
    format: Optional[DeckFormat] = None
    deck_name: Optional[str] = None
    format_name: Optional[str] = None  # e.g. "Standard", "Modern"
    dry_run: bool = False

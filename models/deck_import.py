"""
Pydantic v2 models for Archidekt deck import feature.

REQ-P01, REQ-P02, REQ-P03: Performance requirements for deck import
REQ-S01, REQ-S02, REQ-S03: Security requirements for file uploads
REQ-U01, REQ-U02, REQ-U03: UI/UX requirements for import workflow
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DeckFormat(str, Enum):
    """Supported deck file formats."""
    ARCHIDEKT_JSON = "archidekt_json"
    ARCHIDEKT_TEXT = "archidekt_text"
    SCRYALLAH_TXT = "scryfall_txt"


class CardPreview(BaseModel):
    """
    Preview information for a single card in a deck.
    
    Used in deck preview responses to show card details
    before final import.
    """
    name: str = Field(..., description="Card name")
    quantity: int = Field(..., ge=1, description="Number of copies in deck")
    scryfall_id: Optional[str] = Field(None, description="Scryfall card ID if resolved")
    is_legal: bool = Field(True, description="Whether card is legal in format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Lightning Bolt",
                "quantity": 4,
                "scryfall_id": "43534",
                "is_legal": True
            }
        }


class DeckPreview(BaseModel):
    """
    Preview of an imported deck with validation results.
    
    Contains the parsed deck structure and validation status.
    Used in the preview workflow before final import.
    
    REQ-U01: Import workflow includes preview step
    REQ-U02: Clear error messages for invalid deck formats
    """
    deck_id: str = Field(..., description="Unique identifier for imported deck")
    deck_name: str = Field(..., description="Name of the deck")
    main_deck: list[CardPreview] = Field(..., description="Main deck cards")
    sideboard: list[CardPreview] = Field(default=[], description="Sideboard cards")
    total_cards: int = Field(..., description="Total cards in main deck")
    sideboard_count: int = Field(..., description="Total cards in sideboard")
    is_valid: bool = Field(..., description="Whether deck meets format requirements")
    errors: list[str] = Field(default=[], description="Validation errors if invalid")
    warnings: list[str] = Field(default=[], description="Non-critical warnings")
    created_at: str = Field(..., description="ISO timestamp of import")
    
    @field_validator('total_cards')
    @classmethod
    def validate_total_cards(cls, v, info) -> int:
        """Ensure total_cards matches main deck quantity sum."""
        if info.data.get('main_deck'):
            calculated_total = sum(card.quantity for card in info.data['main_deck'])
            if v != calculated_total:
                raise ValueError('total_cards does not match main deck quantity sum')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "deck_id": "deck_abc123",
                "deck_name": "Mono-Red Aggro",
                "main_deck": [
                    {"name": "Lightning Bolt", "quantity": 4, "scryfall_id": "43534", "is_legal": True}
                ],
                "sideboard": [],
                "total_cards": 60,
                "sideboard_count": 0,
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "created_at": "2026-03-20T12:00:00Z"
            }
        }


class DeckImportRequest(BaseModel):
    """
    Request model for deck import.
    
    Accepts deck data via URL (Archidekt) or file upload.
    Supports multiple deck formats.
    
    REQ-P01: Performance requirements for deck loading
    REQ-S01, REQ-S02: Security validation for file uploads
    """
    archidekt_url: Optional[str] = Field(
        None,
        description="URL to Archidekt deck (alternative to file_data)"
    )
    file_data: Optional[bytes] = Field(
        None,
        description="Uploaded file content (alternative to archidekt_url)"
    )
    file_name: Optional[str] = Field(
        None,
        description="Name of uploaded file"
    )
    format: Optional[DeckFormat] = Field(
        None,
        description="Deck format (auto-detected if not provided)"
    )
    deck_name: Optional[str] = Field(
        None,
        description="Custom deck name (auto-generated if not provided)"
    )
    format_name: Optional[str] = Field(
        None,
        description="Format name (Standard
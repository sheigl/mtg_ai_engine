"""
APP-02: Deck Building AI — REST endpoint for stateless deck construction.

POST /ai/deck/build takes a card pool, format, and strategy description to produce
a legal, optimized MTG deck via the Filter → Score → Select → Validate pipeline.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/deck", tags=["deck-building-ai"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CardPoolEntry(BaseModel):
    """A single card in the input pool."""
    name: str
    mana_cost: Optional[str] = None
    type_line: str = ""
    oracle_text: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    cmc: float = 0.0
    rarity: Optional[str] = None
    set_code: Optional[str] = None


class DeckBuildRequest(BaseModel):
    """POST /ai/deck/build request body."""
    cards: list[CardPoolEntry]
    format: str
    strategy: str = "midrange"
    commanders: Optional[list[str]] = None
    seed: Optional[int] = None

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        allowed = {"aggro", "control", "midrange", "combo"}
        if v.lower() not in allowed:
            raise ValueError(f"Strategy must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        from mtg_engine.engine.formats import FORMAT_VALIDATORS
        if v.lower().strip() not in FORMAT_VALIDATORS:
            raise ValueError(f"Unknown format: '{v}'")
        return v.lower().strip()

    model_config = {"json_schema_extra": {
        "examples": [{
            "cards": [
                {"name": "Lightning Bolt", "mana_cost": "{R}", "type_line": "Instant",
                 "oracle_text": "Lightning Bolt deals 3 damage to any target."},
                {"name": "Mountain", "type_line": "Land"},
            ],
            "format": "modern",
            "strategy": "aggro",
        }]
    }}


class DeckEntry(BaseModel):
    """A card entry in the constructed deck."""
    name: str
    quantity: int = Field(ge=1)


class DeckBuildResponse(BaseModel):
    """POST /ai/deck/build response body."""
    deck: list[DeckEntry]
    sideboard: list[DeckEntry]
    validation: dict  # {"valid": bool, "violations": list[str], "format": str}
    strategy: str
    format: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/build", response_model=DeckBuildResponse)
async def build_deck_endpoint(req: DeckBuildRequest) -> dict:
    """
    POST /ai/deck/build — construct an optimized deck from a card pool.

    Pipeline: Filter → Score → Select → Validate.
    Returns the constructed main deck, sideboard, and validation results.
    """
    from mtg_engine.ai.deck_builder import build_deck as engine_build_deck
    from mtg_engine.models.game import Card

    # Convert request cards to Card models
    card_pool: list[Card] = []
    for entry in req.cards:
        card_pool.append(Card(
            name=entry.name,
            mana_cost=entry.mana_cost,
            type_line=entry.type_line,
            oracle_text=entry.oracle_text,
            power=entry.power,
            toughness=entry.toughness,
            colors=entry.colors,
            color_identity=entry.color_identity,
            keywords=entry.keywords,
            cmc=entry.cmc,
            rarity=entry.rarity,
            set_code=entry.set_code,
        ))

    # Run the engine pipeline
    result = engine_build_deck(
        card_pool=card_pool,
        format_name=req.format,
        strategy=req.strategy,
        commander_names=req.commanders,
        seed=req.seed,
    )

    # Convert to response model
    deck_entries = [DeckEntry(**e) for e in result["deck"]]
    sideboard_entries = [DeckEntry(**e) for e in result["sideboard"]]

    return {
        "deck": deck_entries,
        "sideboard": sideboard_entries,
        "validation": result["validation"],
        "strategy": req.strategy,
        "format": req.format,
    }

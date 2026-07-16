"""
Card Search API endpoints.

APP-01: GET /cards/search — full-text + faceted search against local SQLite cache.
All filters combine with AND logic. Results are paginated and sortable.
No Scryfall API calls during search; read-only on cached data.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from mtg_engine.card_data.scryfall import ScryfallClient
from mtg_engine.models.game import Card

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cards", tags=["card-search"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bad(msg: str, code: str, status: int = 400) -> Exception:
    from fastapi import HTTPException
    return HTTPException(status_code=status, detail={"error": msg, "error_code": code})


# ── Response models ───────────────────────────────────────────────────────────

class SearchCardResponse(BaseModel):
    """Single card in search results."""
    name: str
    mana_cost: Optional[str] = None
    type_line: str = ""
    oracle_text: Optional[str] = None
    colors: list[str] = Field(default_factory=list)
    cmc: float = 0.0
    keywords: list[str] = Field(default_factory=list)
    rarity: Optional[str] = None
    set_code: Optional[str] = None


class CardSearchResponse(BaseModel):
    """Paginated search response."""
    cards: list[SearchCardResponse]
    total: int
    page: int
    per_page: int


# ── Singleton ScryfallClient for search ───────────────────────────────────────

_search_client: Optional[ScryfallClient] = None


def _get_search_client() -> ScryfallClient:
    """Lazy-initialize the shared ScryfallClient instance."""
    global _search_client
    if _search_client is None:
        _search_client = ScryfallClient()
    return _search_client


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/search")
def search_cards(
    q: Optional[str] = Query(default=None, description="Free-text search (name + oracle_text)"),
    type: Optional[str] = Query(default=None, alias="type", description="Card type substring match"),
    colors: Optional[str] = Query(default=None, description="Comma-separated colors: W,U,B,R,G,C"),
    cmc_min: Optional[float] = Query(default=None, ge=0, description="Minimum converted mana cost"),
    cmc_max: Optional[float] = Query(default=None, ge=0, description="Maximum converted mana cost"),
    mana_cost: Optional[str] = Query(default=None, description="Exact mana cost match e.g. {2}{R}"),
    keyword: Optional[str] = Query(default=None, description="Card must have this keyword"),
    rarity: Optional[str] = Query(default=None, description="Filter by rarity (c/u/r/m/mythical/special)"),
    set_code: Optional[str] = Query(default=None, description="3-letter set code"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=25, ge=1, le=100, description="Results per page (max 100)"),
    sort_by: str = Query(default="name", description="Sort field: name or cmc"),
    sort_order: str = Query(default="asc", description="Sort direction: asc or desc"),
) -> dict:
    """
    GET /cards/search — search the local card cache.

    All filters combine with AND logic. Results are paginated and sorted by name ascending by default.
    Returns HTTP 400 for invalid parameters.
    """
    # Parse colors from comma-separated string
    color_list: Optional[list[str]] = None
    if colors:
        color_list = [c.strip() for c in colors.split(",") if c.strip()]

    try:
        client = _get_search_client()
        cards, total = client.search_cards(
            q=q,
            type_line=type,
            colors=color_list,
            cmc_min=cmc_min,
            cmc_max=cmc_max,
            mana_cost=mana_cost,
            keyword=keyword,
            rarity=rarity,
            set_code=set_code,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as e:
        raise _bad(str(e), "INVALID_PARAMETER", 400)

    result = CardSearchResponse(
        cards=[SearchCardResponse(**c.model_dump()) for c in cards],
        total=total,
        page=page,
        per_page=per_page,
    )

    return {"data": result.model_dump()}

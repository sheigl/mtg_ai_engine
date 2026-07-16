"""APP-01 Card Search API tests — engine layer + API endpoint."""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from mtg_engine.card_data.scryfall import ScryfallClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def search_client(tmp_path: Path) -> ScryfallClient:
    return ScryfallClient(db_path=tmp_path / "search_cache.db")


@pytest.fixture
def populated_cache(search_client: ScryfallClient) -> ScryfallClient:
    """Populate cache with test cards for filtering tests."""
    test_cards = [
        {
            "id": "test-001",
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "colors": ["R"],
            "cmc": 1.0,
            "keywords": [],
            "rarity": "uncommon",
            "set": "MOM",
        },
        {
            "id": "test-002",
            "name": "Avacyn's Pilgrim",
            "mana_cost": "{W}",
            "type_line": "Creature — Human Cleric",
            "oracle_text": "Flying. Whenever Avacyn's Pilgrim enters the battlefield, create a Mountain and a Forest.",
            "colors": ["W"],
            "cmc": 1.0,
            "keywords": ["flying"],
            "rarity": "common",
            "set": "AVR",
        },
        {
            "id": "test-003",
            "name": "Llanowar Elves",
            "mana_cost": "{G}",
            "type_line": "Creature — Elf Druid",
            "oracle_text": "Tap: Add {G}.",
            "colors": ["G"],
            "cmc": 1.0,
            "keywords": [],
            "rarity": "common",
            "set": "MOM",
        },
        {
            "id": "test-004",
            "name": "Lightning Strike",
            "mana_cost": "{R}",
            "type_line": "Instant",
            "oracle_text": "Lightning Strike deals 3 damage to any target.",
            "colors": ["R"],
            "cmc": 1.0,
            "keywords": [],
            "rarity": "common",
            "set": "MOM",
        },
        {
            "id": "test-005",
            "name": "Giant Growth",
            "mana_cost": "{G}{G}",
            "type_line": "Sorcery",
            "oracle_text": "Target creature gets +3/+3 until end of turn.",
            "colors": ["G"],
            "cmc": 2.0,
            "keywords": [],
            "rarity": "common",
            "set": "MOM",
        },
        {
            "id": "test-006",
            "name": "Lightning Helix",
            "mana_cost": "{1}{R}",
            "type_line": "Sorcery",
            "oracle_text": "Cascade. Lightning Helix deals 3 damage to any target.",
            "colors": ["R"],
            "cmc": 2.0,
            "keywords": ["cascade"],
            "rarity": "rare",
            "set": "MOM",
        },
        {
            "id": "test-007",
            "name": "Jeska's Will",
            "mana_cost": "{2}{R}",
            "type_line": "Sorcery",
            "oracle_text": "Jeska's Will deals 3 damage to any target. You may cast target instant card from your graveyard this turn.",
            "colors": ["R"],
            "cmc": 3.0,
            "keywords": [],
            "rarity": "rare",
            "set": "MOM",
        },
        {
            "id": "test-008",
            "name": "Lightning Greaves",
            "mana_cost": "{2}",
            "type_line": "Artifact — Equipment",
            "oracle_text": "Equipped creature has haste and shroud. Equip.",
            "colors": [],
            "cmc": 2.0,
            "keywords": ["haste", "shroud"],
            "rarity": "common",
            "set": "MOM",
        },
    ]
    for card in test_cards:
        search_client._cache_put(card)
    return search_client


@pytest.fixture
def app_client(populated_cache: ScryfallClient) -> TestClient:
    """FastAPI test client with a populated cache."""
    from mtg_engine.api.main import app

    # Inject the test client into the router's singleton
    import mtg_engine.api.routers.card_search as cs_router
    old = cs_router._search_client
    cs_router._search_client = populated_cache
    try:
        yield TestClient(app)
    finally:
        cs_router._search_client = old


# ── Engine Layer Tests (ScryfallClient.search_cards) ─────────────────────────

class TestSearchEngineLayer:
    """Tests for ScryfallClient.search_cards() directly."""

    def test_free_text_search_by_name(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(q="Lightning")
        assert total == 4  # Lightning Bolt, Strike, Helix, Greaves
        names = [c.name for c in cards]
        assert "Lightning Bolt" in names
        assert "Lightning Strike" in names
        assert "Lightning Helix" in names
        assert "Lightning Greaves" in names

    def test_free_text_search_by_oracle(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(q="deals 3 damage")
        assert total == 4  # Lightning Bolt, Strike, Helix, Jeska's Will
        names = [c.name for c in cards]
        assert "Lightning Bolt" in names

    def test_filter_by_type(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(type_line="Instant")
        assert total == 2
        assert all("Instant" in c.type_line for c in cards)

    def test_filter_by_type_creature(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(type_line="Creature")
        assert total == 2  # Avacyn's Pilgrim, Llanowar Elves

    def test_filter_by_color(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(colors=["R"])
        assert total == 4  # Lightning Bolt, Strike, Helix, Jeska's Will
        assert all("R" in c.colors for c in cards)

    def test_filter_by_color_green(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(colors=["G"])
        assert total == 2  # Llanowar Elves, Giant Growth

    def test_cmc_range_max(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(cmc_max=1.0)
        assert total == 4  # All cmc=1 cards (Bolt, Pilgrim, Elves, Strike)
        assert all(c.cmc <= 1.0 for c in cards)

    def test_cmc_range_min(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(cmc_min=2.0)
        assert total == 4  # Giant Growth(2), Helix(2), Jeska's Will(3), Greaves(2)
        assert all(c.cmc >= 2.0 for c in cards)

    def test_cmc_range_both(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(cmc_min=1.5, cmc_max=2.5)
        assert total == 3  # Giant Growth(2), Helix(2), Greaves(2)
        assert all(1.5 <= c.cmc <= 2.5 for c in cards)

    def test_combined_filters_and_logic(self, populated_cache: ScryfallClient):
        """type=Instant AND colors=R should return only red instants."""
        cards, total = populated_cache.search_cards(type_line="Instant", colors=["R"])
        assert total == 2  # Lightning Bolt and Lightning Strike
        names = [c.name for c in cards]
        assert "Lightning Bolt" in names
        assert "Lightning Strike" in names

    def test_combined_filters_no_match(self, populated_cache: ScryfallClient):
        """type=Creature AND colors=R should return nothing (no red creatures)."""
        cards, total = populated_cache.search_cards(type_line="Creature", colors=["R"])
        assert total == 0
        assert cards == []

    def test_keyword_filter(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(keyword="flying")
        assert total == 1
        assert cards[0].name == "Avacyn's Pilgrim"

    def test_keyword_filter_cascade(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(keyword="cascade")
        assert total == 1
        assert cards[0].name == "Lightning Helix"

    def test_rarity_filter(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(rarity="common")
        assert total == 5  # Pilgrim, Elves, Strike, Growth, Greaves
        assert all(c.rarity == "common" for c in cards)

    def test_rarity_filter_rare(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(rarity="rare")
        assert total == 2  # Helix, Jeska's Will

    def test_set_code_filter(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(set_code="AVR")
        assert total == 1
        assert cards[0].name == "Avacyn's Pilgrim"

    def test_exact_mana_cost(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(mana_cost="{G}{G}")
        assert total == 1
        assert cards[0].name == "Giant Growth"

    def test_empty_cache(self, search_client: ScryfallClient):
        """Empty cache returns empty results."""
        cards, total = search_client.search_cards(q="nonexistent")
        assert total == 0
        assert cards == []

    def test_pagination_page_1(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(per_page=3, page=1)
        assert total == 8
        assert len(cards) == 3

    def test_pagination_page_2(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(per_page=3, page=2)
        assert total == 8
        assert len(cards) == 3

    def test_pagination_last_page_partial(self, populated_cache: ScryfallClient):
        """Last page has fewer items than per_page."""
        cards, total = populated_cache.search_cards(per_page=3, page=3)
        assert total == 8
        assert len(cards) == 2  # 8 - 6 = 2 remaining

    def test_pagination_beyond_results(self, populated_cache: ScryfallClient):
        cards, total = populated_cache.search_cards(per_page=3, page=10)
        assert total == 8
        assert cards == []

    def test_sort_by_name_asc(self, populated_cache: ScryfallClient):
        cards, _ = populated_cache.search_cards(sort_by="name", sort_order="asc")
        names = [c.name for c in cards]
        assert names == sorted(names)

    def test_sort_by_name_desc(self, populated_cache: ScryfallClient):
        cards, _ = populated_cache.search_cards(sort_by="name", sort_order="desc")
        names = [c.name for c in cards]
        assert names == sorted(names, reverse=True)

    def test_sort_by_cmc_asc(self, populated_cache: ScryfallClient):
        cards, _ = populated_cache.search_cards(sort_by="cmc", sort_order="asc")
        cmcs = [c.cmc for c in cards]
        # Should be non-decreasing (with name as tiebreaker)
        assert cmcs == sorted(cmcs)

    def test_sort_by_cmc_desc(self, populated_cache: ScryfallClient):
        cards, _ = populated_cache.search_cards(sort_by="cmc", sort_order="desc")
        cmcs = [c.cmc for c in cards]
        # Should be non-increasing
        assert cmcs == sorted(cmcs, reverse=True)

    def test_invalid_sort_by(self, populated_cache: ScryfallClient):
        with pytest.raises(ValueError, match="sort_by"):
            populated_cache.search_cards(sort_by="invalid")

    def test_invalid_sort_order(self, populated_cache: ScryfallClient):
        with pytest.raises(ValueError, match="sort_order"):
            populated_cache.search_cards(sort_order="random")

    def test_invalid_page(self, populated_cache: ScryfallClient):
        with pytest.raises(ValueError, match="page"):
            populated_cache.search_cards(page=0)

    def test_invalid_per_page_too_small(self, populated_cache: ScryfallClient):
        with pytest.raises(ValueError, match="per_page"):
            populated_cache.search_cards(per_page=0)

    def test_invalid_per_page_too_large(self, populated_cache: ScryfallClient):
        with pytest.raises(ValueError, match="per_page"):
            populated_cache.search_cards(per_page=101)

    def test_invalid_color(self, populated_cache: ScryfallClient):
        with pytest.raises(ValueError, match="Invalid color"):
            populated_cache.search_cards(colors=["X"])

    def test_case_insensitive_search(self, populated_cache: ScryfallClient):
        """Free-text search should be case-insensitive."""
        cards_upper, total_upper = populated_cache.search_cards(q="LIGHTNING")
        cards_lower, total_lower = populated_cache.search_cards(q="lightning")
        assert total_upper == total_lower
        assert total_upper == 4

    def test_result_includes_all_fields(self, populated_cache: ScryfallClient):
        """Each result card includes all required fields."""
        cards, _ = populated_cache.search_cards(q="Lightning Bolt")
        c = cards[0]
        assert c.name is not None
        assert c.mana_cost is not None or c.mana_cost == ""
        assert isinstance(c.type_line, str)
        assert isinstance(c.colors, list)
        assert isinstance(c.cmc, float)
        assert isinstance(c.keywords, list)
        assert c.rarity is not None
        assert c.set_code is not None

    def test_cache_miss_no_api_call(self, search_client: ScryfallClient):
        """Search for a card not in cache returns empty (no API call)."""
        cards, total = search_client.search_cards(q="Some Nonexistent Card")
        assert total == 0
        assert cards == []


# ── API Endpoint Tests ───────────────────────────────────────────────────────

class TestSearchAPIEndpoint:
    """Tests for GET /cards/search endpoint."""

    def test_api_free_text_search(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"q": "Lightning"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 4
        assert len(data["cards"]) == 4

    def test_api_filter_by_type(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"type": "Instant"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2

    def test_api_filter_by_colors(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"colors": "R,G"})
        assert resp.status_code == 200
        # No card has both R and G colors in our test data
        data = resp.json()["data"]
        assert data["total"] == 0

    def test_api_cmc_range(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"cmc_min": "1.5", "cmc_max": "2.5"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3

    def test_api_pagination(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"per_page": "3", "page": "1"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 8
        assert len(data["cards"]) == 3
        assert data["page"] == 1
        assert data["per_page"] == 3

    def test_api_combined_filters(self, app_client: TestClient):
        """type=Instant AND colors=R."""
        resp = app_client.get("/cards/search", params={"type": "Instant", "colors": "R"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2

    def test_api_keyword_filter(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"keyword": "flying"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["cards"][0]["name"] == "Avacyn's Pilgrim"

    def test_api_sort_by_cmc_desc(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"sort_by": "cmc", "sort_order": "desc"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        cmcs = [c["cmc"] for c in data["cards"]]
        assert cmcs == sorted(cmcs, reverse=True)

    def test_api_invalid_sort_by(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"sort_by": "invalid"})
        assert resp.status_code == 400
        assert "INVALID_PARAMETER" in resp.json()["detail"]["error_code"]

    def test_api_invalid_page(self, app_client: TestClient):
        """page=0 should be rejected by FastAPI validation."""
        resp = app_client.get("/cards/search", params={"page": "0"})
        # FastAPI validates ge=1 at the router level → 422
        assert resp.status_code == 422

    def test_api_invalid_per_page(self, app_client: TestClient):
        """per_page=0 should be rejected by FastAPI validation."""
        resp = app_client.get("/cards/search", params={"per_page": "0"})
        assert resp.status_code == 422

    def test_api_empty_results(self, app_client: TestClient):
        resp = app_client.get("/cards/search", params={"q": "nonexistent card xyz"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["cards"] == []

    def test_api_response_structure(self, app_client: TestClient):
        """Response has correct nested structure."""
        resp = app_client.get("/cards/search", params={"q": "Lightning Bolt"})
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert "cards" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_api_card_fields(self, app_client: TestClient):
        """Each card in results has all required fields."""
        resp = app_client.get("/cards/search", params={"q": "Lightning Bolt"})
        card = resp.json()["data"]["cards"][0]
        assert "name" in card
        assert "mana_cost" in card
        assert "type_line" in card
        assert "oracle_text" in card
        assert "colors" in card
        assert "cmc" in card
        assert "keywords" in card
        assert "rarity" in card
        assert "set_code" in card

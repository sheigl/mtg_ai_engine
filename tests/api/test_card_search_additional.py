"""APP-01 Card Search API — additional integration tests for coverage gaps.

These tests cover acceptance criteria items not exercised by the existing test suite:
- rarity, set_code, mana_cost via HTTP endpoint
- default pagination (page=1, per_page=25)
- sort defaults (name asc)
- combined filter edge cases at API level
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from mtg_engine.card_data.scryfall import ScryfallClient


# ── Fixtures (mirror test_card_search.py) ─────────────────────────────────────

@pytest.fixture
def search_client(tmp_path: Path) -> ScryfallClient:
    return ScryfallClient(db_path=tmp_path / "search_cache.db")


@pytest.fixture
def populated_cache(search_client: ScryfallClient) -> ScryfallClient:
    """Populate cache with test cards for filtering tests."""
    test_cards = [
        {
            "id": "test-001", "name": "Lightning Bolt", "mana_cost": "{R}",
            "type_line": "Instant", "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "colors": ["R"], "cmc": 1.0, "keywords": [],
            "rarity": "uncommon", "set": "MOM",
        },
        {
            "id": "test-002", "name": "Avacyn's Pilgrim", "mana_cost": "{W}",
            "type_line": "Creature — Human Cleric",
            "oracle_text": "Flying. Whenever Avacyn's Pilgrim enters the battlefield, create a Mountain and a Forest.",
            "colors": ["W"], "cmc": 1.0, "keywords": ["flying"],
            "rarity": "common", "set": "AVR",
        },
        {
            "id": "test-003", "name": "Llanowar Elves", "mana_cost": "{G}",
            "type_line": "Creature — Elf Druid", "oracle_text": "Tap: Add {G}.",
            "colors": ["G"], "cmc": 1.0, "keywords": [],
            "rarity": "common", "set": "MOM",
        },
        {
            "id": "test-004", "name": "Lightning Strike", "mana_cost": "{R}",
            "type_line": "Instant", "oracle_text": "Lightning Strike deals 3 damage to any target.",
            "colors": ["R"], "cmc": 1.0, "keywords": [],
            "rarity": "common", "set": "MOM",
        },
        {
            "id": "test-005", "name": "Giant Growth", "mana_cost": "{G}{G}",
            "type_line": "Sorcery", "oracle_text": "Target creature gets +3/+3 until end of turn.",
            "colors": ["G"], "cmc": 2.0, "keywords": [],
            "rarity": "common", "set": "MOM",
        },
        {
            "id": "test-006", "name": "Lightning Helix", "mana_cost": "{1}{R}",
            "type_line": "Sorcery", "oracle_text": "Cascade. Lightning Helix deals 3 damage to any target.",
            "colors": ["R"], "cmc": 2.0, "keywords": ["cascade"],
            "rarity": "rare", "set": "MOM",
        },
        {
            "id": "test-007", "name": "Jeska's Will", "mana_cost": "{2}{R}",
            "type_line": "Sorcery",
            "oracle_text": "Jeska's Will deals 3 damage to any target. You may cast target instant card from your graveyard this turn.",
            "colors": ["R"], "cmc": 3.0, "keywords": [],
            "rarity": "rare", "set": "MOM",
        },
        {
            "id": "test-008", "name": "Lightning Greaves", "mana_cost": "{2}",
            "type_line": "Artifact — Equipment",
            "oracle_text": "Equipped creature has haste and shroud. Equip.",
            "colors": [], "cmc": 2.0, "keywords": ["haste", "shroud"],
            "rarity": "common", "set": "MOM",
        },
    ]
    for card in test_cards:
        search_client._cache_put(card)
    return search_client


@pytest.fixture
def app_client(populated_cache: ScryfallClient) -> TestClient:
    """FastAPI test client with a populated cache."""
    from mtg_engine.api.main import app

    import mtg_engine.api.routers.card_search as cs_router
    old = cs_router._search_client
    cs_router._search_client = populated_cache
    try:
        yield TestClient(app)
    finally:
        cs_router._search_client = old


# ── API Endpoint Tests for Missing Coverage ───────────────────────────────────

class TestSearchAPIAdditionalCoverage:
    """Tests covering acceptance criteria gaps in the original test suite."""

    def test_api_rarity_filter(self, app_client: TestClient):
        """rarity parameter works via HTTP endpoint."""
        resp = app_client.get("/cards/search", params={"rarity": "common"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5  # Pilgrim, Elves, Strike, Growth, Greaves
        for card in data["cards"]:
            assert card["rarity"] == "common"

    def test_api_rarity_filter_rare(self, app_client: TestClient):
        """rarity=rare returns only rare cards."""
        resp = app_client.get("/cards/search", params={"rarity": "rare"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2  # Helix, Jeska's Will

    def test_api_set_code_filter(self, app_client: TestClient):
        """set_code parameter works via HTTP endpoint."""
        resp = app_client.get("/cards/search", params={"set_code": "AVR"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["cards"][0]["name"] == "Avacyn's Pilgrim"

    def test_api_mana_cost_filter(self, app_client: TestClient):
        """mana_cost exact match works via HTTP endpoint."""
        resp = app_client.get("/cards/search", params={"mana_cost": "{G}{G}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["cards"][0]["name"] == "Giant Growth"

    def test_api_default_pagination(self, app_client: TestClient):
        """Default page=1 and per_page=25 when not specified."""
        resp = app_client.get("/cards/search")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1
        assert data["per_page"] == 25
        # All 8 cards fit in one page of 25
        assert data["total"] == 8
        assert len(data["cards"]) == 8

    def test_api_default_sort_name_asc(self, app_client: TestClient):
        """Default sort is by name ascending."""
        resp = app_client.get("/cards/search")
        assert resp.status_code == 200
        data = resp.json()["data"]
        names = [c["name"] for c in data["cards"]]
        assert names == sorted(names)

    def test_api_all_filters_combined(self, app_client: TestClient):
        """Multiple filters combine with AND logic at API level."""
        # type=Sorcery AND colors=R should return Helix and Jeska's Will
        resp = app_client.get("/cards/search", params={
            "type": "Sorcery",
            "colors": "R",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        names = {c["name"] for c in data["cards"]}
        assert "Lightning Helix" in names
        assert "Jeska's Will" in names

    def test_api_type_and_rarity_combined(self, app_client: TestClient):
        """type AND rarity combined filter."""
        resp = app_client.get("/cards/search", params={
            "type": "Creature",
            "rarity": "common",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2  # Pilgrim, Elves

    def test_api_q_and_type_combined(self, app_client: TestClient):
        """Free-text q AND type combined filter."""
        resp = app_client.get("/cards/search", params={
            "q": "Lightning",
            "type": "Instant",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Lightning Bolt and Lightning Strike are both Instant + have "Lightning" in name
        assert data["total"] == 2

    def test_api_cmc_and_keyword_combined(self, app_client: TestClient):
        """cmc range AND keyword combined filter."""
        resp = app_client.get("/cards/search", params={
            "cmc_min": "1.0",
            "cmc_max": "2.0",
            "keyword": "cascade",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["cards"][0]["name"] == "Lightning Helix"

    def test_api_no_params_returns_all(self, app_client: TestClient):
        """No query params returns all cards in cache."""
        resp = app_client.get("/cards/search")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 8

    def test_api_color_filter_case_insensitive(self, app_client: TestClient):
        """Color filter should be case-insensitive."""
        resp_upper = app_client.get("/cards/search", params={"colors": "R"})
        resp_lower = app_client.get("/cards/search", params={"colors": "r"})
        assert resp_upper.status_code == 200
        assert resp_lower.status_code == 200
        total_upper = resp_upper.json()["data"]["total"]
        total_lower = resp_lower.json()["data"]["total"]
        assert total_upper == total_lower

    def test_api_invalid_color_returns_400(self, app_client: TestClient):
        """Invalid color returns HTTP 400."""
        resp = app_client.get("/cards/search", params={"colors": "X"})
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "INVALID_PARAMETER" in detail["error_code"]

    def test_api_sort_by_cmc_asc(self, app_client: TestClient):
        """Sort by cmc ascending."""
        resp = app_client.get("/cards/search", params={
            "sort_by": "cmc",
            "sort_order": "asc",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        cmcs = [c["cmc"] for c in data["cards"]]
        assert cmcs == sorted(cmcs)

    def test_api_sort_by_name_desc(self, app_client: TestClient):
        """Sort by name descending."""
        resp = app_client.get("/cards/search", params={
            "sort_by": "name",
            "sort_order": "desc",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        names = [c["name"] for c in data["cards"]]
        assert names == sorted(names, reverse=True)

    def test_api_per_page_max_100(self, app_client: TestClient):
        """per_page=100 is accepted (max allowed)."""
        resp = app_client.get("/cards/search", params={"per_page": "100"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["per_page"] == 100

    def test_api_per_page_exceeds_100_rejected(self, app_client: TestClient):
        """per_page > 100 is rejected by FastAPI validation."""
        resp = app_client.get("/cards/search", params={"per_page": "101"})
        assert resp.status_code == 422

    def test_api_negative_cmc_min_rejected(self, app_client: TestClient):
        """Negative cmc_min is rejected by FastAPI validation."""
        resp = app_client.get("/cards/search", params={"cmc_min": "-1"})
        assert resp.status_code == 422


# ── Engine Layer Additional Tests ─────────────────────────────────────────────

class TestSearchEngineAdditional:
    """Additional engine layer tests for edge cases."""

    def test_search_no_filters_returns_all(self, populated_cache: ScryfallClient):
        """No filters returns all cards sorted by name ascending."""
        cards, total = populated_cache.search_cards()
        assert total == 8
        names = [c.name for c in cards]
        assert names == sorted(names)

    def test_search_empty_q_returns_all(self, populated_cache: ScryfallClient):
        """Empty string q returns all cards (no filter applied)."""
        cards, total = populated_cache.search_cards(q="")
        assert total == 8

    def test_color_filter_normalizes_case(self, populated_cache: ScryfallClient):
        """Color filter normalizes to uppercase."""
        cards_upper, total_upper = populated_cache.search_cards(colors=["R"])
        cards_lower, total_lower = populated_cache.search_cards(colors=["r"])
        assert total_upper == total_lower

    def test_multiple_colors_and_logic(self, populated_cache: ScryfallClient):
        """Multiple colors use AND logic (card must have ALL specified)."""
        # No card has both R and G in our test data
        cards, total = populated_cache.search_cards(colors=["R", "G"])
        assert total == 0

    def test_keyword_case_insensitive(self, populated_cache: ScryfallClient):
        """Keyword filter is case-insensitive."""
        cards_upper, total_upper = populated_cache.search_cards(keyword="FLYING")
        cards_lower, total_lower = populated_cache.search_cards(keyword="flying")
        assert total_upper == total_lower
        assert total_upper == 1

    def test_rarity_case_insensitive(self, populated_cache: ScryfallClient):
        """Rarity filter is case-insensitive."""
        cards_upper, total_upper = populated_cache.search_cards(rarity="COMMON")
        cards_lower, total_lower = populated_cache.search_cards(rarity="common")
        assert total_upper == total_lower

    def test_pagination_offset_calculation(self, populated_cache: ScryfallClient):
        """Page 2 with per_page=4 returns items 5-8."""
        _, all_total = populated_cache.search_cards()
        assert all_total == 8

        cards_p1, _ = populated_cache.search_cards(per_page=4, page=1)
        cards_p2, _ = populated_cache.search_cards(per_page=4, page=2)

        # No overlap between pages
        names_p1 = {c.name for c in cards_p1}
        names_p2 = {c.name for c in cards_p2}
        assert len(names_p1 & names_p2) == 0
        assert len(cards_p1) == 4
        assert len(cards_p2) == 4

    def test_sort_cmc_with_name_tiebreaker(self, populated_cache: ScryfallClient):
        """When sorting by cmc, cards with same cmc are sorted by name."""
        cards, _ = populated_cache.search_cards(sort_by="cmc", sort_order="asc")
        # Group by cmc and check each group is sorted by name
        from collections import defaultdict
        groups = defaultdict(list)
        for c in cards:
            groups[c.cmc].append(c.name)
        for cmc, names in groups.items():
            assert names == sorted(names), f"Names at cmc={cmc} not sorted: {names}"

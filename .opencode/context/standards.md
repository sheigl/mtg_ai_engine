# mtg_ai_engine — Coding Standards for FMT-01 Implementation

## Testing Framework
- **pytest** for all tests
- Use `pytest.mark.cr("XXX.X")` for rules-engine tests referencing specific Comprehensive Rules
- Test fixtures go in `conftest.py` or as module-level helpers
- Prefer module-level helper functions (`_make_card`, `_make_game`) over class fixtures for simple object creation

## Backend Code (Python 3.11 + FastAPI + Pydantic v2)
- All models use Pydantic v2 `BaseModel` with `Field(default_factory=...)` for mutable defaults
- Engine functions should be pure — take inputs, return results without side effects
- Use `model_copy(update={...})` for Pydantic updates (never mutate directly)
- Import style: `from mtg_engine.models.game import Card, GameState, PlayerState`
- Banned/restricted list lookups are case-insensitive — normalize to lowercase before comparison

## Format Validation Coding Standards (FMT-01)
- **Banned lists**: Hardcoded in `mtg_engine/engine/formats/banned.py`. Each entry includes a comment with the date of last update and source URL.
- **Card name matching**: Always case-insensitive. Normalize both list entries and query keys to lowercase.
- **Unknown format handling**: The dispatcher returns `(False, ["Unknown format: ..."])` — never raise an exception for unknown formats at the engine layer. API layer converts this to a 400 response.
- **Graceful degradation**: If `card.rarity` or `card.set_code` is `None`, skip checks that depend on those fields rather than producing false positives.
- **Commander reuse**: Always call `validate_deck_for_commander()` from `commander.py` for Commander format — don't duplicate its logic.

## API Endpoint Standards
- Request/response models are Pydantic v2 `BaseModel` classes defined in the router file or a shared models module
- Error responses follow pattern: `{"error": str, "error_code": str}` wrapped in HTTPException
- Success responses wrap data in `{"data": ...}` for consistency with existing endpoints

## Sample Backend Code (Format Validation)
```python
from mtg_engine.models.game import Card
from mtg_engine.engine.formats.banned import is_banned, is_restricted
from mtg_engine.engine.formats import validate_deck

# Banned list lookup
assert is_banned("Ancestral Recall", "legacy") is True  # If on the list
assert is_banned("Basic Island", "modern") is False

# Restricted list (Vintage only)
assert is_restricted("Black Lotus") is True

# Full deck validation
cards = [Card(name="Lightning Bolt"), Card(name="Forest")] * 30
is_valid, violations = validate_deck(cards, "modern")
if not is_valid:
    for v in violations:
        print(f"Violation: {v}")

# Commander with commanders specified
commander_card = Card(
    name="Niv-Mizzet", type_line="Legendary Creature — Dragon Shapeshifter",
    color_identity=["R"],
)
deck_cards = [commander_card] + [Card(name=f"Card {i}") for i in range(99)]
is_valid, violations = validate_deck(deck_cards, "commander", commanders=[commander_card])
```

## Card Search API Coding Standards (APP-01)
- **Search operates on SQLite cache only**: `ScryfallClient.search_cards()` never calls the Scryfall API. If a card is not cached, it does not appear in results.
- **Two-query pagination**: Execute separate COUNT query + SELECT with LIMIT/OFFSET. Returns `(list[Card], int)` tuple (cards, total_count).
- **SQLite json_extract() for filtering**: Use `json_extract(data_json, '$.field')` to filter on fields stored in the JSON blob. No schema migration needed.
- **Case-insensitive LIKE for free-text search**: Use `LOWER()` + `LIKE '%...%'` on both name and oracle_text columns. SQLite default collation is case-insensitive for ASCII.
- **AND logic for combined filters**: All query parameters combine with AND (e.g., type=Creature AND colors=W AND cmc_max=3).
- **Keyword matching via quoted substring**: Keywords stored as JSON arrays `["flying", "haste"]`. Match with `LIKE '%"keyword"%'` to avoid false positives.
- **Color AND logic**: Card must contain ALL specified colors. Build dynamic SQL appending one `AND json_extract(...) LIKE '%"?%"%'` per color.
- **NULL oracle_text handling**: Use `COALESCE(json_extract(data_json, '$.oracle_text'), '')` for free-text search to avoid NULL always-false behavior.
- **Parameterized queries only**: All user input goes through `?` placeholders — never string-interpolate into SQL.
- **Lightweight card building**: `_build_search_card()` extracts only fields needed for search results (no faces, no uuid generation).

### Sample Backend Code (Card Search Engine)
```python
from mtg_engine.card_data.scryfall import ScryfallClient
from pathlib import Path

# Create client with test cache
client = ScryfallClient(db_path=Path("/tmp/test_cache.db"))

# Seed cache with test data
test_card = {
    "id": "abc-123", "name": "Lightning Bolt", "mana_cost": "{R}",
    "type_line": "Instant", "oracle_text": "Deals 3 damage to any target.",
    "colors": ["R"], "cmc": 1.0, "keywords": [],
    "rarity": "uncommon", "set": "MOM",
}
client._cache_put(test_card)

# Search by name (free-text)
cards, total = client.search_cards(q="lightning")
assert total == 1
assert cards[0].name == "Lightning Bolt"

# Search by type + color
cards, total = client.search_cards(type_line="Creature", colors=["W"])
assert total >= 0  # Depends on cache contents

# Paginated search
cards, total = client.search_cards(per_page=10, page=2)
assert len(cards) <= 10

# Sort by cmc descending
cards, total = client.search_cards(sort_by="cmc", sort_order="desc")
if len(cards) > 1:
    assert cards[0].cmc >= cards[1].cmc
```

### Sample Testing Code (Card Search API — pytest)
```python
import pytest
from mtg_engine.card_data.scryfall import ScryfallClient
from fastapi.testclient import TestClient
from mtg_engine.api.main import app

@pytest.fixture
def search_client(tmp_path):
    """ScryfallClient with empty cache for isolated tests."""
    return ScryfallClient(db_path=tmp_path / "search_cache.db")

@pytest.fixture
def populated_cache(search_client):
    """Populate cache with known test cards."""
    test_cards = [
        {"id": "t-001", "name": "Lightning Bolt", "mana_cost": "{R}",
         "type_line": "Instant", "oracle_text": "Deals 3 damage to any target.",
         "colors": ["R"], "cmc": 1.0, "keywords": [],
         "rarity": "uncommon", "set": "MOM"},
        {"id": "t-002", "name": "Avacyn's Pilgrim", "mana_cost": "{W}",
         "type_line": "Creature — Human Cleric",
         "oracle_text": "Flying, Whenever Avacyn's Pilgrim enters...",
         "colors": ["W"], "cmc": 1.0, "keywords": ["flying"],
         "rarity": "common", "set": "AVR"},
    ]
    for card in test_cards:
        search_client._cache_put(card)
    return search_client

class TestSearchEngine:
    def test_free_text_search_by_name(self, populated_cache):
        cards, total = populated_cache.search_cards(q="lightning")
        assert total == 1
        assert cards[0].name == "Lightning Bolt"

    def test_filter_by_type(self, populated_cache):
        cards, total = populated_cache.search_cards(type_line="Creature")
        assert all("Creature" in c.type_line for c in cards)

    def test_empty_cache_returns_zero(self, search_client):
        cards, total = search_client.search_cards(q="anything")
        assert cards == []
        assert total == 0

class TestSearchAPI:
    def test_search_endpoint_returns_paginated_result(self):
        client = TestClient(app)
        resp = client.get("/cards/search", params={"q": "lightning"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "cards" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_invalid_sort_field_returns_400(self):
        client = TestClient(app)
        resp = client.get("/cards/search", params={"sort_by": "invalid"})
        assert resp.status_code == 400

    def test_negative_page_returns_422(self):
        """Pydantic validation rejects negative page."""
        client = TestClient(app)
        resp = client.get("/cards/search", params={"page": -1})
        assert resp.status_code in (400, 422)

    def test_combined_filters_and_logic(self, populated_cache):
        """Type=Instant AND colors=R should only match red instants."""
        # This test depends on cache contents — adjust as needed
        cards, total = populated_cache.search_cards(
            type_line="Instant", colors=["R"]
        )
        for c in cards:
            assert "Instant" in c.type_line
            assert "R" in c.colors
```

## Sample Testing Code (pytest — Format Validation)
```python
import pytest
from mtg_engine.models.game import Card
from mtg_engine.engine.formats.banned import is_banned, is_restricted
from mtg_engine.engine.formats import validate_deck


def _make_card(name="Test Card", rarity=None, set_code=None):
    return Card(name=name, rarity=rarity, set_code=set_code)


class TestBannedLookups:
    def test_known_banned(self):
        # Use a card that's actually on the banned list
        assert is_banned("Known Banned Card", "modern") is True

    def test_legal_card_not_banned(self):
        assert is_banned("Basic Island", "modern") is False

    def test_case_insensitive(self):
        result_lower = is_banned("known banned card".lower(), "modern")
        result_upper = is_banned("KNOWN BANNED CARD".upper(), "modern")
        assert result_lower == result_upper


class TestFormatValidation:
    def test_unknown_format(self):
        is_valid, violations = validate_deck([], "nonexistent")
        assert is_valid is False
        assert len(violations) > 0

    def test_standard_min_size(self):
        cards = [_make_card(f"C{i}") for i in range(59)]
        is_valid, violations = validate_deck(cards, "standard")
        assert is_valid is False
        assert any("60" in v or "minimum" in v.lower() for v in violations)

    def test_pauper_rejects_rare(self):
        cards = [_make_card(f"C{i}", rarity="c") for i in range(60)]
        cards.append(_make_card("Rare Card", rarity="r"))
        is_valid, violations = validate_deck(cards, "pauper")
        assert is_valid is False

    def test_brawl_commander_type(self):
        bad_cmd = Card(name="Bad Cmd", type_line="Legendary Enchantment")
        cards = [bad_cmd] + [_make_card(f"C{i}") for i in range(59)]
        is_valid, violations = validate_deck(cards, "brawl", commanders=[bad_cmd])
        assert is_valid is False

    def test_vintage_restricted_max_one(self):
        # Requires a card on the restricted list with 2+ copies
        pass  # Covered when restricted list has entries


class TestAPIEndpoint:
    """Integration tests for POST /deck/validate."""

    def test_validate_returns_result(self):
        from fastapi.testclient import TestClient
        from mtg_engine.api.main import app
        client = TestClient(app)

        resp = client.post("/deck/validate", json={
            "format": "standard",
            "cards": [{"name": f"Card {i}"} for i in range(60)],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "valid" in data
        assert "violations" in data

    def test_unknown_format_returns_400(self):
        from fastapi.testclient import TestClient
        from mtg_engine.api.main import app
        client = TestClient(app)

        resp = client.post("/deck/validate", json={
            "format": "nonexistent",
            "cards": [],
        })
        assert resp.status_code == 400
```

## Deck Building AI Coding Standards (APP-02)
- **Pipeline architecture**: Filter → Score → Select → Validate. Each stage is a pure function that takes inputs and returns outputs without side effects. No GameState dependency — operates on raw `Card` objects only.
- **Baseline scoring reuse**: Always call `estimate_card_quality(card.model_dump())` from `card_eval.py` for baseline quality (0-10 range). Never modify card_eval.py; wrap it with strategy-aware multipliers in deck_builder.py.
- **Strategy weights are hardcoded tables**: `STRATEGY_WEIGHTS[strategy][category] -> float`. Categories: `creature_low`, `creature_mid`, `creature_high`, `removal`, `counterspell`, `draw`, `ramp`, `board_wipe`, `land`, `other`. Strategies: `aggro`, `control`, `midrange`, `combo`.
- **CMC curve targeting**: Applied as a multiplicative bonus (1.0x-1.3x) on top of strategy weights. Aggro favors CMC<=2, Control favors CMC 3-5, Midrange favors CMC 2-4, Combo favors CMC>=3.
- **Composite score formula**: `baseline_quality × strategy_multiplier × cmc_curve_bonus`. All three factors are floats >= 0.
- **Deterministic tie-breaking**: Use `random.Random(seed)` where seed is derived from `(format + strategy + sorted card pool names)` hash by default. Users can override with explicit `seed` parameter.
- **Singleton enforcement in selection**: For Legacy/Vintage/Commander/Brawl, add max 1 copy of non-basic-land cards. Basic lands (Plains, Island, Swamp, Mountain, Forest, Snow-Covered variants, Wastes) are exempt.
- **Restricted enforcement** (Vintage): Max 1 copy of restricted cards during selection phase. Use `is_restricted(card.name)` from `mtg_engine/engine/formats/banned.py`.
- **Commander color identity**: For Commander/Brawl with `commander_names` provided, use `get_color_identity()` from `mtg_engine/engine/formats/commander.py`. Cards whose color identity is NOT a subset of the composite commander identity are excluded during filtering. Commanders themselves are always locked into the deck.
- **Land balancing**: After greedy selection, if fewer than 24% of selected cards are lands (type_line contains "Land"), fill remaining slots with highest-scored lands from pool up to 24%.
- **Sideboard construction**: For non-Commander/Brawl formats, select up to 15 best remaining legal cards after main deck is filled. Same singleton/restricted rules apply.
- **Validation before return**: Always run FMT-01 `validate_deck()` on the constructed deck. If validation fails, return errors in response rather than an invalid deck. Response always includes `validation` field with `valid: bool` and `violations: list[str]`.
- **Card input/output format**: Input is `list[Card]` (Pydantic models). Output is `list[DeckCardEntry]` where each entry has `{name: str, quantity: int}`. Group identical cards by name with quantity counts.

### Sample Backend Code (Deck Builder Engine)
```python
from mtg_engine.models.game import Card
from mtg_engine.ai.deck_builder import build_deck, filter_card_pool, score_cards

# Build a full deck from a card pool
pool = [Card(name="Lightning Bolt", mana_cost="{R}", type_line="Instant",
             oracle_text="Deals 3 damage to any target.", cmc=1.0, colors=["R"],
             color_identity=["R"]), ...]

result = build_deck(pool, "modern", "aggro", seed=42)
# result.deck: list[Card] — main deck cards (60+)
# result.sideboard: list[Card] — sideboard cards (up to 15)
# result.validation: dict with {valid: bool, violations: list[str], format: str}

# Filter stage only
filtered = filter_card_pool(pool, "modern")
assert all(not is_banned(c.name, "modern") for c in filtered)

# Score stage only
scored = score_cards(filtered, "aggro")
assert scored[0].composite_score >= scored[-1].composite_score  # Descending order
```

### Sample Testing Code (Deck Builder — pytest)
```python
import pytest
from mtg_engine.models.game import Card
from mtg_engine.ai.deck_builder import build_deck, filter_card_pool, score_cards

def _make_card(name: str, mana_cost: str = "{1}", type_line: str = "Creature — Beast",
               oracle_text: str = "", cmc: float = 1.0, colors: list[str] | None = None,
               color_identity: list[str] | None = None, keywords: list[str] | None = None,
               set_code: str | None = None, rarity: str | None = None) -> Card:
    return Card(
        name=name, mana_cost=mana_cost, type_line=type_line, oracle_text=oracle_text,
        cmc=cmc, colors=colors or [], color_identity=color_identity or [],
        keywords=keywords or [], set_code=set_code, rarity=rarity,
    )

def test_filter_removes_banned_cards():
    """Banned cards are excluded from the filtered pool."""
    pool = [
        _make_card("Legal Card", set_code="MOM"),
        _make_card("Bane of the Living", set_code="MOM"),  # Banned in Modern
    ]
    filtered = filter_card_pool(pool, "modern")
    names = {c.name for c in filtered}
    assert "Bane of the Living" not in names

def test_score_aggro_boosts_low_cmc():
    """Aggro strategy gives higher scores to low-CMC creatures."""
    low = _make_card("Goblin", cmc=1, type_line="Creature — Goblin")
    high = _make_card("Dragon", cmc=7, type_line="Creature — Dragon")
    
    scored_low = score_cards([low], "aggro")[0]
    scored_high = score_cards([high], "aggro")[0]
    
    assert scored_low.composite_score > scored_high.composite_score

def test_build_deck_full_pipeline():
    """End-to-end: pool → filter → score → select → validate."""
    pool = []
    for i in range(30):
        pool.append(_make_card(f"Creature {i}", cmc=2, mana_cost="{1}{R}",
                               type_line="Creature — Goblin", set_code="MOM"))
    for i in range(25):
        pool.append(_make_card(f"Mountain {i}", cmc=0, type_line="Land — Mountain", set_code="MOM"))
    
    result = build_deck(pool, "modern", "aggro", seed=42)
    assert len(result.deck) >= 60
    assert result.validation["valid"] is True

def test_deterministic_with_seed():
    """Same inputs + seed produce identical output."""
    pool = [_make_card(f"Card {i}", cmc=i % 5, set_code="MOM") for i in range(100)]
    
    r1 = build_deck(pool, "modern", "aggro", seed=42)
    r2 = build_deck(pool, "modern", "aggro", seed=42)
    
    assert [c.name for c in r1.deck] == [c.name for c in r2.deck]
```

## Game Replay Coding Standards (APP-03)
- **Stateless replay**: The replay engine does not track server-side session state. Clients pass `from_event_seq` to indicate position; the engine reconstructs board state from scratch per request.
- **Two-tier reconstruction**: Board state at any event uses snapshot anchors (full GameState serialized at priority grants) as starting points, then incrementally applies transcript events between the anchor and target seq for intermediate positions.
- **Engine purity**: Functions in `mtg_engine/export/replay_engine.py` take a `GameExportStore` and return structured dicts — no FastAPI dependencies, no side effects. The API router wraps these with HTTP semantics.
- **Snapshot fallback**: If no snapshot exists before the target event (very early game), start from minimal initial state (20 life each, empty battlefield) and replay all events from seq 1 to target.
- **Event types that affect board state**: `zone_change` (move card between zones), `life_change` (delta to player life), `damage` (marked damage on permanents), `draw` (hand size +1, library -1), `cast`/`resolve` (stack +/- 1). Other events are no-ops for reconstruction.
- **seq=0 convention**: Event sequence 0 means "before game starts" — returns initial board state with no event. Forward from 0 yields event seq 1. Backward from 0 returns HTTP 400.
- **Response wrapping**: All endpoints return `{"data": ...}` on success, matching existing API conventions. Errors use `HTTPException(status_code=..., detail={"error": str, "error_code": str})`.

### Sample Backend Code (Replay Engine)
```python
from mtg_engine.export.replay_engine import get_replay_info, step_to_event, build_timeline
from mtg_engine.export.store import get_export_store

# Get replay metadata
store = get_export_store("game-abc-123")
if store is None:
    raise HTTPException(404)

info = get_replay_info(store)
# {"game_id": "game-abc-123", "total_events": 147, "turns": 12, ...}

# Step forward one event from current position
event, board_state = step_to_event(store, "forward", from_seq=5)
# event: dict with seq, event_type, description, data, turn, phase, step
# board_state: dict with battlefield, player_life, hand_sizes, graveyard_top, stack_size

# Build condensed timeline for navigation
timeline = build_timeline(store)
# [{"turn": 1, "phase": "beginning", "step": "upkeep", "event_count": 3, ...}, ...]
```

### Sample Testing Code (Replay API — pytest)
```python
import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    get_manager()._games.clear()
    export_store.clear()
    yield
    get_manager()._games.clear()
    export_store.clear()

def _create_game(seed: int = 1) -> str:
    resp = client.post("/game", json={
        "player1_name": "p1", "player2_name": "p2",
        "deck1": ["Forest"] * 60, "deck2": ["Forest"] * 60,
        "seed": seed,
    })
    assert resp.status_code == 200
    return resp.json()["data"]["game_id"]

def test_replay_info_returns_metadata():
    game_id = _create_game()
    # Advance game to generate transcript entries...
    resp = client.get(f"/replay/{game_id}/info")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_events" in data

def test_step_forward():
    game_id = _create_game()
    # Advance game...
    resp = client.post(f"/replay/{game_id}/step", json={
        "direction": "forward", "from_event_seq": 0,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["to_seq"] == 1

def test_replay_404_deleted_game():
    game_id = _create_game()
    client.delete(f"/game/{game_id}")
    resp = client.get(f"/replay/{game_id}/info")
    assert resp.status_code == 404
```

## Draft / Sealed Simulation Coding Standards (APP-05)
- **Stateless engine + in-memory session store**: Core draft/sealed logic (`mtg_engine/ai/draft.py`) is pure-function based. A module-level `_draft_sessions: dict[str, DraftSession]` tracks active sessions — mirroring `GameManager` singleton pattern but scoped to draft operations only. No GameState dependency, no transcript/recorder wiring needed.
- **Pack generation via Scryfall SQLite cache**: Use `ScryfallClient.search_cards(set_code=..., per_page=100)` to fetch all cards in a set from the local SQLite cache. If fewer than 50 cards found (set not loaded), fall back to randomized format-legal pool from entire cache. Each pack is exactly 15 cards with rarity-weighted distribution (common ~80%, uncommon ~15%, rare ~4.5%, mythic ~0.5%).
- **Pack deduplication**: Standard limited rules — no duplicate card names within a single pack. When generating packs, track used names and skip duplicates (keeping one copy per unique name).
- **Draft passing rules**: Odd rounds pass left (index +1 mod N), even rounds pass right (index -1 mod N). Generalizes to any player count >= 2. Each round, every player picks exactly 1 card from the pack currently in front of them.
- **Bot auto-pick scoring**: Composite score = `estimate_card_quality() × strategy_multiplier + color_synergy_bonus + cmc_curve_fit`. Color synergy: +1.0 per matching color in already-drafted cards' color identity. CMC curve fit: bonus if card's CMC fills a gap in the drafted pool's curve. Strategy parameter influences category weighting via `STRATEGY_WEIGHTS` from deck_builder.py.
- **Post-draft deck construction**: After all picks complete, each player's drafted pool is passed to APP-02's `build_deck(card_pool, format_name="standard", strategy=...)`. This reuses the proven Filter→Score→Select→Validate pipeline without duplicating logic.
- **Sealed mode**: Generates one 15-card pack per player and immediately builds decks via APP-02. No pick orchestration needed; session goes straight to BUILDING → COMPLETE phase.
- **Session lifecycle**: `PICKING` (active picks) → `BUILDING` (post-pick deck construction) → `COMPLETE` (results ready). Human players can only pick during `PICKING`; attempts during other phases return HTTP 409 Conflict.
- **Error handling**: Invalid session_id → HTTP 404; illegal pick (card not in available pack, wrong player turn) → HTTP 400/409; set not found and cache empty → fallback pool with `pack_source: "fallback"` metadata in response.

### Sample Backend Code (Draft Engine)
```python
from mtg_engine.ai.draft import create_draft_session, make_pick, bot_auto_pick, complete_draft
from mtg_engine.models.game import Card

# Create a 4-player draft session from set MOM
session = create_draft_session(
    players=["Alice", "Bob", "Charlie", "Diana"],
    packs_per_player=3,
    set_code="MOM",
    format="standard",
    human_player_name="Alice",
)

# Get current pick order for round 1 (odd → pass left)
pick_order = get_pick_order(1, num_players=4)
assert pick_order == [0, 1, 2, 3]  # Alice picks first from her pack

# Human player makes a pick
session = make_pick(session.session_id, "Alice", "Lightning Bolt")

# Bot players auto-pick remaining cards in the round
for idx in pick_order[1:]:
    session = bot_auto_pick(session.session_id, idx)

# After all rounds complete, build decks
results = complete_draft(session.session_id)
assert results["phase"] == "complete"
for player_result in results["players"]:
    assert len(player_result["deck"]) > 0  # Each player has a constructed deck
```

### Sample Testing Code (Draft — pytest)
```python
import pytest
from mtg_engine.ai.draft import create_draft_session, make_pick, bot_auto_pick, complete_draft
from mtg_engine.models.game import Card

def _make_card(name: str, mana_cost: str = "{1}", type_line: str = "Creature",
               cmc: float = 1.0, colors: list[str] | None = None, set_code: str = "MOM",
               rarity: str = "common") -> Card:
    return Card(
        name=name, mana_cost=mana_cost, type_line=type_line, oracle_text="",
        cmc=cmc, colors=colors or [], color_identity=[], keywords=[],
        set_code=set_code, rarity=rarity,
    )

class TestPackGeneration:
    def test_generate_pack_returns_15_cards(self):
        """Pack generation produces exactly 15 cards from specified set."""
        from mtg_engine.ai.draft import _generate_pack
        import random
        rng = random.Random(42)
        pack = _generate_pack("MOM", rng)
        assert len(pack) == 15

    def test_generate_pack_no_duplicate_names(self):
        """No duplicate card names within a single pack."""
        from mtg_engine.ai.draft import _generate_pack
        import random
        rng = random.Random(42)
        pack = _generate_pack("MOM", rng)
        names = [c.name for c in pack]
        assert len(names) == len(set(names))

class TestPickOrder:
    def test_odd_round_passes_left(self):
        """Round 1 (odd) passes left — pick order is index +1 mod N."""
        from mtg_engine.ai.draft import get_pick_order
        order = get_pick_order(1, num_players=4)
        assert order == [0, 1, 2, 3]

    def test_even_round_passes_right(self):
        """Round 2 (even) passes right — pick order is reversed."""
        from mtg_engine.ai.draft import get_pick_order
        order = get_pick_order(2, num_players=4)
        assert order == [3, 2, 1, 0]

class TestBotAutoPick:
    def test_bot_picks_highest_scored_card(self):
        """Bot selects the card with highest draft score from available pack."""
        # Setup session with known cards in bot's pack...
        pass  # Full implementation in tests/ai/test_draft.py

    def test_bot_considers_color_synergy(self):
        """Cards matching drafted colors receive higher scores."""
        # Bot has drafted red cards; a new red card should score higher than a blue card of equal base quality
        pass

class TestSealedMode:
    def test_sealed_generates_pool_and_deck(self):
        """Sealed mode produces pool + deck for each player."""
        from mtg_engine.ai.draft import create_sealed_session
        session = create_sealed_session(
            players=["Alice", "Bob"], set_code="MOM", format="standard"
        )
        assert len(session.pools["Alice"]) == 15
        assert session.results is not None

class TestAPIEndpoints:
    def test_draft_start_returns_session_id(self):
        from fastapi.testclient import TestClient
        from mtg_engine.api.main import app
        client = TestClient(app)
        resp = client.post("/ai/draft/start", json={
            "players": ["Alice", "Bob"],
            "packs_per_player": 3,
            "set_code": "MOM",
            "format": "standard",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "session_id" in data

    def test_invalid_session_returns_404(self):
        from fastapi.testclient import TestClient
        from mtg_engine.api.main import app
        client = TestClient(app)
        resp = client.get("/ai/draft/nonexistent-id/state")
        assert resp.status_code == 404

    def test_sealed_start_returns_complete_results(self):
        from fastapi.testclient import TestClient
        from mtg_engine.api.main import app
        client = TestClient(app)
        resp = client.post("/ai/sealed/start", json={
            "players": ["Alice"],
            "set_code": "MOM",
            "format": "standard",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["players"]) == 1
        assert "deck" in data["players"][0]


## WebSocket Spectator Coding Standards (APP-04)
- **No new dependencies**: FastAPI has native `WebSocket` support. Use `from fastapi import WebSocket` — no external packages needed.
- **Pub/Sub via TranscriptRecorder listeners**: Each connected WebSocket client registers its own listener callback on the game's `TranscriptRecorder`. When a transcript event fires, all registered listeners are notified and the event is pushed to each client's outgoing queue. No engine code modifications required beyond adding `unregister_listener()` for cleanup.
- **Per-connection asyncio.Queue**: Each WebSocket connection gets its own `asyncio.Queue[dict]`. The per-connection listener pushes to that specific queue via `queue.put_nowait()`. This isolates slow clients from fast ones and makes cleanup trivial — just close the websocket and drop the queue.
- **Sync→Async bridging pattern**: Listener callbacks run synchronously (called from `_notify_listeners` which iterates the listeners list). They use `queue.put_nowait()` to push events into an async queue, decoupling the sync engine thread from the async WebSocket send loop. The main event loop drains the queue with `await queue.get()`. Never call `websocket.send_text()` directly from a listener callback — it's async and would deadlock.
- **Connection registry**: Module-level `_spectators: dict[str, set[SpectatorConnection]]` in the router file manages all active connections. `SpectatorConnection` is a lightweight dataclass holding the WebSocket, its queue, and the listener callback reference (needed for cleanup).
- **Initial state on connect**: Send `{ type: "initial_state", data: <GameState.model_dump()> }` immediately after accepting the connection. This gives late-joining spectators a complete starting point without needing to replay the entire transcript.
- **Event message format**: All broadcast events use consistent JSON structure: `{ type: "<event_type>", data: {...}, timestamp: float, seq: int, turn: int, phase: str, step: str }`. The `type` field matches TranscriptEntry event types (`cast`, `resolve`, `trigger`, `sba`, `zone_change`, `damage`, `phase_change`, `priority_grant`).
- **Game-end detection**: After receiving each event from the queue, check if the game is over by querying `GameManager.get(game_id).is_game_over`. If true, send `{ type: "game_end", data: { winner: str, loser: str }, timestamp: float }` and close with code 1000 (Normal Closure). Also handle `KeyError` from deleted games the same way.
- **Heartbeat**: Background `asyncio.create_task(_heartbeat(conn))` per connection sends `{ type: "ping" }` every 30 seconds. Tracks pong responses via `conn.pong_received_at = time.monotonic()`. If no pong arrives within 15 seconds, closes with code 1001 (Going Away).
- **Read-only access**: Spectator WebSocket is read-only — incoming non-pong messages are silently ignored. No game actions can be taken via the spectator endpoint.
- **Error handling for invalid games**: Reject during WebSocket handshake before `accept()`: close with code 4004 and reason string ("Game not found" or "Game already completed"). This produces an HTTP 404-equivalent at the WebSocket layer.
- **Graceful disconnect cleanup**: Use `try/finally` pattern to guarantee cleanup regardless of how the connection terminates: cancel heartbeat task, unregister listener via `recorder.unregister_listener(conn.listener_fn)`, remove from registry with `_spectators[game_id].discard(conn)`.
- **Critical fix — TranscriptRecorder needs `unregister_listener()`**: The class has `register_listener(fn)` but no corresponding unregistration. Add following the exact pattern from `SnapshotRecorder` and `DebugLogRecorder`:

```python
def unregister_listener(self, fn: Callable[["TranscriptEntry"], None]) -> None:
    """Remove a previously registered listener. No-op if not found."""
    try:
        self._listeners.remove(fn)
    except ValueError:
        pass
```

### Sample Backend Code (WebSocket Spectator Router)
```python
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import get_export_store
from mtg_engine.export.transcript import TranscriptEntry

router = APIRouter()

@dataclass
class SpectatorConnection:
    ws: WebSocket
    queue: asyncio.Queue[dict]
    listener_fn: Callable[[TranscriptEntry], None]
    game_id: str
    pong_received_at: float = field(default_factory=time.monotonic)

# Module-level registry: game_id -> set of connections
_spectators: dict[str, set[SpectatorConnection]] = {}

async def _heartbeat(conn: SpectatorConnection) -> None:
    """Background task: send ping every 30s, close if no pong within 15s."""
    while True:
        try:
            await asyncio.sleep(30)
            await conn.ws.send_text(json.dumps({"type": "ping"}))
            if time.monotonic() - conn.pong_received_at > 15:
                await conn.ws.close(code=1001)
                return
        except Exception:
            return

@router.websocket("/ws/game/{game_id}")
async def ws_game_spectate(websocket: WebSocket, game_id: str):
    # Validate game exists and is active
    try:
        gs = get_manager().get(game_id)
    except KeyError:
        await websocket.close(code=4004, reason="Game not found")
        return

    if gs.is_game_over:
        await websocket.close(code=4004, reason="Game already completed")
        return

    await websocket.accept()

    # Setup per-connection queue and listener
    store = get_export_store(game_id)
    recorder = store.transcript
    queue: asyncio.Queue[dict] = asyncio.Queue()

    def _listener(entry: TranscriptEntry) -> None:
        queue.put_nowait({
            "type": entry.event_type,
            "data": entry.data,
            "timestamp": time.time(),
            "seq": entry.seq,
            "turn": entry.turn,
            "phase": entry.phase,
            "step": entry.step,
        })

    recorder.register_listener(_listener)
    conn = SpectatorConnection(ws=websocket, queue=queue, listener_fn=_listener, game_id=game_id)
    _spectators.setdefault(game_id, set()).add(conn)

    # Send initial state
    await websocket.send_text(json.dumps({
        "type": "initial_state",
        "data": gs.model_dump(),
    }))

    heartbeat_task = asyncio.create_task(_heartbeat(conn))

    try:
        while True:
            msg = await queue.get()
            await websocket.send_text(json.dumps(msg))

            # Check game-over after each event
            try:
                current_gs = get_manager().get(game_id)
                if current_gs.is_game_over:
                    await websocket.send_text(json.dumps({
                        "type": "game_end",
                        "data": {"winner": current_gs.winner},
                        "timestamp": time.time(),
                    }))
                    break
            except KeyError:
                # Game deleted — treat as end
                break

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        recorder.unregister_listener(conn.listener_fn)
        _spectators.get(game_id, set()).discard(conn)
```

### Sample Testing Code (WebSocket Spectator — pytest)
```python
import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store, get_export_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    """Clear all games and spectator registry before each test."""
    get_manager()._games.clear()
    get_manager()._recorders.clear()
    export_store.clear()
    from mtg_engine.api.routers.spectate import _spectators
    _spectators.clear()
    yield
    get_manager()._games.clear()
    get_manager()._recorders.clear()
    export_store.clear()
    from mtg_engine.api.routers.spectate import _spectators
    _spectators.clear()

def _create_game(seed: int = 1) -> str:
    """Create a game and return its ID."""
    resp = client.post("/game", json={
        "player1_name": "p1", "player2_name": "p2",
        "deck1": ["Forest"] * 60, "deck2": ["Forest"] * 60,
        "seed": seed,
    })
    assert resp.status_code == 200
    return resp.json()["data"]["game_id"]

def test_connect_sends_initial_state():
    """WebSocket connection receives initial game state on connect."""
    game_id = _create_game()
    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        assert data["data"]["game_id"] == game_id

def test_event_broadcasting_during_gameplay():
    """Transcript events are broadcast to connected WebSocket clients."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        ws.receive_json()  # initial state

        # Manually record a transcript event
        recorder.record_cast("p1", "Lightning Bolt", ["p2"], turn=1, phase="combat", step="declare_attackers")
        import time; time.sleep(0.1)

        data = ws.receive_json()
        assert data["type"] == "cast"
        assert data["data"]["card_name"] == "Lightning Bolt"

def test_multiple_spectators_receive_events():
    """Multiple WebSocket clients all receive the same broadcasted events."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript

    with client.websocket_connect(f"/ws/game/{game_id}") as ws1, \
         client.websocket_connect(f"/ws/game/{game_id}") as ws2:
        ws1.receive_json()  # initial state
        ws2.receive_json()  # initial state

        recorder.record_damage("Lightning Bolt", "p2", 3, turn=1, phase="combat", step="declare_attackers")
        import time; time.sleep(0.1)

        data1 = ws1.receive_json()
        data2 = ws2.receive_json()
        assert data1["type"] == "damage" and data2["type"] == "damage"

def test_nonexistent_game_rejected():
    """Connecting to a non-existent game rejects the WebSocket handshake."""
    with pytest.raises(Exception):  # TestClient raises on failed handshake
        with client.websocket_connect("/ws/game/nonexistent-id"):
            pass

def test_disconnect_cleanup_removes_listener():
    """When a spectator disconnects, their listener is unregistered."""
    game_id = _create_game()
    recorder = get_export_store(game_id).transcript
    from mtg_engine.api.routers.spectate import _spectators

    with client.websocket_connect(f"/ws/game/{game_id}") as ws:
        ws.receive_json()  # initial state
        assert game_id in _spectators
        listener_fn = list(_spectators[game_id])[0].listener_fn
        assert listener_fn in recorder._listeners

    # After disconnect, listener should be unregistered
    assert listener_fn not in recorder._listeners
```

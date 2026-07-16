# Design: APP-01 Card Search API

## Overview
A `GET /cards/search` REST endpoint that queries the local SQLite Scryfall cache with multiple filters (name, type, color, cmc range, keyword, rarity, set_code) and returns paginated results. No network calls — reads only from cached data.

## User Story Reference
`.opencode/discovery/story-app01-card-search.md`

---

## Architecture Decisions

### 1. Search logic lives in `ScryfallClient.search_cards()`
**Decision**: Add a new method to the existing `ScryfallClient` class rather than creating a separate search module. The ScryfallClient already owns the SQLite connection, schema knowledge, and `_build_card()` mapping — duplicating this would create inconsistency.

**Trade-offs considered**:
- Separate `CardSearchEngine` class: Would isolate concerns but duplicate DB access logic and card building. Over-engineered for a single-table query.
- Raw SQL in API router: Violates separation of concerns; the router should not know about SQLite internals.

### 2. Two-query pagination (COUNT + SELECT)
**Decision**: Execute a separate `SELECT COUNT(*)` query before the paginated `SELECT ... LIMIT/OFFSET`. This gives accurate total count for UI pagination controls.

**Trade-offs considered**:
- `SQLITE_OFFSETS` / `LIMIT -1` trick: SQLite doesn't expose row counts after LIMIT. Would require client-side estimation which breaks "showing 1-25 of 847" UX.
- Single query with window functions (`COUNT(*) OVER()`): Returns total on every row — wasteful for large result sets.

### 3. SQLite `json_extract()` for filtering
**Decision**: Use SQLite's built-in JSON functions (available since 3.9, our Python 3.11 ships with 3.38+) to filter directly in SQL without schema migration. Card data is stored as a single `data_json` blob — we extract fields at query time.

**Trade-offs considered**:
- Add columns to SQLite schema: Would require migration logic and break existing caches. Not worth it for read-only search.
- Load all cards into memory and filter in Python: O(N) scan of entire cache, terrible for large caches (20k+ cards).

### 4. Case-insensitive LIKE for free-text search
**Decision**: Use SQLite `LIKE` with `%` wildcards on both `name` and `json_extract(data_json, '$.oracle_text')`. SQLite's default collation is case-insensitive for ASCII.

**Trade-offs considered**:
- FTS5 full-text index: Would be faster but requires schema migration and ongoing maintenance. Substring LIKE is sufficient for MVP (<100ms on typical caches).
- Trigram/GIN indexes: PostgreSQL feature, not available in SQLite without extensions.

### 5. AND logic for combined filters
**Decision**: All query parameters combine with AND (e.g., `type=Creature&colors=W&cmc_max=3` returns white creatures with CMC ≤ 3). This matches user mental model and Scryfall's own search behavior.

---

## API Contract

### Endpoint
```
GET /cards/search
```

### Query Parameters
| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `q` | string | — | — | Free-text search (matches name + oracle_text) |
| `type` | string | — | — | Card type substring match (e.g., "Creature", "Instant") |
| `colors` | string | — | Comma-separated single letters: W,U,B,R,G,C | Filter by card colors (AND logic — must have ALL specified colors) |
| `cmc_min` | float | — | ≥ 0 | Minimum converted mana cost |
| `cmc_max` | float | — | ≥ 0 | Maximum converted mana cost |
| `mana_cost` | string | — | — | Exact mana cost match (e.g., "{2}{R}") |
| `keyword` | string | — | — | Card must have this keyword (case-insensitive) |
| `rarity` | string | — | c, u, r, m, mythical, special | Filter by rarity |
| `set_code` | string | — | 3-letter code | Filter by set |
| `page` | int | 1 | ≥ 1 | Page number (1-indexed) |
| `per_page` | int | 25 | 1–100 | Results per page |
| `sort_by` | string | "name" | "name", "cmc" | Sort field |
| `sort_order` | string | "asc" | "asc", "desc" | Sort direction |

### Response Format (200 OK)
```json
{
  "data": {
    "cards": [
      {
        "scryfall_id": "...",
        "name": "Lightning Bolt",
        "mana_cost": "{R}",
        "type_line": "Instant",
        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
        "colors": ["R"],
        "cmc": 1.0,
        "keywords": [],
        "rarity": "uncommon",
        "set_code": "MOM"
      }
    ],
    "total": 847,
    "page": 1,
    "per_page": 25
  }
}
```

### Error Responses (400 Bad Request)
```json
{
  "detail": {
    "error": "Invalid sort_by field: 'power'. Must be one of: name, cmc",
    "error_code": "INVALID_SORT_FIELD"
  }
}
```

---

## Database Query Strategy

### Base Query Template
```sql
SELECT data_json FROM cards WHERE <filters> ORDER BY <sort> LIMIT ? OFFSET ?
```

### Filter Clauses (AND combined)
| Filter | SQL Clause |
|--------|-----------|
| `q` (free-text) | `(LOWER(name) LIKE '%' || LOWER(?) || '%' OR LOWER(json_extract(data_json, '$.oracle_text')) LIKE '%' || LOWER(?) || '%')` |
| `type` | `json_extract(data_json, '$.type_line') LIKE '%?%'` |
| `colors` (AND logic) | For each color: `json_extract(data_json, '$.colors') LIKE '%"W"%'` — card must contain ALL specified colors |
| `cmc_min` | `CAST(json_extract(data_json, '$.cmc') AS REAL) >= ?` |
| `cmc_max` | `CAST(json_extract(data_json, '$.cmc') AS REAL) <= ?` |
| `mana_cost` | `json_extract(data_json, '$.mana_cost') = ?` |
| `keyword` | `LOWER(json_extract(data_json, '$.keywords')) LIKE '%?%'` — keywords stored as array in JSON; we search the stringified representation |
| `rarity` | `LOWER(json_extract(data_json, '$.rarity')) = LOWER(?)` |
| `set_code` | `json_extract(data_json, '$.set') = ?` |

### Sorting
```sql
-- Default: name ascending
ORDER BY name ASC

-- By cmc descending
ORDER BY CAST(json_extract(data_json, '$.cmc') AS REAL) DESC
```

### Count Query
Same WHERE clause, but `SELECT COUNT(*) FROM cards WHERE <filters>` (no ORDER BY, no LIMIT).

---

## Files to Create/Modify

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `mtg_engine/api/routers/card_search.py` | FastAPI router for card search | Request validation, query parameter parsing, response formatting, error handling |
| `tests/api/test_card_search.py` | API integration tests | Test endpoint with real SQLite cache, verify filters, pagination, errors |

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/card_data/scryfall.py` | Add `search_cards()` method + `_build_search_card()` helper | Core search logic: build SQL query from params, execute COUNT + SELECT, return Card models |
| `mtg_engine/api/main.py` | Import and mount `card_search_router` | Wire new endpoint into FastAPI app |

---

## Implementation Details

### ScryfallClient.search_cards() Method Signature
```python
def search_cards(
    self,
    q: Optional[str] = None,
    type_line: Optional[str] = None,
    colors: Optional[list[str]] = None,
    cmc_min: Optional[float] = None,
    cmc_max: Optional[float] = None,
    mana_cost: Optional[str] = None,
    keyword: Optional[str] = None,
    rarity: Optional[str] = None,
    set_code: Optional[str] = None,
    page: int = 1,
    per_page: int = 25,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[Card], int]:
    """Search cached cards. Returns (cards, total_count)."""
```

### ScryfallClient._build_search_card() Helper
A lightweight version of `_build_card()` that only extracts fields needed for search results (no faces, no uuid generation — uses scryfall_id as id):
```python
def _build_search_card(self, raw: dict) -> Card:
    """Build minimal Card from cached JSON for search results."""
    return Card(
        id=raw.get("id", ""),
        scryfall_id=raw.get("id"),
        name=raw.get("name", ""),
        mana_cost=raw.get("mana_cost"),
        type_line=raw.get("type_line", ""),
        oracle_text=raw.get("oracle_text"),
        colors=raw.get("colors", []),
        color_identity=raw.get("color_identity", []),
        keywords=[k.lower() for k in raw.get("keywords", [])],
        cmc=float(raw.get("cmc", 0.0)),
        rarity=raw.get("rarity"),
        set_code=raw.get("set"),
    )
```

### Router Request Model
```python
class CardSearchRequest(BaseModel):
    q: Optional[str] = None
    type: Optional[str] = Field(default=None, alias="type")
    colors: Optional[str] = None  # comma-separated string from query param
    cmc_min: Optional[float] = None
    cmc_max: Optional[float] = None
    mana_cost: Optional[str] = None
    keyword: Optional[str] = None
    rarity: Optional[str] = None
    set_code: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
    sort_by: str = Field(default="name")
    sort_order: str = Field(default="asc")

class CardSearchResult(BaseModel):
    cards: list[Card]
    total: int
    page: int
    per_page: int
```

### Router Endpoint
```python
@router.get("/cards/search", tags=["card-search"])
def search_cards_endpoint(params: CardSearchRequest = Depends()):
    # Validate sort_by, sort_order, colors format
    # Parse colors from comma-separated string to list
    # Call ScryfallClient().search_cards(...)
    # Return formatted response
```

---

## Task Breakdown (Ordered by Dependency)

### Task 1: Add `search_cards()` to ScryfallClient
- **Files**: `mtg_engine/card_data/scryfall.py`
- **Description**: Implement the core search method that builds SQL queries from parameters, executes COUNT + SELECT against SQLite cache, and returns Card models. Include `_build_search_card()` helper for lightweight card construction.
- **Acceptance Criteria**:
  - Method accepts all filter parameters defined in API contract
  - Returns `(list[Card], int)` tuple (cards, total count)
  - Uses parameterized queries to prevent SQL injection
  - Handles empty cache gracefully (returns `([], 0)`)
  - Free-text search matches both name and oracle_text case-insensitively

### Task 2: Create Card Search API Router
- **Files**: `mtg_engine/api/routers/card_search.py`
- **Description**: FastAPI router with request validation, parameter parsing, error handling, and response formatting. Uses Pydantic models for input/output validation.
- **Acceptance Criteria**:
  - `GET /cards/search` endpoint accepts all query parameters
  - Returns HTTP 400 for invalid parameters (negative page/per_page, unknown sort field, bad colors format)
  - Returns paginated response with total count
  - Colors parameter parsed from comma-separated string to list

### Task 3: Wire Router into FastAPI App
- **Files**: `mtg_engine/api/main.py`
- **Description**: Import and mount the new card_search router alongside existing routers.
- **Acceptance Criteria**:
  - Endpoint accessible at `/cards/search`
  - No conflicts with existing routes

### Task 4: Write Tests
- **Files**: `tests/api/test_card_search.py`
- **Description**: Comprehensive test suite covering all acceptance criteria. Use `tmp_path` fixture for isolated SQLite cache, populate with known test cards via `_cache_put()`.
- **Acceptance Criteria**: ≥8 tests covering:
  1. Free-text search by name (single filter)
  2. Filter by type line
  3. Filter by colors
  4. CMC range filtering (min + max)
  5. Combined filters (AND logic)
  6. Pagination (page 1, page 2, empty last page)
  7. Sorting (by name asc/desc, by cmc asc/desc)
  8. Empty cache returns `([], 0)`
  9. HTTP 400 for invalid parameters
  10. Keyword filter

---

## Data Models / Interfaces

### Pydantic Request Model
```python
class CardSearchRequest(BaseModel):
    q: Optional[str] = None
    type: Optional[str] = Field(default=None)
    colors: Optional[str] = None          # "W,U" or "R,G" — parsed to list in endpoint
    cmc_min: Optional[float] = None
    cmc_max: Optional[float] = None
    mana_cost: Optional[str] = None       # "{2}{R}"
    keyword: Optional[str] = None         # "flying"
    rarity: Optional[str] = None          # "c", "u", "r", "m"
    set_code: Optional[str] = None        # "MOM"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)
    sort_by: str = Field(default="name")  # "name" or "cmc"
    sort_order: str = Field(default="asc") # "asc" or "desc"

    class Config:
        populate_by_name = True
```

### Pydantic Response Model
```python
class CardSearchResult(BaseModel):
    cards: list[Card]
    total: int
    page: int
    per_page: int
```

---

## Testing Strategy

### Unit Tests (ScryfallClient.search_cards)
- **Empty cache**: Returns `([], 0)` for any query
- **Single card, exact match**: Search by name returns the card
- **Free-text partial match**: "lightning" matches "Lightning Bolt" in name and oracle_text
- **Type filter**: `type="Creature"` only returns creatures
- **Color filter**: `colors=["W"]` only returns white cards; `colors=["W","U"]` requires BOTH colors (AND logic)
- **CMC range**: `cmc_min=2, cmc_max=4` filters correctly
- **Mana cost exact match**: `mana_cost="{R}"` matches only `{R}` cards
- **Keyword filter**: `keyword="flying"` matches cards with flying keyword
- **Pagination**: 100 cards cached, page=1/per_page=25 returns 25 cards and total=100
- **Sorting**: Verify name asc/desc and cmc asc/desc ordering

### API Integration Tests (GET /cards/search)
- **Happy path**: Query with valid params returns 200 with correct structure
- **Empty results**: Query that matches nothing returns `{"cards": [], "total": 0}`
- **Invalid sort_by**: Returns HTTP 400
- **Negative page**: Returns HTTP 400 (Pydantic validation)
- **per_page > 100**: Returns HTTP 400 (Pydantic validation)
- **Combined filters**: Multiple params work together with AND logic

### Test Fixtures
```python
@pytest.fixture
def search_client(tmp_path):
    """ScryfallClient with empty cache for isolated tests."""
    return ScryfallClient(db_path=tmp_path / "search_cache.db")

@pytest.fixture
def populated_cache(search_client):
    """Populate cache with known test cards for deterministic testing."""
    test_cards = [
        {"id": "test-001", "name": "Lightning Bolt", "mana_cost": "{R}", "type_line": "Instant",
         "oracle_text": "Lightning Bolt deals 3 damage to any target.", "colors": ["R"],
         "cmc": 1.0, "keywords": [], "rarity": "uncommon", "set": "MOM"},
        {"id": "test-002", "name": "Avacyn's Pilgrim", "mana_cost": "{W}", "type_line": "Creature — Human Cleric",
         "oracle_text": "Flying, Whenever Avacyn's Pilgrim enters the battlefield, create a Mountain and a Forest.",
         "colors": ["W"], "cmc": 1.0, "keywords": ["flying"], "rarity": "common", "set": "AVR"},
        # ... more test cards for pagination tests
    ]
    for card in test_cards:
        search_client._cache_put(card)
    return search_client
```

---

## Potential Risks

### 1. Performance on large caches (20k+ cards)
**Risk**: `json_extract()` + LIKE queries may be slow without indexes on JSON fields.
**Mitigation**: For MVP, accept the performance trade-off. If cache grows beyond ~50k cards, add a virtual table with FTS5 or denormalize frequently-queried fields into separate columns. Monitor query time in logs.

### 2. Keyword array matching via LIKE
**Risk**: Keywords are stored as JSON arrays `["flying", "haste"]`. Using `LIKE '%flying%'` on the stringified JSON could produce false positives (e.g., "first strike" contains "strike").
**Mitigation**: Use exact substring match with word boundaries: `LIKE '%"flying"%'` — matching the quoted keyword in the JSON array representation. This is safe because Scryfall keywords are always properly quoted strings in the JSON.

### 3. Color AND logic complexity
**Risk**: Building dynamic SQL for multiple colors requires careful parameter binding.
**Mitigation**: Build WHERE clause dynamically in Python, appending one `AND json_extract(...) LIKE '%"?%"%'` per color. Use parameterized queries throughout to prevent injection.

### 4. Oracle text NULL handling
**Risk**: Some cards (tokens, basic lands) may have NULL oracle_text. `json_extract(data_json, '$.oracle_text')` returns NULL, and `LIKE` with NULL is always false.
**Mitigation**: Use `COALESCE(json_extract(data_json, '$.oracle_text'), '')` to treat NULL as empty string for LIKE matching.

---

## Handoff to Implementer

**Design Document**: `specs/038-gap-analysis/APP-01-design.md` (this file)
**User Story**: `.opencode/discovery/story-app01-card-search.md`
**Estimated Complexity**: Low — single endpoint, no new dependencies, straightforward SQLite queries
**Key Files**:
1. `mtg_engine/card_data/scryfall.py` — Add `search_cards()` method
2. `mtg_engine/api/routers/card_search.py` — New router file
3. `mtg_engine/api/main.py` — Mount new router
4. `tests/api/test_card_search.py` — Test suite

**Start With**: Task 1 — Implement `ScryfallClient.search_cards()` with SQL query building and pagination logic. This is the foundation; the router just wraps it.

**Acceptance Criteria** (from Discovery story):
- [ ] `GET /cards/search` endpoint accepts all query parameters: q, type, colors, cmc_min, cmc_max, mana_cost, keyword, rarity, set_code
- [ ] Free-text search matches name and oracle_text case-insensitively
- [ ] Paginated response with total count
- [ ] Default per_page=25, max 100; default page=1
- [ ] Each result includes: name, mana_cost, type_line, oracle_text, colors, cmc, keywords, rarity, set_code
- [ ] Search operates entirely against local SQLite cache (no Scryfall API calls)
- [ ] Cards not in cache do NOT appear in results
- [ ] Multiple filters combine with AND logic
- [ ] Results sorted by name ascending by default; optional sort_by (cmc, name) and sort_order (asc/desc)
- [ ] HTTP 400 for invalid parameters
- [ ] ≥8 tests covering all axes

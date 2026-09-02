# Story: Card Search API (APP-01)

## User Story
As a player or AI agent, I want to search the loaded card database by name, oracle text, mana cost, type, and other attributes, so that I can discover cards for deck building, draft preparation, and gameplay reference.

## Context
**Status: ✅ Complete**

Implemented as APP-01. A queryable REST API on top of the local SQLite Scryfall cache:

- **`GET /cards/search`** endpoint with filters: `q` (free-text), `type`, `colors`, `cmc_min`, `cmc_max`, `mana_cost`, `keyword`, `rarity`, `set_code`
- **Two-query pagination**: COUNT query first for total results, then SELECT with LIMIT/OFFSET for the page
- **SQLite json_extract() filtering**: Card data stored as JSON blobs; uses `json_extract()` in WHERE clauses for structured field access
- **Case-insensitive LIKE matching**: Free-text search across name AND oracle_text columns
- **AND logic**: All filter parameters combine with AND
- **Parameter validation**: HTTP 400 for invalid parameters

## Acceptance Criteria
- [x] `GET /cards/search` with filters: q, type, colors, cmc_min, cmc_max, mana_cost, keyword, rarity, set_code
- [x] Free-text search matches name and oracle_text via case-insensitive substring
- [x] Paginated response: `{ data: { cards: [...], total, page, per_page } }`
- [x] Default per_page=25, max per_page=100; default page=1
- [x] Search operates entirely against local SQLite cache (no Scryfall API calls)
- [x] Multiple filters combine with AND logic
- [x] Results sorted by name ascending by default; optional sort_by (cmc, name) and sort_order (asc/desc)
- [x] HTTP 400 for invalid parameters
- [x] 49 tests (35 engine + 14 API) covering all filters, pagination, sorting, errors

## Dependencies
- None (ScryfallClient and SQLite cache already existed)

## Priority: High | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/api/routers/card_search.py`, `mtg_engine/card_data/scryfall.py`
- Test files: `tests/api/test_card_search.py` and related engine tests
- Router mounted in `mtg_engine/api/main.py`
- Search is read-only on cached data — cards not in cache do not appear

# Story: Card Search API (APP-01)

## User Story
As a player or AI agent, I want to search the loaded card database by name, oracle text, mana cost, type, and other attributes, so that I can discover cards for deck building, draft preparation, and gameplay reference.

## Context
The engine already has `ScryfallClient` in `mtg_engine/card_data/scryfall.py` with SQLite cache + MongoDB bulk store. It supports `get_card(name)` and `preload(names)`. The `Card` model in `models/game.py` has fields: name, mana_cost, type_line, oracle_text, colors, cmc, keywords, rarity, set_code, color_identity, etc.

Currently there is no search endpoint — only exact-name lookup via ScryfallClient. This story adds a queryable REST API on top of the cached card data so callers can filter and paginate results without hitting the Scryfall API rate limits.

## Acceptance Criteria
- [x] `GET /cards/search` endpoint accepts query parameters: `q`, `type`, `colors`, `cmc_min`, `cmc_max`, `mana_cost`, `keyword`, `rarity`, `set_code`
- [x] Free-text search (`q`) matches against card name and oracle_text using case-insensitive substring matching
- [x] Results include a paginated response: `{ data: { cards: [...], total: int, page: int, per_page: int } }`
- [x] Default `per_page=25`, max `per_page=100`; default `page=1`
- [x] Each result card includes: name, mana_cost, type_line, oracle_text, colors, cmc, keywords, rarity, set_code
- [x] Search operates entirely against the local SQLite cache (no Scryfall API calls during search)
- [x] If a card is not in the local cache, it does NOT appear in results (search is read-only on cached data)
- [x] Multiple filters combine with AND logic
- [x] Results sorted by name ascending by default; optional `sort_by` (cmc, name) and `sort_order` (asc/desc)
- [x] HTTP 400 returned for invalid parameters
- [x] 49 tests covering: all filters, pagination, sorting, error cases

## Dependencies
- None (ScryfallClient and SQLite cache already exist)

## Status: ✅ Complete

Implemented with 49 tests (35 engine + 14 API). Full search endpoint with filters, pagination, sorting. SQLite Scryfall cache.

## Priority: High

## Notes
- The search should be fast (<100ms for typical queries). Consider adding a simple full-text index on the SQLite `cards` table if substring matching is too slow with large caches.
- This endpoint does NOT fetch from Scryfall — it only searches what's already cached. If a user wants to ensure a card is available, they should call `POST /deck/import` or similar first to trigger caching.
- The router file will be `mtg_engine/api/routers/card_search.py`, mounted in `main.py` alongside existing routers.

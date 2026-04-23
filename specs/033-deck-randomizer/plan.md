# Implementation Plan: Deck Randomizer from MTGGoldfish

**Branch**: `033-deck-randomizer` | **Date**: 2026-04-21 | **Spec**: `/specs/033-deck-randomizer/spec.md`
**Input**: Feature specification from `/specs/033-deck-randomizer/spec.md`

## Summary

Implement a deck randomizer that fetches competitive decks from MTGGoldfish metagame pages, caches them in MongoDB, and allows users to either get random decks automatically or pick from a dropdown when creating games.

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5.x, React 18
**Primary Dependencies**: FastAPI, Pydantic, motor (async MongoDB), httpx (for scraping), beautifulsoup4 (HTML parsing)
**Storage**: MongoDB (cached decks), in-memory (runtime deck cache)
**Testing**: Manual browser + backend pytest
**Target Platform**: Modern browsers
**Project Type**: Web SPA (Vite + React) + FastAPI backend
**Performance Goals**: First fetch < 30s, cached fetch < 100ms
**Constraints**: Must not break existing deck import; must gracefully handle MTGGoldfish being unavailable
**Scale/Scope**: Backend + frontend; ~12 files touched

## Constitution Check

- New Python dependency needed: `beautifulsoup4` for HTML scraping.
- MongoDB collection needed: `metagame_decks`.
- Scraping is inherently fragile — need fallback to default decks.

## Project Structure

### Documentation

```text
specs/033-deck-randomizer/
├── spec.md              # Feature specification
├── plan.md              # This file
```

### Source Code Changes

```text
backend:
mtg_engine/card_data/mtggoldfish.py      # NEW: Scraper + cache manager
mtg_engine/models/deck_import.py         # UPDATE: Add MetagameDeck model
mtg_engine/api/routers/deck_import.py    # UPDATE: Add /deck/metagame endpoints
mtg_engine/persistence/mongo_client.py   # UPDATE: Add metagame_decks collection
mtg_engine/api/routers/ai_game.py        # UPDATE: Randomize decks if empty
mtg_engine/api/routers/human_game.py     # UPDATE: Randomize decks if empty

frontend:
frontend/src/types/game.ts               # UPDATE: Add MetagameDeck type
frontend/src/components/CreateGameForm.tsx # UPDATE: Deck dropdown + randomize checkbox
frontend/src/components/HumanGameCreator.tsx # UPDATE: Deck dropdown + randomize checkbox
frontend/src/hooks/useMetagameDecks.ts   # NEW: Hook for fetching cached decks
```

## Implementation Tasks

### Phase 1: MTGGoldfish Scraper (`mtg_engine/card_data/mtggoldfish.py`)

Create a scraper module:

1. `fetch_metagame_decks(format: str, limit: int = 10)` — Scrape MTGGoldfish metagame page:
   - Standard: `https://www.mtggoldfish.com/metagame/standard#paper`
   - Commander: `https://www.mtggoldfish.com/metagame/commander#paper`
   - Parse HTML with BeautifulSoup to extract deck names and deck page URLs
2. `fetch_deck_list(deck_url: str)` — Scrape individual deck page for card list:
   - Parse the deck table to get card names and quantities
   - Extract commander name for Commander decks
3. `DeckCache` class — MongoDB-backed cache:
   - `save_decks(format, decks)` — Store fetched decks in MongoDB
   - `get_random_deck(format)` — Return a random cached deck
   - `get_decks_by_format(format)` — List all cached decks for a format
   - `needs_refresh(format)` — Check if cache is stale (> 7 days)
   - `refresh(format)` — Fetch and cache new decks

### Phase 2: MongoDB Integration

1. Add `get_metagame_decks_collection()` to `mongo_client.py`
2. Create `metagame_decks` collection with indexes on `format` and `name`
3. Document schema:
   ```json
   {
     "format": "standard",
     "name": "Mono Red Aggro",
     "cards": [{"name": "Mountain", "quantity": 20}, ...],
     "commander": null,
     "fetched_at": "2026-04-21T12:00:00Z"
   }
   ```

### Phase 3: Backend Endpoints

1. `GET /deck/metagame?format=standard` — List cached decks for a format
2. `POST /deck/metagame/refresh` — Trigger a refresh from MTGGoldfish
3. `GET /deck/metagame/random?format=standard` — Return a random deck

### Phase 4: Game Creation Integration

Update `ai_game.py` and `human_game.py`:

1. If `deck1` is empty and `deck1_deck_name` is not set, call `DeckCache.get_random_deck(format)` for player 1
2. If `deck2` is empty and `deck2_deck_name` is not set, call `DeckCache.get_random_deck(format)` for player 2
3. If `randomize_decks_per_game` is true (series mode), store the setting in series config and randomize each game

### Phase 5: Frontend UI

1. **Create `useMetagameDecks.ts` hook**:
   - Fetches cached decks by format
   - Provides `refetch()` to trigger refresh
2. **Update `CreateGameForm.tsx`**:
   - Replace raw deck textareas with:
     - Deck source selector: "Custom" | "Random" | "From Cache"
     - If "From Cache": dropdown with cached deck names
     - If "Random": auto-assigned (no UI needed)
     - If "Custom": existing textarea
   - Add "Randomize decks per game" checkbox (visible when series count > 1)
3. **Update `HumanGameCreator.tsx`**:
   - Same deck selection UI pattern

### Phase 6: Build & Verify

- Install `beautifulsoup4` dependency
- TypeScript compilation
- Vite build
- Backend tests pass
- Manual test: fetch decks, create game with random decks, verify series randomization

## Dependencies

```bash
pip install beautifulsoup4
```

## Test Plan

- [ ] Fetch Standard decks from MTGGoldfish and cache in MongoDB
- [ ] Fetch Commander decks from MTGGoldfish and cache in MongoDB
- [ ] List cached decks via API endpoint
- [ ] Create AI game with no decks — random decks assigned
- [ ] Create human game with one deck provided — other player gets random deck
- [ ] Create 3-game series with "Randomize decks per game" — different decks each game
- [ ] Create 3-game series without checkbox — same decks all games
- [ ] Select specific deck from dropdown for a player
- [ ] Verify fallback to default decks when MTGGoldfish is unavailable
- [ ] Verify no regressions in manual deck import

## Rollback

- Remove `beautifulsoup4` from dependencies
- Drop `metagame_decks` MongoDB collection
- Revert file changes

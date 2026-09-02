# Story: Draft / Sealed Simulation (APP-05)

## User Story
As a player or AI agent, I want to simulate a draft pick event or sealed pool so that I can practice drafting strategies and generate decks from limited-format card pools.

## Context
The engine already has APP-02 Deck Building AI (`mtg_engine/ai/deck_builder.py`) which constructs legal decks from a card pool. The `card_eval.py` module provides per-card quality scoring. ScryfallClient supports bulk card fetching via `preload()`.

This story adds two simulation modes:
1. **Draft**: N-player draft where each player picks 1 card per round from packs of 15 cards. Packs are generated from a set pool (e.g., "MOM" for Modern Horizons). Cards pass left/right in alternating rounds.
2. **Sealed**: Each player receives a single 15-card pack and builds a deck from that fixed pool.

The draft uses bot-driven pick logic based on card evaluation scores, with support for human-in-the-loop picks via REST API.

## Acceptance Criteria
- [x] `POST /ai/draft/start` with player list, packs, set code, format → returns session ID
- [x] Pack generation from Scryfall set data with rarity-weighted random selection
- [x] `GET /ai/draft/{id}/state` returns round, picks, drafted cards per player
- [x] `POST /ai/draft/{id}/pick` for human-in-the-loop with validation
- [x] Bot auto-pick using `estimate_card_quality()` with color synergy
- [x] Snake-draft: odd rounds pass left, even rounds pass right
- [x] Post-draft deck construction via APP-02 `build_deck()`
- [x] `GET /ai/draft/{id}/results` returns decklists and statistics
- [x] Sealed mode: one 15-card pack per player, auto-deck construction
- [x] 57 tests covering: pack generation, pick order, bot pick, human pick, sealed, results, error handling

## Dependencies
- APP-02 (Deck Building AI) — required for post-draft deck construction

## Status: ✅ Complete

Implemented with 57 tests (37 engine + 20 API). Pack generation with rarity-weighted selection, snake-draft pick order, bot auto-pick with color synergy, sealed pool mode, LRU session eviction.

## Priority: Medium

## Notes
- Draft state should be stored in-memory via a `DraftSession` model (similar to GameManager's pattern). No MongoDB persistence needed initially.
- Pack generation uses Scryfall set data. If the set isn't loaded, fall back to a randomized pool from all cached cards filtered by format legality.
- Bot pick strategy can start simple (highest quality score) and evolve to consider color synergy, CMC curve, and card interactions within the drafted pool.
- Consider adding a `strategy` parameter per player so different bots can play different strategies during draft simulation.

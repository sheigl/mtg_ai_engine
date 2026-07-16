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
- [ ] `POST /ai/draft/start` endpoint accepts: `{ players: list[str], packs_per_player: int, set_code: str, format: str }` and returns a draft session ID
- [ ] Draft generates packs of 15 cards from the specified set using Scryfall data (via MongoDB bulk store or cached SQLite)
- [ ] `GET /ai/draft/{session_id}/state` returns current draft state: round number, pick number, available picks per player, each player's drafted cards so far
- [ ] `POST /ai/draft/{session_id}/pick` accepts `{ player_name: str, card_name: str }` for human-in-the-loop picks; validates the card is in the available pool
- [ ] Bot players auto-pick using `estimate_card_quality()` scoring with strategy-aware weighting (prioritize synergy within drafted cards)
- [ ] Pack passing follows standard Limited rules: odd rounds pass left, even rounds pass right (for 8-player draft)
- [ ] After all picks complete, each player's drafted pool is automatically converted to a deck via APP-02's `build_deck()` with the specified format
- [ ] `GET /ai/draft/{session_id}/results` returns final results: each player's decklist, sideboard, and draft statistics (cards picked per round)
- [ ] Sealed mode: `POST /ai/sealed/start` accepts `{ players: list[str], set_code: str }`, generates one 15-card pack per player, builds decks automatically
- [ ] >= 8 tests covering: pack generation from set code, draft pick order (left/right passing), bot auto-pick logic, human-in-the-loop pick validation, deck construction post-draft, sealed pool generation, results retrieval, invalid session handling

## Dependencies
- APP-02 (Deck Building AI) — required for post-draft deck construction

## Priority: Medium

## Notes
- Draft state should be stored in-memory via a `DraftSession` model (similar to GameManager's pattern). No MongoDB persistence needed initially.
- Pack generation uses Scryfall set data. If the set isn't loaded, fall back to a randomized pool from all cached cards filtered by format legality.
- Bot pick strategy can start simple (highest quality score) and evolve to consider color synergy, CMC curve, and card interactions within the drafted pool.
- Consider adding a `strategy` parameter per player so different bots can play different strategies during draft simulation.

# Story: Deck Building AI (APP-02)

## User Story
As a player or AI agent, I want to provide a card pool, format, and strategy description so that the system constructs a legal, optimized deck automatically.

## Context
The engine already has:
- **FMT-01 Format Validation** (`mtg_engine/engine/formats/__init__.py`): `validate_deck(cards, format_name, commanders)` with 8 formats (Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper) and banned/restricted list enforcement.
- **Card Evaluation** (`mtg_engine/ai/card_eval.py`): `estimate_card_quality()`, `is_removal_spell()`, `is_counterspell()`, `is_board_wipe()`, `is_draw_spell()`, `is_ramp()`, etc. — provides per-card scoring heuristics.
- **Card model** with color_identity, cmc, type_line, keywords for strategy-aware selection.

This story builds a deck construction algorithm that scores cards from a pool, applies format constraints (deck size, banned lists, singleton rules), and produces a legal decklist. The "strategy" parameter guides card prioritization (e.g., "aggro" favors low-CMC creatures with haste; "control" favors counterspells and board wipes).

## Acceptance Criteria
- [ ] `POST /ai/deck/build` endpoint accepts: `{ card_pool: list[Card], format: str, strategy: str, commander_names: optional[list[str]] }`
- [ ] Returns `{ data: { deck: list[dict], sideboard: list[dict], validation: DeckValidationResponse } }` where each dict includes card name and quantity
- [ ] Strategy parameter supports at minimum: "aggro", "control", "midrange", "combo" — each adjusts scoring weights (e.g., aggro boosts low-CMC creatures, control boosts removal/counterspells)
- [ ] Deck construction respects format rules: deck size minimums (60/100), banned cards excluded, singleton enforcement for Legacy/Vintage/Commander/Brawl
- [ ] Commander format: if `commander_names` provided, validates color identity and includes commanders in the 100-card total
- [ ] Uses existing `estimate_card_quality()` as baseline score, modified by strategy weights and CMC curve targeting
- [ ] Deck is validated via FMT-01's `validate_deck()` before returning; if validation fails, returns errors in the response rather than an invalid deck
- [ ] Sideboard construction: for formats that support sideboards (non-Commander), fills remaining legal cards up to 15
- [ ] Cards not in any format's legality window are excluded from consideration
- [ ] >= 8 tests covering: aggro strategy produces low-CMC heavy deck, control strategy produces removal-heavy deck, banned card exclusion, singleton enforcement, commander color identity validation, minimum deck size met, sideboard population, invalid format handling

## Dependencies
- FMT-01 (Format Validation) — already complete ✅

## Priority: High

## Notes
- The algorithm should be deterministic given the same inputs (card_pool + format + strategy). Use a seeded sort for tie-breaking.
- Strategy weights can start as hardcoded multipliers per card category (removal, draw, ramp, creature CMC bracket) and evolve into ML-driven scoring later.
- This is intentionally NOT an LLM-based deck builder — it's a heuristic algorithm using existing `card_eval.py` functions. Future iterations could integrate LLM suggestions.

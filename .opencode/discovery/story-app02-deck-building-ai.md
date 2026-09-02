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
- [x] `POST /ai/deck/build` endpoint accepts card pool, format, strategy, optional commander names
- [x] Returns deck, sideboard, and validation results
- [x] Strategy parameter supports: "aggro", "control", "midrange", "combo" with adjusted scoring weights
- [x] Deck construction respects format rules: deck size, banned cards, singleton enforcement
- [x] Commander format: validates color identity, includes commanders in 100-card total
- [x] Uses `estimate_card_quality()` baseline modified by strategy weights and CMC curve targeting
- [x] Deck validated via FMT-01's `validate_deck()` before returning
- [x] Sideboard construction fills remaining legal cards up to 15 (non-Commander formats)
- [x] Cards outside format legality window are excluded
- [x] 59 tests covering: strategies, banned cards, singleton, commander, deck size, sideboard, invalid formats

## Dependencies
- FMT-01 (Format Validation) — already complete ✅

## Status: ✅ Complete

Implemented with 59 tests (52 unit + 7 API). Full pipeline: Filter → Score → Select → Validate. Supports 8 formats with strategy weights, CMC curve targeting, basic land exemption.

## Priority: High

## Notes
- The algorithm should be deterministic given the same inputs (card_pool + format + strategy). Use a seeded sort for tie-breaking.
- Strategy weights can start as hardcoded multipliers per card category (removal, draw, ramp, creature CMC bracket) and evolve into ML-driven scoring later.
- This is intentionally NOT an LLM-based deck builder — it's a heuristic algorithm using existing `card_eval.py` functions. Future iterations could integrate LLM suggestions.

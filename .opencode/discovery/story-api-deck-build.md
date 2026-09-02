# Story: Deck Building AI (APP-02)

## User Story
As a player, I want to automatically construct a deck from a card pool based on strategy, format, and constraints, so that I can quickly generate playable decks for testing or limited events.

## Context
**Status: ✅ Complete**

Implemented as APP-02. Automated deck construction via Pipeline architecture:

- **Pipeline**: Filter → Score → Select → Validate
  - **Filter**: Removes banned cards, enforces legality windows, singleton rules (basic land exemption), restricted limits (Vintage), commander color identity filtering
  - **Score**: `estimate_card_quality()` baseline × strategy_multiplier × cmc_curve_bonus for composite scoring
  - **Select**: Greedy selection with deterministic tie-breaking via seed, land balancing (~24% minimum), sideboard construction up to 15 cards
  - **Validate**: FMT-01 `validate_deck()` integration — returns validation errors if deck is invalid
- **Strategy weights**: Aggro, Control, Midrange, Combo — each with specific category multipliers and CMC curve targets
- **Format support**: All 8 formats — Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper

## Acceptance Criteria
- [x] `POST /ai/deck/build` endpoint with strategy, format, commanders, seed parameters
- [x] Filter stage removes banned cards, enforces legality windows, singleton rules, restricted limits
- [x] Score stage uses strategy weights × CMC curve bonus for composite scoring
- [x] Select stage uses greedy selection with deterministic tie-breaking, land balancing
- [x] Sideboard construction (up to 15 cards, non-singleton formats only)
- [x] Commander color identity filtering
- [x] Validation integration with FMT-01
- [x] All 8 formats supported
- [x] 59 tests (52 unit + 7 API integration)

## Dependencies
- FMT-01 Format Rules Engine (for deck validation at end of pipeline)

## Priority: High | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/ai/deck_builder.py`, `mtg_engine/api/routers/deck_build_ai.py`
- Test file: `tests/ai/test_deck_builder.py`
- Strategy weights are configurable via `STRATEGY_WEIGHTS` dict
- Basic lands always exempt from singleton dedup per CR 905.2
- Uses `random.Random(seed)` for reproducible deterministic results

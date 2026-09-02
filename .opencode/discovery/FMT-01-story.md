# Story: Format Rules Engine (FMT-01)

## User Story
As an MTG player or AI agent, I want to validate that my deck is legal for a given format before starting a game, so that I don't waste time playing with illegal decks and the engine can enforce format-specific rules.

## Context
The engine already has Commander-specific validation in `mtg_engine/engine/formats/commander.py` (`validate_deck_for_commander`, `get_color_identity`). However, there is no unified format validation system for other formats (Standard, Pioneer, Modern, Legacy, Vintage, Pauper, Brawl). The existing `card_data/deck_validator.py` only checks basic structure (60-card minimum, 15-sideboard maximum) with no format-specific rules.

This story creates a centralized Format Rules Engine that:
- Provides hardcoded banned/restricted lists per format (Scryfall API integration is out of scope — static data only)
- Reuses existing Commander validation logic rather than duplicating it
- Exposes a `POST /deck/validate` API endpoint for pre-game deck checking

**Important model gap**: The `Card` model currently lacks `rarity` and `set_code` fields. Pauper requires rarity, and Standard/Pioneer/Modern require set codes to determine legality windows. These fields must be added to the Card model as part of this story (with optional/default values so existing code is not broken).

## Acceptance Criteria

### Banned List Data Source
- [x] `mtg_engine/engine/formats/banned.py` contains hardcoded banned lists for all 8 formats
- [x] Banned/restricted lists accessible via `is_banned()` and `is_restricted()` lookup functions
- [x] Case-insensitive matching for card names

### Card Model Extensions
- [x] `Card` model gains optional `rarity: str | None = None` and `set_code: str | None = None` fields
- [x] Both fields default to `None` — backward compatible

### Generic Validation Function
- [x] `validate_deck(cards, format_name, commanders)` in `mtg_engine/engine/formats/__init__.py`
- [x] Returns all violations found (not just first)
- [x] Supports 8 formats: Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper

### Format-Specific Rules — Commander
- [x] Delegates to existing `validate_deck_for_commander()` — no duplication

### Format-Specific Rules — Brawl
- [x] Exactly 60 cards, legendary creature/planeswalker commander, Standard banned list

### Format-Specific Rules — Pauper
- [x] All cards must have `rarity == "common"`; unknown rarity flagged; max 4 copies per non-basic

### Format-Specific Rules — Standard / Pioneer / Modern / Legacy / Vintage
- [x] All formats check banned lists; Vintage checks restricted list; deck size min 60; sideboard max 15; set-code legality windows enforced

### API Endpoint
- [x] `POST /deck/validate` with format, cards, optional commanders; returns valid + violations; unknown format returns HTTP 400

### Tests
- [x] 42 tests (36 engine + 6 API) covering: banned lists, restricted, Commander, Brawl, Pauper, validation, API success/error paths

## Dependencies
- **None** — this story is self-contained. The Card model changes are additive (optional fields with defaults), so they don't break existing code. Existing Commander validation is already implemented and tested.

## Priority: High

This is the first task of Sprint 4 and enables downstream work like APP-02 Deck Building AI, which depends on format validation.

## Status: ✅ Complete

Implemented with 42 tests (36 engine + 6 API). Supports 8 formats (Standard, Pioneer, Modern, Legacy, Vintage, Commander, Brawl, Pauper) with banned/restricted lists, set-code legality windows, rarity checks, and `POST /deck/validate` API endpoint.

## Notes
- **Banned list data freshness**: Hardcoded lists will become stale over time. This is acceptable for MVP — a future enhancement could wire up Scryfall API to fetch live banned/restricted lists dynamically.
- **Set code legality windows**: Standard rotates every year; Pioneer and Modern have fixed entry points (Return to Ravnica / 8th Edition). The implementation should use a set-code cutoff approach: define the earliest legal set per format, then check `card.set_code >= cutoff`. A helper like `_is_set_legal_for_format(set_code, format)` would encapsulate this.
- **Pauper singleton**: Unlike Commander (which allows unlimited basic lands), Pauper follows standard constructed rules — max 4 copies of any card by name except basics. This should be enforced.
- **Brawl legality window**: Brawl uses Standard-legal cards. If set_code data is available, use the Standard legality window; otherwise, fall back to checking the Standard banned list only and flagging unknown-set cards as warnings rather than hard errors.
- **Separation from deck_import.py**: The existing `card_data/deck_validator.py` handles import-time structural validation (60 min / 15 max sideboard). FMT-01 should live in `engine/formats/` to keep format rules logic separate from the import/parsing pipeline. The API endpoint can call both: first resolve card names, then validate format legality.

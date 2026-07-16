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
- [ ] `mtg_engine/engine/formats/banned.py` contains hardcoded banned lists for each format: Standard, Pioneer, Modern, Legacy, Vintage, Commander, Pauper
- [ ] Each list uses representative sample data (not exhaustive — a handful of well-known banned cards per format is sufficient)
- [ ] `mtg_engine/engine/formats/banned.py` contains the Vintage restricted list with a few representative cards
- [ ] Banned/restricted lists are accessible via simple lookup functions: `is_banned(card_name, format)` and `is_restricted(card_name)`

### Card Model Extensions
- [ ] `Card` model gains optional `rarity: str | None = None` field (values like "common", "uncommon", "rare", "mythic")
- [ ] `Card` model gains optional `set_code: str | None = None` field (e.g., "MOM", "RNA", "ONE")
- [ ] Both fields default to `None` so existing code paths that don't populate them continue to work

### Generic Validation Function
- [ ] `validate_deck(cards, format_name, commanders=None)` → `(is_valid: bool, violations: list[str])` in a central module (e.g., `mtg_engine/engine/formats/__init__.py`)
- [ ] Accepts a list of `Card` objects and a format string
- [ ] Returns all violations found (not just the first one) — caller can see every issue at once

### Format-Specific Rules — Commander (reuse existing)
- [ ] Commander validation delegates to existing `validate_deck_for_commander()` in `commander.py`
- [ ] No duplication of color identity, singleton, or 100-card logic

### Format-Specific Rules — Brawl
- [ ] Deck must be exactly 60 cards (including commander)
- [ ] Commander must be a legendary creature or planeswalker
- [ ] Cards checked against Standard banned list (or Pioneer legality window if set_code is available)

### Format-Specific Rules — Pauper
- [ ] All cards in the deck must have `rarity == "common"`
- [ ] Cards without rarity data are flagged as a violation ("unknown rarity")
- [ ] Singleton rule applies (no more than 4 copies of any non-basic card, per standard MTG rules)

### Format-Specific Rules — Standard / Pioneer / Modern / Legacy / Vintage
- [ ] All formats check their respective banned lists
- [ ] Vintage additionally checks the restricted list (singleton-only for restricted cards)
- [ ] Minimum 60-card deck size enforced for constructed formats
- [ ] Maximum 15 sideboard enforced if sideboard is provided
- [ ] Standard/Pioneer/Modern legality windows are checked via `set_code` when available; if set_code is missing on a card, it is flagged as "unknown legality" rather than silently accepted

### API Endpoint
- [ ] New endpoint: `POST /deck/validate` with JSON body `{ "format": str, "cards": list[dict], "commanders": list[dict] | null }`
- [ ] Response includes: `{ "valid": bool, "violations": list[str], "format": str }`
- [ ] Unknown format names return HTTP 400 with a helpful error listing supported formats
- [ ] Endpoint is mounted under the existing `/deck` prefix (can be in `deck_import.py` or a new router)

### Tests
- [ ] >= 8 tests covering: banned list lookup, restricted list check, Commander validation delegation, Brawl rules, Pauper rarity check, generic validate_deck function, API endpoint success path, API endpoint error path (unknown format)
- [ ] Tests go in `tests/engine/formats/test_formats.py`

## Dependencies
- **None** — this story is self-contained. The Card model changes are additive (optional fields with defaults), so they don't break existing code. Existing Commander validation is already implemented and tested.

## Priority: High

This is the first task of Sprint 4 and enables downstream work like APP-02 Deck Building AI, which depends on format validation.

## Notes
- **Banned list data freshness**: Hardcoded lists will become stale over time. This is acceptable for MVP — a future enhancement could wire up Scryfall API to fetch live banned/restricted lists dynamically.
- **Set code legality windows**: Standard rotates every year; Pioneer and Modern have fixed entry points (Return to Ravnica / 8th Edition). The implementation should use a set-code cutoff approach: define the earliest legal set per format, then check `card.set_code >= cutoff`. A helper like `_is_set_legal_for_format(set_code, format)` would encapsulate this.
- **Pauper singleton**: Unlike Commander (which allows unlimited basic lands), Pauper follows standard constructed rules — max 4 copies of any card by name except basics. This should be enforced.
- **Brawl legality window**: Brawl uses Standard-legal cards. If set_code data is available, use the Standard legality window; otherwise, fall back to checking the Standard banned list only and flagging unknown-set cards as warnings rather than hard errors.
- **Separation from deck_import.py**: The existing `card_data/deck_validator.py` handles import-time structural validation (60 min / 15 max sideboard). FMT-01 should live in `engine/formats/` to keep format rules logic separate from the import/parsing pipeline. The API endpoint can call both: first resolve card names, then validate format legality.

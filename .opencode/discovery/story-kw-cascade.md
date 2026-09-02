# Story: Cascade (CR 702.85)

## User Story
As a player, I want my cascade spells to exile cards from my library until a nonland card with lesser mana value is found, then let me cast it without paying its mana cost, so that cascade enables high-variance, value-generating plays.

## Context
Cascade exiles cards from the top of the library until a nonland card with lesser mana value is found, then allows casting it without paying its mana cost. Remaining exiled cards are put on the bottom in random order. Implements real `apply()` with `model_copy` pure transforms and human/AI choice paths.

### Comprehensive Rules Grounding
- **CR 702.85a**: "Cascade is a triggered ability that functions on the stack. 'Cascade' means 'When you cast this spell, exile cards from the top of your library until you exile a nonland card whose mana value is less than this spell's mana value. You may cast that card without paying its mana cost if you do. Then put all cards exiled this way that weren't cast on the bottom of your library in a random order.'"
- **Example card**: Bloodbraid Elf — "Cascade (When you cast this spell, exile cards from the top of your library until you exile a nonland card with lesser mana value. You may cast it without paying its mana cost. Put the rest on the bottom in a random order.)"

## Acceptance Criteria
- [x] `Cascade.has_cascade()` correctly detects cascade keyword
- [x] `Cascade.from_oracle_text()` detects cascade in oracle text
- [x] `apply_cascade()` implements the full exile-then-choose resolution via pure `model_copy`
- [x] Human path: queues `pending_cascade` on GameState with found_card and exiled_cards
- [x] AI path: auto-casts found card (adds to stack as free spell), randomizes remaining on bottom
- [x] `resolve_cascade_cast()` places found card on stack and clears pending cascade
- [x] `resolve_cascade_exile()` exiles found card and clears pending cascade
- [x] Correctly handles edge cases: library emptied, all lands, all high-CMC cards
- [x] Unit tests in `tests/ability/keywords/test_cascade.py`, integration tests in `tests/engine/test_keywords_integration.py`, and scenario tests in `tests/test_018/test_018_cascade.py`

## Dependencies
- None (standalone triggered keyword, called during spell resolution)

## Priority: Medium

## Status: ✅ Complete

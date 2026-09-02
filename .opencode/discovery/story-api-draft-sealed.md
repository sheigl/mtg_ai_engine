# Story: Draft / Sealed Simulation (APP-05)

## User Story
As a player, I want to simulate a draft or sealed event — generating packs, drafting with bots, and constructing a deck from the results — so that I can practice limited formats without a live pod.

## Context
**Status: ✅ Complete**

Implemented as APP-05. Limited-format deck construction simulation via REST API:

- **Pack generation**: Rarity-weighted random selection from Scryfall set data.
- **Snake draft**: Odd rounds pass left, even rounds pass right (standard 8-player arrangement).
- **Bot auto-pick**: Uses `estimate_card_quality()` scoring with strategy-aware weighting and color synergy.
- **Sealed pool mode**: One 15-card pack per player, automatic deck construction via APP-02 `build_deck()`.
- **In-memory session storage**: LRU eviction (MAX_DRAFT_SESSIONS=100, completed sessions evicted first).
- **Format validation**: Both draft and sealed modes validate constructed decks.

## Acceptance Criteria
- [x] `POST /ai/draft/start` — start a new draft session
- [x] `GET /ai/draft/{id}/state` — get current draft state (packs, picks, current pick)
- [x] `POST /ai/draft/{id}/pick` — make a pick for human player
- [x] `GET /ai/draft/{id}/results` — get final pool and suggested deck
- [x] `POST /ai/sealed/start` — start a sealed pool session
- [x] Bot auto-pick uses card quality scoring with strategy weighting
- [x] Snake draft: odd rounds pass left, even rounds pass right
- [x] LRU session eviction (max 100 sessions)
- [x] 57 tests (37 engine + 20 API integration)

## Dependencies
- APP-02 Deck Building AI (for sealed pool deck construction)
- Card Search API (for set data and card lookup)

## Priority: Medium | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/ai/draft.py`, `mtg_engine/api/routers/draft_ai.py`
- Test files: `tests/ai/test_draft.py`, `tests/api/test_draft_ai.py`
- In-memory session storage (`_draft_sessions` dict) — documented as non-thread-safe
- `_process_pick()` intentionally mutates in-place (documented exception for lightweight lifecycle objects)
- Bot auto-pick resolves immediately after human pick or at session start

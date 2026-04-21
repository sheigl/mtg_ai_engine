# Research: Skip Empty Phases

**Feature**: 029-skip-empty-phases
**Date**: 2026-04-21

## Unknown 1: Where to Inject Skip Logic

**Question**: Should skip detection happen inside `advance_step()` or in a separate helper called by the game loop?

**Decision**: Inject skip logic inside `advance_step()` in `turn_manager.py`, after `begin_step()` completes but before priority is granted.

**Rationale**:
- `advance_step()` is the canonical place where phase transitions happen
- It already handles `phase_skip_flags` (US7) — skip-empty-phases is a natural extension
- `begin_step()` must run first because it may create triggers (upkeep effects, delayed triggers) that would prevent skipping
- Keeping it in the engine layer (not the AI client layer) ensures consistency across all game modes (AI vs AI, human vs AI, API-driven)

**Alternatives considered**:
- Game loop layer (`ai_client/game_loop.py`): Rejected — would only affect AI games, not API-driven or human games
- Separate middleware function: Rejected — adds indirection without benefit; `advance_step()` already orchestrates the flow

## Unknown 2: How to Detect "Only Pass" for Both Players

**Question**: The existing `_compute_legal_actions()` computes actions for the priority holder only. How do we check both players?

**Decision**: Create a new helper `_has_non_pass_actions(gs, player_name)` that computes legal actions for a given player and returns `True` if any action has `action_type != "pass"`.

**Rationale**:
- The existing `_compute_legal_actions()` is ~700 lines and tightly coupled to the `game.py` router
- Extracting a reusable helper avoids duplicating the complex logic
- The helper can be called twice: once for the current priority holder, once for the other player (with a temporary priority swap)

**Implementation approach**:
1. Move `_compute_legal_actions()` or create a wrapper `get_legal_actions_for_player(gs, player_name)` in `mtg_engine/engine/actions.py` (new file or existing module)
2. The skip logic calls it for both players
3. Also check `gs.pending_triggers`, `gs.pending_*_choice`, and `gs.stack` — any of these prevent skipping

**Alternatives considered**:
- Duplicate `_compute_legal_actions()` logic in `turn_manager.py`: Rejected — 700+ lines, high maintenance burden
- Check only the priority holder: Rejected — non-active player might have instants/activated abilities

## Unknown 3: Transcript Recording for Skipped Phases

**Question**: Should skipped phases use a new `event_type` or reuse `phase_change` with a flag?

**Decision**: Add new `event_type="phase_skipped"` and a corresponding `record_phase_skipped()` method on `TranscriptRecorder`.

**Rationale**:
- New event type makes it unambiguous for transcript consumers
- Keeps backward compatibility — existing `phase_change` entries unchanged
- The description can clearly state "Turn X: [Phase] — [Step] skipped (no actions available)"

**Alternatives considered**:
- Reuse `phase_change` with `"skipped": true` in data: Rejected — less explicit, consumers must check nested field
- Omit from transcript entirely: Rejected — violates FR-003

## Unknown 4: Preventing Infinite Skip Loops

**Question**: What prevents all phases from being skipped indefinitely (e.g., both players have no cards, no permanents)?

**Decision**: The skip logic naturally terminates because:
- Untap step always runs (no priority, so skip logic doesn't apply)
- Some steps always have mandatory actions or create triggers
- Combat steps with creatures on battlefield have declare attackers/blockers actions
- If literally nothing ever happens, the game would eventually end via state-based actions (e.g., draw from empty library)

**Safety mechanism**: Add a recursion depth limit (e.g., max 10 consecutive skips) as a defensive measure. If exceeded, log a warning and grant priority normally.

## Unknown 5: Performance Impact

**Question**: Computing legal actions twice per phase (for both players) adds overhead. Is this acceptable?

**Decision**: Yes. The skip check only runs when the priority holder has only "pass" (the fast path). In most game states, players have cards/abilities, so the check exits after the first player's evaluation.

**Rationale**:
- `_compute_legal_actions()` is already called on every `GET /game/{id}/legal-actions` request
- The skip check is an additional call only in the "empty phase" case
- Per spec assumption: action detection <50ms is acceptable
- Can be optimized later by caching legal action results if needed

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skip logic location | `advance_step()` in `turn_manager.py` | Canonical phase transition point |
| Action detection | Reuse `_compute_legal_actions()` via extracted helper | Avoid duplication, leverage existing logic |
| Transcript event | New `phase_skipped` event type | Explicit, backward-compatible |
| Recursion safety | Max 10 consecutive skips | Defensive programming |
| API changes | None | Skip is transparent to clients |

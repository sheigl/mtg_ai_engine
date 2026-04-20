# Research: Feature 024 - Commentary Annotations, Rating Override & Card Ordering

## Decision 1: Annotation Storage Location

**Decision**: Add a `player_annotation` (str | None) field to the existing `DebugEntry` model in `mtg_engine/models/debug.py`.

**Rationale**: DebugEntry is already stored, streamed, and exported via the debug log infrastructure. Attaching the annotation directly to the entry keeps retrieval trivial and avoids a second lookup. The PATCH endpoint (`PATCH /game/{game_id}/debug/entry/{entry_id}`) already accepts partial updates and sets `rating`/`explanation`/`alternative` — the same pattern works for `player_annotation`.

**Alternatives considered**: Separate annotation store keyed by entry_id — rejected because it adds a second data structure with no benefit given debug entries already live for the game lifetime.

---

## Decision 2: Rating Override Storage

**Decision**: Add `player_rating_override` (str | None — one of `good`, `acceptable`, `suboptimal`) to `DebugEntry`. The original `rating` field is **never modified after the observer sets it**. The UI displays `player_rating_override` as the active rating when present, with the original `rating` shown in a "dimmed" style.

**Rationale**: Preserving the original AI rating is a hard invariant stated in the spec (FR-010, SC-004). Storing both fields on the same model object is the safest approach — there is no risk of the original being overwritten since the PATCH logic will only update `player_rating_override`, never `rating`.

**Alternatives considered**: Overwriting `rating` and storing original separately — rejected because it changes semantics of an existing field that other consumers may rely on.

---

## Decision 3: New API Endpoints

**Decision**: Add two new PATCH sub-resources rather than extending the existing PATCH entry endpoint:
- `PATCH /game/{game_id}/debug/entry/{entry_id}/annotate` — sets/clears `player_annotation`
- `PATCH /game/{game_id}/debug/entry/{entry_id}/rerate` — sets/clears `player_rating_override`

**Rationale**: The existing PATCH endpoint is used by the streaming pipeline and sets `rating` (the AI value). Mixing player and AI writes on the same endpoint risks confusion and accidental overwrites. Separate endpoints make intent unambiguous and allow independent access control later.

**Alternatives considered**: Extending the existing PATCH body with `player_annotation` / `player_rating_override` fields — rejected because it merges AI streaming updates with human annotations in one endpoint, making the AI invariant harder to enforce.

---

## Decision 4: Game Log Integration

**Decision**: Extend `mtg_engine/export/game_log.py`'s `build_game_log()` to accept an optional `debug_entries` list. Entries are merged into the turn/phase timeline by matching `turn`, `phase`, `step`. Annotations and rating overrides are rendered inline below the observer commentary block:

```
[Observer AI — T1 precombat_main/main] Rating: good (AI) → SUBOPTIMAL (Player Override)
  Commentary: <explanation>
  Player Comment: <annotation text>
```

**Rationale**: The export endpoint (`GET /export/{game_id}/game-log`) already receives the transcript and snapshots. Adding debug entries as a third input follows the same pattern. The game log builder is the right place for formatting — not the API router.

**Alternatives considered**: A separate debug export endpoint — rejected because the spec explicitly states annotations appear in the existing "Download Log" action with no extra steps (SC-002).

---

## Decision 5: Drag-to-Reorder Strategy

**Decision**: Use HTML5 drag-and-drop with a client-side order state array for both hand and battlefield reordering. For the hand (InteractiveHand), maintain `handOrder: string[]` (card IDs) in HumanGameBoard. For the battlefield (Battlefield), maintain `permanentOrder: string[]` in HumanGameBoard. Both passed as props; components sort their items by these arrays before rendering.

**Rationale**: The existing card-play drag already uses HTML5 drag events. Reuse the same mechanism with a distinguishing flag (`isReorder` via data attribute or a separate state boolean) to avoid conflict with the card-play drop target. Framer Motion's existing layout animations on Battlefield cards will give smooth reorder animations for free once the rendered order changes.

**Conflict resolution**: A drag originating from within a zone (hand→hand or battlefield→battlefield) is a reorder. A drag from hand to the battlefield drop zone is a card play. The existing `draggedCardId` in HumanGameBoard tracks card-play drags; a new `reorderDragState` tracks intra-zone reordering. They are mutually exclusive.

**Alternatives considered**: react-dnd or dnd-kit — rejected to avoid adding a new dependency. Framer Motion's `drag` prop — evaluated but conflicts with the existing HTML5 drag used for card play.

---

## Decision 6: SSE Stream Update for Annotations/Overrides

**Decision**: When `player_annotation` or `player_rating_override` is patched, the debug SSE stream (`GET /game/{game_id}/debug/stream`) emits an update event for the entry. The frontend's `useDebugLog` hook already upserts entries by `entry_id`, so the updated entry will render automatically.

**Rationale**: The SSE mechanism is already the live update path for debug entries. Piggybacking on it for annotation/override updates means the panel stays consistent across refreshes without polling.

---

## Findings: Existing Code Reuse

| Component | File | Reuse |
|-----------|------|-------|
| DebugEntry model | `mtg_engine/models/debug.py` | Extend with 2 new nullable fields |
| PATCH endpoint | `mtg_engine/api/routers/debug.py` | Add 2 new sub-routes |
| CommentaryBlock | `frontend/src/components/CommentaryBlock.tsx` | Add rating picker + annotation input UI |
| PromptResponseBlock | `frontend/src/components/PromptResponseBlock.tsx` | Add annotation input UI only |
| useDebugLog | `frontend/src/hooks/useDebugLog.ts` | No change needed (already upserts by entry_id) |
| InteractiveHand | `frontend/src/components/InteractiveHand.tsx` | Add reorder drag handlers + accept `handOrder` prop |
| Battlefield | `frontend/src/components/Battlefield.tsx` | Accept `permanentOrder` prop; sort before render |
| HumanGameBoard | `frontend/src/components/HumanGameBoard.tsx` | Add handOrder + permanentOrder state; pass to children |
| build_game_log | `mtg_engine/export/game_log.py` | Accept debug_entries; merge into output |
| game log endpoint | `mtg_engine/api/routers/export.py` | Pass debug entries from store to build_game_log |

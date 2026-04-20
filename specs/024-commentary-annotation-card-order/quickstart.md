# Quickstart: Feature 024 Development

## What's Being Built

Three independently deliverable capabilities:

1. **Player Annotations** — text comments on any completed debug entry (P1)
2. **Rating Override** — replace the observer's Good/Acceptable/Suboptimal rating (P2)
3. **Card Reordering** — drag cards in hand/battlefield to change visual order (P3)

## Key Files to Modify

### Backend

| File | Change |
|------|--------|
| `mtg_engine/models/debug.py` | Add `player_annotation: str | None` and `player_rating_override: str | None` to `DebugEntry` |
| `mtg_engine/api/routers/debug.py` | Add `PATCH …/annotate` and `PATCH …/rerate` endpoints; emit SSE update on each |
| `mtg_engine/export/debug_log.py` | Implement `annotate_entry()` and `rerate_entry()` on `DebugLogRecorder` |
| `mtg_engine/export/game_log.py` | Accept `debug_entries` param; merge entries into turn timeline |
| `mtg_engine/api/routers/export.py` | Pass debug entries from export store into `build_game_log()` |

### Frontend

| File | Change |
|------|--------|
| `frontend/src/types/debug.ts` | Add `player_annotation`, `player_rating_override` to `DebugEntry` type |
| `frontend/src/components/CommentaryBlock.tsx` | Add rating picker (override) + annotation input/display |
| `frontend/src/components/PromptResponseBlock.tsx` | Add annotation input/display only |
| `frontend/src/components/InteractiveHand.tsx` | Accept `handOrder` prop; add intra-zone drag-to-reorder |
| `frontend/src/components/Battlefield.tsx` | Accept `permanentOrder` prop; sort before render |
| `frontend/src/components/HumanGameBoard.tsx` | Add `handOrder`, `permanentOrder` state; wire to child components |

## Implementation Order

Work in this order to keep each step independently testable:

1. **Backend model + endpoints** (annotations + rating override) — no frontend changes yet
2. **Game log integration** — backend only, verify with curl
3. **Frontend type update** — add new fields to `DebugEntry`
4. **CommentaryBlock UI** — rating override picker + annotation
5. **PromptResponseBlock UI** — annotation only
6. **Hand reorder** — InteractiveHand + HumanGameBoard state
7. **Battlefield reorder** — Battlefield + HumanGameBoard state

## Testing

- Backend: `python -m pytest tests/ -v -k "debug"` from project root
- Frontend: `cd frontend && npm run build` to catch type errors
- Manual: Start engine, create a human-vs-AI game with observer enabled, verify each feature in browser

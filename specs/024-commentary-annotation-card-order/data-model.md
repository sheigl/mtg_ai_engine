# Data Model: Feature 024

## Modified Entity: DebugEntry

**File**: `mtg_engine/models/debug.py`

### New Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `player_annotation` | `str \| None` | `None` | Free-text comment added by the human player |
| `player_rating_override` | `str \| None` | `None` | Player's replacement rating; one of `good`, `acceptable`, `suboptimal` |

### Invariants

- `rating` (original AI value) is **read-only after initial set** — never modified by player actions.
- `player_rating_override` may be set, changed, or cleared (`None`) by the player at any time while the game is active.
- `player_annotation` may be created, updated, or deleted (set to `None`) by the player at any time after the entry is `is_complete = True`.
- Blank or whitespace-only `player_annotation` values MUST be rejected at the API layer.

### State Transitions

```
DebugEntry lifecycle:
  created (is_complete=False)
    → streaming (response chunks applied via PATCH)
    → complete (is_complete=True, rating set by observer)
      → [optional] player_annotation set/edited/cleared
      → [optional] player_rating_override set/changed/cleared
```

---

## Client-Side State: Card Display Order

**Not persisted server-side.** Lives in HumanGameBoard component state only.

### Hand Order

```
handOrder: string[]   // ordered list of card IDs; superset of humanPlayer.hand IDs
```

- Initialized from `humanPlayer.hand` on first render.
- When a new card is drawn, it is appended to the end of `handOrder`.
- When a card is played/discarded, it is removed from `handOrder`.
- Reordering updates the array in-place.

### Battlefield Order

```
permanentOrder: string[]   // ordered list of permanent IDs for the human player's battlefield
```

- Initialized from `humanPermanents` on first render.
- When a permanent enters the battlefield, it is appended to the end.
- When a permanent leaves, it is removed.
- Reordering updates the array in-place.

### Merge Strategy

When server state updates (new poll), `handOrder` and `permanentOrder` are reconciled:
1. Remove IDs that no longer exist in the server state.
2. Append any new IDs not already present (at the end).
3. Existing IDs keep their current position.

---

## Export Format: Game Log Entry (Debug Section)

When observer commentary or AI prompt/response entries are emitted in the game log, they appear immediately after the action they relate to:

```
[Observer AI — T{turn} {phase}/{step}]
  AI Rating  : {rating}
  Player Rating Override: {player_rating_override}   ← omitted if None
  Commentary : {explanation}
  Alternative: {alternative}                         ← omitted if None
  Player Comment: {player_annotation}               ← omitted if None

[AI Player: {source} — T{turn} {phase}/{step}]
  (prompt/response summary)
  Player Comment: {player_annotation}               ← omitted if None
```

Both `player_rating_override` and `player_annotation` are omitted entirely when `None` so unmodified entries look identical to the current format.

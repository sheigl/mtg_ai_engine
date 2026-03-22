# Data Model: Observer AI Debug Panel

**Feature**: 011-observer-ai-commentary
**Date**: 2026-03-22

---

## New Models (`mtg_engine/models/debug.py`)

### `DebugEntryType` (Enum)

| Value | Meaning |
|-------|---------|
| `prompt_response` | A prompt sent to a playing AI + its (possibly streaming) response |
| `commentary` | Observer AI's rating and explanation of a non-pass action |

---

### `DebugEntry` (Pydantic BaseModel)

Primary record for every debug event. Covers both playing AI interactions and observer commentary.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_id` | `str` (UUID) | Yes | Unique identifier; stable across streaming patches |
| `entry_type` | `DebugEntryType` | Yes | `prompt_response` or `commentary` |
| `source` | `str` | Yes | Player name (e.g. "Llama") or `"Observer AI"` |
| `turn` | `int` | Yes | Game turn number at time of entry |
| `phase` | `str` | Yes | Phase string (e.g. `"precombat_main"`) |
| `step` | `str` | Yes | Step string (e.g. `"main"`) |
| `timestamp` | `float` | Yes | Unix timestamp (for ordering in UI) |
| `prompt` | `str` | Yes | Full prompt text sent to the LLM |
| `response` | `str` | Yes | Accumulated response text (may be partial during streaming) |
| `is_complete` | `bool` | Yes | `False` while streaming; `True` once LLM finishes |
| `rating` | `str \| None` | No | `"good"`, `"acceptable"`, or `"suboptimal"`. Only set for `commentary` entries |
| `explanation` | `str \| None` | No | Observer AI's explanation. Only set for `commentary` entries |
| `alternative` | `str \| None` | No | Suggested better play. Set for `commentary` entries rated `"suboptimal"` |

**Validation rules**:
- `rating` must be one of `"good"`, `"acceptable"`, `"suboptimal"` if present
- `rating`, `explanation` should both be set together for `commentary` entries
- `prompt_response` entries should not have `rating`, `explanation`, or `alternative`

---

### `DebugEntryPatch` (Pydantic BaseModel — request body for PATCH)

Used by the AI client to append streaming tokens to an in-progress entry.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `response_chunk` | `str` | Yes | Token(s) to append to the existing `response` field |
| `is_complete` | `bool` | Yes | Set `True` on the final patch to mark the entry done |

---

### `DebugLog` (Pydantic BaseModel — response envelope)

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `str` | The game this log belongs to |
| `entries` | `list[DebugEntry]` | All entries in chronological order (by `timestamp`) |

---

## Storage (`mtg_engine/export/debug_log.py`)

### `DebugLogRecorder`

In-memory store for a single game's debug entries. Lives inside `GameExportStore` alongside existing recorders.

**State**:
- `_entries: list[DebugEntry]` — ordered by insertion
- `_index: dict[str, DebugEntry]` — keyed by `entry_id` for O(1) patch access
- `_listeners: list[Callable[[DebugEntry], None]]` — called on every append or patch

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `append_entry` | `(entry: DebugEntry) → None` | Adds new entry; notifies listeners |
| `patch_entry` | `(entry_id: str, chunk: str, is_complete: bool) → DebugEntry \| None` | Appends chunk to response; notifies listeners; returns updated entry or None if not found |
| `get_all` | `() → list[DebugEntry]` | Returns all entries (copy) |
| `register_listener` | `(callback: Callable) → None` | Registers a listener for SSE fan-out |

---

## Extension to `GameExportStore` (`mtg_engine/export/store.py`)

```
GameExportStore
├── snapshots: SnapshotRecorder      (existing)
├── transcript: TranscriptRecorder   (existing)
├── rules_qa: RulesQARecorder        (existing)
└── debug_log: DebugLogRecorder      (NEW)
```

`debug_log` is initialized unconditionally on game creation. Entries accumulate only when the AI client's `--debug` flag is active; the recorder is otherwise empty.

---

## New AI Client Models (`ai_client/observer.py`)

### `CommentaryResult` (dataclass or TypedDict — internal only)

Internal return type from `ObserverAI.analyze()` before posting to engine.

| Field | Type | Description |
|-------|------|-------------|
| `rating` | `str` | `"good"`, `"acceptable"`, or `"suboptimal"` |
| `explanation` | `str` | Natural-language explanation |
| `alternative` | `str \| None` | Better play suggestion (only for suboptimal) |

---

## Frontend Types (`frontend/src/types/debug.ts`)

```typescript
export type DebugEntryType = 'prompt_response' | 'commentary';
export type Rating = 'good' | 'acceptable' | 'suboptimal';

export interface DebugEntry {
  entry_id: string;
  entry_type: DebugEntryType;
  source: string;           // player name or "Observer AI"
  turn: number;
  phase: string;
  step: string;
  timestamp: number;
  prompt: string;
  response: string;
  is_complete: boolean;
  rating?: Rating;
  explanation?: string;
  alternative?: string;
}

export interface DebugLog {
  game_id: string;
  entries: DebugEntry[];
}
```

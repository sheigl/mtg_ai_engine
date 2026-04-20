# Data Model: Feature 025 — MongoDB Game Data Persistence

## MongoDB Collection: `games`

One document per game. The `game_id` is used as the MongoDB `_id`.

### Top-Level Document Schema

```python
{
  "_id": str,                    # == game_id
  "game_id": str,                # game UUID
  "format": str,                 # "standard" | "commander"
  "player_1": {
    "name": str,
    "type": str,                 # "human" | "ai"
  },
  "player_2": {
    "name": str,
    "type": str,                 # "human" | "ai"
  },
  "has_human_player": bool,      # True if either player is human (index key)
  "created_at": datetime,        # UTC, set at game creation
  "completed_at": datetime|None, # UTC, set when game ends
  "is_complete": bool,           # False until game_end event
  "outcome": dict|None,          # GameOutcome.model_dump() — set on game_end
  "transcript": [TranscriptEntry, ...],   # appended on each event
  "snapshots": [Snapshot, ...],           # appended on each finalize_snapshot()
  "debug_entries": [DebugEntry, ...],     # appended when is_complete=True
  "rules_qa": [RulesQAEntry, ...],        # appended on each new entry
}
```

---

### Sub-document: TranscriptEntry

Mirrors `TranscriptEntry` Pydantic model exactly:

```python
{
  "seq": int,
  "event_type": str,   # cast|resolve|trigger|sba|zone_change|damage|phase_change|priority_grant|choice_made|game_end|...
  "description": str,
  "data": dict,
  "turn": int,
  "phase": str,
  "step": str,
}
```

---

### Sub-document: Snapshot

Mirrors `Snapshot` Pydantic model exactly:

```python
{
  "game_id": str,
  "snapshot_id": str,
  "turn": int,
  "phase": str,
  "step": str,
  "game_state": dict,           # full serialized GameState (board state)
  "legal_actions": [dict],      # legal actions at this priority grant
  "action_taken": dict|None,    # the action chosen (None if not yet finalized)
  "action_taken_by": str|None,
}
```

---

### Sub-document: DebugEntry

Mirrors `DebugEntry` Pydantic model exactly:

```python
{
  "entry_id": str,
  "entry_type": str,               # "commentary" | "prompt_response"
  "source": str,
  "turn": int,
  "phase": str,
  "step": str,
  "timestamp": float,
  "prompt": str,
  "response": str,
  "is_complete": bool,             # always True when stored
  "rating": str|None,              # original AI rating (never overwritten)
  "explanation": str|None,
  "alternative": str|None,
  "thinking": str,
  "player_annotation": str|None,
  "player_rating_override": str|None,
}
```

**Invariant**: `rating` is the original AI value and is never modified after initial set, even when `player_rating_override` is updated. When a player annotation or rating override is saved, the persisted document is updated in-place using MongoDB `$set` with array filters targeting the specific `entry_id`.

---

### Sub-document: RulesQAEntry

Mirrors the `RulesQARecorder` output schema:

```python
{
  "question": str,
  "answer": str,
  "source": str,   # player or system that asked
  "turn": int,
  "phase": str,
  "step": str,
}
```

---

### Sub-document: GameOutcome

Mirrors `GameOutcome` Pydantic model exactly:

```python
{
  "game_id": str,
  "winner": str|None,
  "win_condition": str|None,
  "total_turns": int,
  "player_1_name": str,
  "player_2_name": str,
  "player_1_deck": [str],
  "player_2_deck": [str],
  "player_1_final_life": int,
  "player_2_final_life": int,
  "snapshot_count": int,
  "transcript_length": int,
}
```

---

## Required MongoDB Indexes

```python
# Primary key — already unique as _id
{ "_id": 1 }  # unique

# Most recent games first (default sort for API queries)
{ "created_at": -1 }

# Training query: completed games sorted by date
{ "is_complete": 1, "created_at": -1 }

# Training query: human-vs-AI completed games
{ "has_human_player": 1, "is_complete": 1, "created_at": -1 }

# Training query: games by format
{ "format": 1, "is_complete": 1, "created_at": -1 }
```

---

## New Python State: `MongoGamePersister`

**Module**: `mtg_engine/persistence/game_persister.py`

Not a Pydantic model — this is a stateful service object.

```
MongoGamePersister
  game_id: str
  collection: AsyncIOMotorCollection
  _finalized: bool              # True after game_end received — blocks duplicate finalization

  register_on_store(store: GameExportStore) → None
    # Registers self as listener on all 4 recorders

  _on_transcript_entry(entry: TranscriptEntry) → None
    # Schedules async $push to transcript array
    # If event_type == "game_end", also schedules finalize_game()

  _on_snapshot_finalized(snap: Snapshot) → None
    # Schedules async $push to snapshots array

  _on_debug_entry(entry: DebugEntry) → None
    # Schedules async $push when is_complete == True

  _on_rules_qa_entry(entry) → None
    # Schedules async $push to rules_qa array

  finalize_game(gs: GameState) → None
    # $set: is_complete, completed_at, outcome

  update_debug_entry(entry: DebugEntry) → None
    # Called by annotate/rerate endpoints to update the stored entry in-place
    # Uses $set with positional array filter on entry_id
```

**Module**: `mtg_engine/persistence/mongo_client.py`

```
_client: AsyncIOMotorClient | None   # module-level singleton

get_client() → AsyncIOMotorClient | None
  # Returns None if MONGODB_URL not set

get_games_collection() → AsyncIOMotorCollection | None
  # Returns None if MongoDB not configured

is_configured() → bool
  # True if MONGODB_URL env var is set
```

---

## Modified Existing Models

### `SnapshotRecorder` (in `mtg_engine/export/snapshots.py`)

Add listener support (same pattern as `TranscriptRecorder`):

```python
_listeners: list[Callable[[Snapshot], None]] = []

register_listener(fn: Callable[[Snapshot], None]) → None
_notify_finalized(snap: Snapshot) → None   # called inside finalize_snapshot()
```

### `GameManager.create_game()` (in `mtg_engine/api/game_manager.py`)

New optional parameters:

```python
player_1_type: str = "ai"   # "human" | "ai"
player_2_type: str = "ai"   # "human" | "ai"
```

These are passed through to `MongoGamePersister` for the initial document insert.

---

## State Transitions

```
Game Document lifecycle:
  created (is_complete=False, all arrays empty)
    → transcript entries pushed as events fire
    → snapshots pushed as actions are finalized
    → debug entries pushed when streaming completes
    → [optional] player annotations / overrides updated in-place
    → game_end event received
      → outcome $set, is_complete=True, completed_at=$set
```

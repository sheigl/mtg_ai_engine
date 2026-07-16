# Design: APP-03 Game Replay

## Overview
Build a structured game replay interface that lets callers step through a completed game event by event, inspect board state at each point, paginate the transcript, and navigate via a condensed timeline. Data is sourced from the existing in-memory `GameExportStore` (transcript + snapshots) — no MongoDB dependency required.

## User Story Reference
`.opencode/discovery/story-app03-game-replay.md` — "As a player or analyst, I want to step through a completed game replay from its transcript so that I can review key moments, understand game flow, and analyze decisions."

---

## Architecture Decisions

### Decision 1: Stateless Replay Engine
The replay engine is stateless — it does not track session state on the server. The client passes `from_event_seq` to indicate position, and the engine reconstructs board state from scratch for each step request. This avoids server-side session management and scales trivially.

**Trade-offs considered**: Server-side sessions would reduce repeated reconstruction work but add complexity (session store, cleanup, concurrency). Stateless is simpler and matches existing export endpoints.

### Decision 2: Two-Tier Board State Reconstruction
Board state at any event position is reconstructed using a two-tier approach:
1. **Snapshot anchors** — If a `Snapshot` exists at or before the target event seq, deserialize its full `GameState` as the starting point. Snapshots are recorded at every priority grant and contain complete game state.
2. **Incremental replay** — Apply transcript events between the snapshot anchor and the target event to incrementally update the reconstructed board state (zone changes, life changes, damage, draws).

This hybrid approach gives accurate board states without requiring a full engine re-run. For positions before any snapshot or between snapshots, incremental replay from the previous snapshot provides reasonable accuracy.

### Decision 3: Separate Router, Not Export Sub-path
The user story notes suggest placing endpoints under `/export/{game_id}/replay/*`, but a dedicated router at `/replay/{game_id}/*` is cleaner and follows the pattern of other top-level feature routers (card_search, deck_build_ai). The replay feature is distinct from bulk export — it's an interactive navigation interface.

### Decision 4: Engine Module in `mtg_engine/export/replay_engine.py`
The reconstruction logic lives alongside existing export modules (`transcript.py`, `snapshots.py`) because it operates on the same data structures. It imports from these modules rather than duplicating logic.

### Trade-offs Considered
- **Alternative: Full engine re-run** — Replaying a game by feeding actions back through the engine would give perfect accuracy but is prohibitively complex (action serialization, deterministic replay guarantees). Rejected for MVP.
- **Alternative: Store intermediate snapshots** — Recording more frequent snapshots would improve reconstruction accuracy but increases memory/storage cost. Current priority-grant frequency is sufficient for MVP.

---

## Files to Create/Modify

### New Files
| File | Purpose | Key Responsibilities |
|------|---------|---------------------|
| `mtg_engine/export/replay_engine.py` | Core replay engine | Board state reconstruction, timeline generation, pagination helpers |
| `mtg_engine/api/routers/replay.py` | FastAPI router for replay endpoints | 4 endpoint handlers, Pydantic request/response models, error handling |
| `tests/api/test_replay.py` | Test suite for replay feature | >=8 tests covering all acceptance criteria |

### Modified Files
| File | Changes | Reason |
|------|---------|--------|
| `mtg_engine/api/main.py` | Import and mount new `replay.router` | Wire endpoints into FastAPI app |
| `.opencode/context/standards.md` | Add APP-03 coding standards section | Document replay patterns for future reference |

---

## Data Models / Interfaces

### Response Models (Pydantic v2) — defined in `mtg_engine/api/routers/replay.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class ReplayInfoResponse(BaseModel):
    """GET /replay/{game_id}/info response."""
    game_id: str
    total_events: int
    turns: int
    winner: Optional[str] = None
    loser: Optional[str] = None
    format: Optional[str] = None

class TranscriptEventResponse(BaseModel):
    """Single transcript event in paginated response."""
    seq: int
    event_type: str
    description: str
    data: dict
    turn: int
    phase: str
    step: str

class EventPageResponse(BaseModel):
    """GET /replay/{game_id}/events response."""
    events: list[TranscriptEventResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class BoardStateSnapshot(BaseModel):
    """Reconstructed board state at a specific event position."""
    battlefield: list[dict]       # permanents with power/toughness, tapped, counters
    player_life: dict[str, int]   # {player_name: life_total}
    hand_sizes: dict[str, int]    # {player_name: hand_size}
    graveyard_top: dict[str, Optional[str]]  # {player_name: top_card_name or null}
    stack_size: int               # number of objects on the stack

class StepResponse(BaseModel):
    """POST /replay/{game_id}/step response."""
    event: TranscriptEventResponse
    board_state: BoardStateSnapshot
    direction: str                # "forward" | "backward"
    from_seq: int                 # the seq we stepped from
    to_seq: int                   # the seq we arrived at

class PhaseSegment(BaseModel):
    """One phase in the timeline."""
    turn: int
    phase: str
    step: Optional[str] = None
    event_count: int
    first_event_seq: int
    last_event_seq: int

class TimelineResponse(BaseModel):
    """GET /replay/{game_id}/timeline response."""
    game_id: str
    total_events: int
    turns: list[dict[int, list[PhaseSegment]]]  # [{turn_num: [phase_segments]}]
```

### Request Model (Pydantic v2)

```python
class StepRequest(BaseModel):
    """POST /replay/{game_id}/step request body."""
    direction: str = Field(..., description="forward or backward")
    from_event_seq: int = Field(default=0, ge=0, description="Current event sequence number (0 = before game starts)")

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("forward", "backward"):
            raise ValueError(f"direction must be 'forward' or 'backward', got '{v}'")
        return v
```

---

## Engine Module Design (`mtg_engine/export/replay_engine.py`)

### Public API

```python
def get_replay_info(store: GameExportStore) -> dict:
    """Return replay metadata: game_id, total_events, turns, winner, loser, format."""

def paginate_events(
    store: GameExportStore, page: int = 1, per_page: int = 25
) -> tuple[list[dict], int]:
    """Return (events_page, total_count) for paginated transcript access."""

def step_to_event(
    store: GameExportStore, direction: str, from_seq: int
) -> tuple[dict, dict] | None:
    """Step forward/backward one event. Returns (event_dict, board_state_dict) or None if out of bounds."""

def build_timeline(store: GameExportStore) -> list[dict]:
    """Return condensed timeline grouped by turn/phase with event counts."""

def reconstruct_board_state_at(
    store: GameExportStore, target_seq: int
) -> dict:
    """Reconstruct board state at the given event sequence number using snapshot anchors + incremental replay."""
```

### Board State Reconstruction Algorithm

The `reconstruct_board_state_at(target_seq)` function works as follows:

1. **Find nearest snapshot anchor**: Search `store.snapshots.get_all()` for the snapshot whose `action_taken` corresponds to an event at or before `target_seq`. If no snapshot exists, start from a minimal initial state (20 life each, empty battlefield).

2. **Deserialize snapshot GameState**: Parse `snapshot.game_state` dict into working copies of player states and battlefield permanents. Extract:
   - Battlefield permanents with power/toughness, tapped status, counters
   - Player life totals
   - Hand sizes (not card identities — transcript doesn't record which specific cards are in hand)
   - Graveyard contents (top N visible from zone_change events)
   - Stack size

3. **Incremental replay**: For each transcript event between the snapshot anchor and `target_seq`:
   - `zone_change`: Move card from one zone to another in reconstructed state
   - `life_change`: Apply delta to player life total
   - `damage`: Track damage marked on permanents (may trigger state changes)
   - `draw`: Increment hand size for the drawing player, decrement library
   - `cast`/`resolve`: Update stack size (+1/-1)
   - Other events: No board state change needed

4. **Return**: Structured dict matching `BoardStateSnapshot` model

### Timeline Generation Algorithm

The `build_timeline(store)` function groups transcript entries by turn and phase:

1. Iterate all transcript entries in sequence order.
2. Group consecutive entries that share the same `(turn, phase)` tuple.
3. For each group, record: turn number, phase name, event count, first/last event seq.
4. Return as list of `PhaseSegment` dicts sorted by (turn, phase).

---

## API Contract

### Endpoint 1: `GET /replay/{game_id}/info`

**Response**: HTTP 200
```json
{
  "data": {
    "game_id": "abc-123",
    "total_events": 147,
    "turns": 12,
    "winner": "p1",
    "loser": "p2",
    "format": "standard"
  }
}
```

**Error**: HTTP 404 if game not in export store.

### Endpoint 2: `GET /replay/{game_id}/events?page=1&per_page=25`

**Query params**: `page` (default 1, min 1), `per_page` (default 25, max 100)

**Response**: HTTP 200
```json
{
  "data": {
    "events": [
      {"seq": 1, "event_type": "phase_change", "description": "Turn 1: entering beginning — upkeep", ...},
      ...
    ],
    "total": 147,
    "page": 1,
    "per_page": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

### Endpoint 3: `POST /replay/{game_id}/step`

**Request Body**:
```json
{
  "direction": "forward",
  "from_event_seq": 0
}
```

**Response**: HTTP 200
```json
{
  "data": {
    "event": {"seq": 1, "event_type": "phase_change", ...},
    "board_state": {
      "battlefield": [],
      "player_life": {"p1": 20, "p2": 20},
      "hand_sizes": {"p1": 7, "p2": 7},
      "graveyard_top": {"p1": null, "p2": null},
      "stack_size": 0
    },
    "direction": "forward",
    "from_seq": 0,
    "to_seq": 1
  }
}
```

**Error**: HTTP 400 if `from_event_seq` is out of bounds or direction would go past start/end.

### Endpoint 4: `GET /replay/{game_id}/timeline`

**Response**: HTTP 200
```json
{
  "data": {
    "game_id": "abc-123",
    "total_events": 147,
    "turns": [
      {"turn": 1, "phases": [
        {"phase": "beginning", "step": "upkeep", "event_count": 3, "first_event_seq": 1, "last_event_seq": 3},
        {"phase": "beginning", "step": "draw", "event_count": 2, "first_event_seq": 4, "last_event_seq": 5}
      ]},
      ...
    ]
  }
}
```

---

## Task Breakdown (Ordered by Dependency)

### Task 1: Replay Engine Module (`mtg_engine/export/replay_engine.py`)
- **Files**: New file `mtg_engine/export/replay_engine.py`
- **Description**: Implement pure functions for replay info, event pagination, board state reconstruction, and timeline generation. The engine takes a `GameExportStore` as input and returns structured dicts — no FastAPI dependencies. Board state reconstruction uses snapshot anchors with incremental transcript replay between snapshots.
- **Acceptance Criteria**:
  - `get_replay_info()` returns correct metadata from store data
  - `paginate_events()` correctly slices transcript entries with proper has_next/has_prev flags
  - `step_to_event()` moves forward/backward one event and reconstructs board state
  - `build_timeline()` groups events by turn/phase with accurate counts
  - Board state reconstruction handles zone_change, life_change, damage, draw events

### Task 2: API Router (`mtg_engine/api/routers/replay.py`)
- **Files**: New file `mtg_engine/api/routers/replay.py`
- **Description**: Create FastAPI router with 4 endpoints. Define Pydantic request/response models. Handle 404 for missing games, 400 for invalid step requests. Follow existing patterns from `export.py` (store access via `get_export_store()`, error handling).
- **Acceptance Criteria**:
  - All 4 endpoints return HTTP 200 with correct response structure
  - Missing game returns HTTP 404 with `{error, error_code}` pattern
  - Invalid step direction or out-of-bounds seq returns HTTP 400
  - Pagination params validated (page >= 1, per_page <= 100)

### Task 3: Wire Router into App (`mtg_engine/api/main.py`)
- **Files**: Modify `mtg_engine/api/main.py`
- **Description**: Import new router and mount via `app.include_router(replay.router)`. Follow existing import/mount pattern.
- **Acceptance Criteria**: `GET /health` still works, all 4 replay endpoints accessible

### Task 4: Test Suite (`tests/api/test_replay.py`)
- **Files**: New file `tests/api/test_replay.py`
- **Description**: Create test suite with >=8 tests. Use same fixture pattern as `test_export.py` (clear_state autouse fixture, `_create_game()` helper). Tests cover info retrieval, stepping, pagination, timeline, board state accuracy, 404 handling, and multi-turn replay.
- **Acceptance Criteria**: All tests pass, no regressions in existing test suite

---

## Testing Strategy

### Test Matrix (>=8 tests)

| # | Test Name | What It Verifies | Acceptance Criterion |
|---|-----------|-----------------|---------------------|
| 1 | `test_replay_info_returns_metadata` | `/info` returns game_id, total_events, turns, winner | Replay info retrieval |
| 2 | `test_step_forward_through_events` | POST `/step` with direction=forward advances seq by 1 | Forward stepping |
| 3 | `test_step_backward_through_events` | POST `/step` with direction=backward retreats seq by 1 | Backward stepping |
| 4 | `test_events_pagination_first_page` | GET `/events?page=1` returns first page with has_prev=false, has_next=true | Pagination of events |
| 5 | `test_timeline_groups_by_turn_phase` | GET `/timeline` returns phases grouped by turn with correct event counts | Timeline generation |
| 6 | `test_board_state_reconstruction_accuracy` | Board state at a known point matches expected life totals and battlefield | Board state accuracy |
| 7 | `test_replay_404_for_deleted_game` | Replay endpoints return 404 when game is not in export store | Game-not-found handling |
| 8 | `test_multi_turn_replay_step_through` | Stepping through a multi-turn game produces correct sequence of events and state changes | Multi-turn replay |

### Test Patterns (following existing conventions)

```python
import pytest
from fastapi.testclient import TestClient
from mtg_engine.api.main import app
from mtg_engine.api.game_manager import get_manager
from mtg_engine.export.store import _store as export_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    get_manager()._games.clear()
    export_store.clear()
    yield
    get_manager()._games.clear()
    export_store.clear()

def _create_game(seed: int = 1) -> str:
    resp = client.post("/game", json={
        "player1_name": "p1", "player2_name": "p2",
        "deck1": ["Forest"] * 60, "deck2": ["Forest"] * 60,
        "seed": seed,
    })
    assert resp.status_code == 200
    return resp.json()["data"]["game_id"]

def test_replay_info_returns_metadata():
    game_id = _create_game()
    # Advance game to generate some transcript entries
    # ... (use existing game advancement pattern)
    resp = client.get(f"/replay/{game_id}/info")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "game_id" in data
    assert "total_events" in data
    assert data["total_events"] >= 0

def test_step_forward_through_events():
    game_id = _create_game()
    # Advance game to generate events...
    resp = client.post(f"/replay/{game_id}/step", json={
        "direction": "forward",
        "from_event_seq": 0,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["to_seq"] == 1
    assert data["event"]["seq"] == 1

def test_replay_404_for_deleted_game():
    game_id = _create_game()
    client.delete(f"/game/{game_id}")
    resp = client.get(f"/replay/{game_id}/info")
    assert resp.status_code == 404
```

---

## Potential Risks

1. **Risk**: Board state reconstruction is lossy — transcript events don't capture full state (e.g., which specific cards are in hand, exact stack contents). → **Mitigation**: Use snapshot anchors for accuracy where available; document limitations in API response; hand_sizes and graveyard_top provide approximate visibility without claiming perfect fidelity.

2. **Risk**: Game has no snapshots (very early game or snapshot recorder not wired). → **Mitigation**: Fall back to minimal initial state + incremental replay from transcript events. The reconstruction will be less accurate but still functional for navigation.

3. **Risk**: Large games with thousands of events make step-by-step reconstruction slow. → **Mitigation**: Snapshot anchors limit the replay window. Most steps only need to apply a handful of events between snapshots. If performance becomes an issue, can add caching layer later.

4. **Risk**: `from_event_seq=0` edge case — no event 0 exists (seq starts at 1). → **Mitigation**: Treat seq=0 as "before game starts" returning initial board state with no event. Forward from 0 returns event 1.

5. **Risk**: Step backward from seq=1 would go to seq=0 which is valid (pre-game state), but step backward from seq=0 should return error. → **Mitigation**: Return HTTP 400 with descriptive message when stepping backward past the beginning.

---

## Handoff to Implementer

**Design Document**: `specs/038-gap-analysis/APP-03-design.md` (this file)
**User Story**: `.opencode/discovery/story-app03-game-replay.md`
**Estimated Complexity**: Medium
**Key Files**:
1. `mtg_engine/export/replay_engine.py` — Core reconstruction engine (new)
2. `mtg_engine/api/routers/replay.py` — API endpoints (new)
3. `tests/api/test_replay.py` — Test suite (new)
4. `mtg_engine/api/main.py` — Router mounting (modify)

**Start With**: Task 1 — Implement the replay engine module (`replay_engine.py`). The board state reconstruction algorithm is the most complex piece; get it working before wiring up API endpoints.

**Acceptance Criteria**:
- [ ] `GET /replay/{game_id}/info` returns `{ game_id, total_events, turns, winner, loser, format }`
- [ ] `GET /replay/{game_id}/events?page=1&per_page=25` returns paginated events with has_next/has_prev
- [ ] `POST /replay/{game_id}/step` accepts direction + from_event_seq, returns event + board state
- [ ] Board state includes battlefield permanents, player life, hand sizes, graveyard top, stack size
- [ ] `GET /replay/{game_id}/timeline` returns condensed timeline grouped by turn/phase
- [ ] Data sourced from in-memory export store — no MongoDB dependency
- [ ] Deleted games return HTTP 404
- [ ] Event descriptions are human-readable (from TranscriptRecorder)
- [ ] >=8 tests covering all axes

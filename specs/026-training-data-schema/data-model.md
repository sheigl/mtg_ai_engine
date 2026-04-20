# Data Model: Training Data Schema (026)

## Collection: `games`

Top-level game metadata. One document per game.

```json
{
  "_id": "game-uuid",
  "game_id": "game-uuid",
  "format": "standard",
  "player_1": { "name": "Alice", "type": "llm" },
  "player_2": { "name": "Bob",   "type": "heuristic" },
  "has_human_player": false,
  "created_at": "2026-04-20T10:00:00Z",
  "completed_at": "2026-04-20T10:05:00Z",
  "is_complete": true,
  "outcome": {
    "winner": "Alice",
    "winning_player": "Alice",
    "reason": "life_total",
    "total_turns": 12,
    "snapshot_count": 47,
    "transcript_length": 310
  }
}
```

**Validation rules:**
- `game_id` is a UUID string (matches `_id`)
- `player_1.type` / `player_2.type` ∈ `{"llm", "heuristic", "human"}`
- `outcome` is `null` until game completes

---

## Collection: `decisions`

Primary training unit. One document per priority grant.

```json
{
  "_id": "snapshot-uuid",
  "game_id": "game-uuid",
  "snapshot_id": "snapshot-uuid",
  "sequence_number": 7,
  "turn": 3,
  "phase": "main",
  "step": "precombat_main",
  "active_player": "Alice",

  "board_state": { /* full serialized GameState dict */ },
  "legal_actions": [ /* list of LegalAction dicts */ ],
  "action_taken": { /* single LegalAction dict, or null */ },
  "action_taken_by": "Alice",

  "llm_reasoning": {
    "entry_id": "debug-entry-uuid",
    "prompt": "...",
    "thinking": "...",
    "response": "...",
    "rating": "good",
    "player_annotation": null,
    "player_rating_override": null
  },

  "observer_evaluation": {
    "entry_id": "observer-entry-uuid",
    "related_entry_id": "debug-entry-uuid",
    "prompt": "...",
    "thinking": "...",
    "response": "...",
    "rating": "suboptimal",
    "explanation": "Should have held priority",
    "alternative": "Cast Lightning Bolt instead"
  },

  "outcome_context": {
    "winner": "Alice",
    "winning_player": "Alice",
    "total_turns": 12,
    "active_player_won": true
  },

  "created_at": "2026-04-20T10:01:23Z"
}
```

**Validation rules:**
- `_id` == `snapshot_id` (UUID string)
- `llm_reasoning` is `null` when active player is heuristic or human
- `observer_evaluation` is `null` when no observer is configured
- `outcome_context` is `null` until game ends; backfilled on game completion
- `action_taken` may be `null` (pass-priority decision)
- `sequence_number` is monotonic per `game_id`, starting at 1

**Indexes:**
```
{ game_id: 1, sequence_number: 1 }        — list decisions in order
{ game_id: 1, active_player: 1 }          — per-player training slices
{ "outcome_context.active_player_won": 1 } — win/loss stratified sets
{ "observer_evaluation.rating": 1 }        — quality filtering
```

---

## Collection: `rules_qa`

One document per Q&A pair generated during a game.

```json
{
  "_id": "qa-uuid",
  "qa_id": "qa-uuid",
  "game_id": "game-uuid",
  "decision_id": "snapshot-uuid",
  "question": "Lightning Bolt has split second...",
  "answer": "No. While... (CR 702.61b)",
  "turn": 3,
  "trigger_event": "split_second",
  "cards_involved": ["Lightning Bolt"],
  "rules_cited": ["702.61b"]
}
```

**Validation rules:**
- `decision_id` links to the `decisions._id` of the priority grant during which the Q&A was triggered
- `decision_id` may be `null` if Q&A is triggered outside a priority grant (rare)

**Indexes:**
```
{ game_id: 1, decision_id: 1 }   — fetch Q&A context for a specific decision
```

---

## Collection: `transcript`

One document per transcript event. Used for full game replay.

```json
{
  "_id": "auto-objectid",
  "game_id": "game-uuid",
  "sequence_number": 42,
  "seq": 42,
  "event_type": "zone_change",
  "description": "Lightning Bolt moves from hand to graveyard (Alice)",
  "data": { "card_name": "Lightning Bolt", "from_zone": "hand", "to_zone": "graveyard", "player": "Alice" },
  "turn": 3,
  "phase": "main",
  "step": "precombat_main"
}
```

**Indexes:**
```
{ game_id: 1, sequence_number: 1 }   — ordered replay
```

---

## Updated Pydantic Models

### `DebugEntry` (mtg_engine/models/debug.py)

New fields added:
```python
snapshot_id: str | None = None          # FR-009: correlation key to decisions doc
related_entry_id: str | None = None     # FR-010: observer entry points to player entry
```

### `QAPair` (mtg_engine/export/rules_qa.py)

New field added:
```python
decision_id: str | None = None          # FR-006: links Q&A to the decision that prompted it
```

---

## State Transitions: Decision Document

```
[snapshot finalized]
  → upsert decisions doc: game_id, snapshot_id, sequence_number, turn, phase, step,
                          active_player, board_state, legal_actions, action_taken,
                          action_taken_by, created_at
  → llm_reasoning: null (default)
  → observer_evaluation: null (default)
  → outcome_context: null (default)

[player DebugEntry arrives, is_complete=True, entry_type=prompt_response]
  → $set decisions.llm_reasoning = { entry_id, prompt, thinking, response, rating, ... }

[observer DebugEntry arrives, is_complete=True, entry_type=commentary]
  → $set decisions.observer_evaluation = { entry_id, related_entry_id, prompt, thinking,
                                           response, rating, explanation, alternative }

[game ends]
  → $set decisions.outcome_context = { winner, winning_player, total_turns, active_player_won }
    on ALL decisions where game_id matches

[annotate/rerate]
  → $set decisions.llm_reasoning.player_annotation / .player_rating_override
    using snapshot_id to locate document
```

---

## GameExportStore Changes

New property:
```python
current_snapshot_id: str | None = None  # updated by store on each record_snapshot()
```

`store.snapshots.record_snapshot()` already returns the `Snapshot` object (which has `snapshot_id`). The caller (`game.py` router) sets `store.current_snapshot_id = snap.snapshot_id` and returns `snapshot_id` in the API response.

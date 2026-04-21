# Data Model: Skip Empty Phases

**Feature**: 029-skip-empty-phases
**Date**: 2026-04-21

## Entities

### PhaseSkipDecision (Internal / Not Persisted)

Represents the evaluation result for whether a phase should be skipped.

| Field | Type | Description |
|-------|------|-------------|
| phase | str | Phase name (e.g., "beginning", "precombat_main") |
| step | str | Step name (e.g., "upkeep", "draw", "main") |
| turn | int | Turn number when evaluation occurred |
| active_player | str | Name of the active player |
| should_skip | bool | True if phase has no non-pass actions for any player |
| reason | str | Human-readable reason for skip decision |

### TranscriptEntry Extension

The existing `TranscriptEntry` model supports new `event_type` values without schema changes.

**New event_type**: `"phase_skipped"`

**Data payload for phase_skipped entries**:

```json
{
  "turn": 5,
  "phase": "precombat_main",
  "step": "main",
  "active_player": "Player 1",
  "reason": "no_actions_available"
}
```

## State Transitions

### Phase Advancement Flow (Modified)

```
Current Phase
    |
    v
advance_step()
    |
    v
begin_step()  -- applies start-of-step effects, may create triggers
    |
    v
SKIP CHECK (NEW)
    |-- Evaluate: does ANY player have non-pass actions?
    |-- Check: pending triggers, pending choices, stack objects
    |
    +-- YES --> Grant priority (existing behavior)
    |
    +-- NO  --> Record phase_skipped in transcript
          |
          v
    advance_step() again (recursive, with depth limit)
```

### Skip Prevention Conditions

A phase is NEVER skipped if ANY of the following are true:

1. `gs.stack` is non-empty (stack objects require resolution)
2. `gs.pending_triggers` has items (triggers create choices)
3. Any `gs.pending_*_choice` is set (scry, surveil, tutor, discard, ward, echo, cascade, dredge, proliferate)
4. `gs.pending_echo_payment` is set
5. Current step is `UNTAP` (no priority granted anyway)
6. Active player has non-pass legal actions
7. Non-active player has non-pass legal actions (if they were to receive priority)

## No Database Changes

This feature operates entirely on in-memory game state. No persistent storage entities are modified.

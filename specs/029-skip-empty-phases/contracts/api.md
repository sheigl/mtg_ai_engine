# API Contracts: Skip Empty Phases

**Feature**: 029-skip-empty-phases
**Date**: 2026-04-21

## Overview

This feature requires **no new API endpoints** and **no changes to existing request/response contracts**.

The skip logic is entirely internal to the game engine's turn manager. Clients (AI loops, human frontends) continue to call `GET /game/{game_id}/legal-actions` and receive the same response format. The only observable difference is that phases with no actions are never returned in the `legal-actions` response — the game transparently advances to the next phase with actions.

## Transcript Output Changes

### New Event Type: `phase_skipped`

Transcript entries now include a new `event_type` value.

**Example transcript entry**:

```json
{
  "seq": 42,
  "event_type": "phase_skipped",
  "description": "Turn 5: precombat_main — main skipped (no actions available)",
  "data": {
    "turn": 5,
    "phase": "precombat_main",
    "step": "main",
    "active_player": "Player 1",
    "reason": "no_actions_available"
  },
  "turn": 5,
  "phase": "precombat_main",
  "step": "main"
}
```

### Backward Compatibility

- Existing `phase_change` entries are unchanged
- New `phase_skipped` entries follow the same `TranscriptEntry` schema
- Consumers that ignore unknown `event_type` values will safely ignore skipped phase entries
- Consumers that process all entries will see the new type

## No Endpoint Changes

| Endpoint | Change | Notes |
|----------|--------|-------|
| `GET /game/{id}/legal-actions` | None | Transparent skip — clients never see skipped phases |
| `POST /game/{id}/pass` | None | Still works normally; skip happens before priority grant |
| `GET /game/{id}` | None | Game state reflects current non-skipped phase |
| `GET /export/{id}/transcript` | None | Response includes new `phase_skipped` entries |

# Quickstart: Skip Empty Phases

**Feature**: 029-skip-empty-phases
**Date**: 2026-04-21

## No Setup Required

This feature is automatic and requires no configuration. Once deployed, the game engine will skip phases transparently.

## Verifying the Feature

### 1. Check Transcript for Skipped Phases

Create a game where both players have no cards in hand and no permanents with activated abilities. Query the transcript after several turns:

```bash
# After creating a game and letting it run for a few turns
curl http://localhost:8000/export/{game_id}/transcript | python -m json.tool
```

Look for entries with `event_type: "phase_skipped"`:

```json
{
  "seq": 15,
  "event_type": "phase_skipped",
  "description": "Turn 3: precombat_main — main skipped (no actions available)",
  "data": {
    "turn": 3,
    "phase": "precombat_main",
    "step": "main",
    "active_player": "Player 1",
    "reason": "no_actions_available"
  }
}
```

### 2. Observe Faster Gameplay

Games with long stretches of no available actions (e.g., both players top-decking with empty boards) will advance much faster. The AI decision count in the game summary will be lower because skipped phases don't generate decisions.

### 3. Confirm Phases Are Not Skipped When Actions Exist

Create a game where a player has a land in hand. The Main Phase should NOT be skipped — the player should receive priority normally and be able to play the land.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Phases not skipped when expected | Pending triggers or choices exist | Check transcript for trigger/choice entries before the phase — triggers prevent skipping |
| Transcript missing skipped phases | Transcript not being recorded | Verify `verbose=True` was set on game creation |
| All phases skipped | Both players truly have no actions | Expected behavior in endgame states with empty boards/hands |

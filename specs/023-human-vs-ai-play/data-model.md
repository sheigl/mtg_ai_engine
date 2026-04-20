# Data Model: Human vs AI Gameplay

**Branch**: `023-human-vs-ai-play` | **Date**: 2026-04-18

## Existing Entities (no changes required)

### GameState (`mtg_engine/models/game.py:254`)
All human player actions update GameState via the same existing endpoints. No new fields are required. The frontend uses existing fields:
- `priority_holder: str` — to detect when it is the human's turn
- `phase / step` — to determine which action categories are legal
- `players[*].hand` — to render the human's hand
- `players[*].mana_pool` — to display available mana
- `battlefield` — to render permanents and select attackers/blockers
- `stack` — to display pending spells for response windows
- `is_game_over / winner` — to trigger win/loss display
- `pending_*` fields — to detect mid-resolution choices

### LegalActionsResponse (returned by `GET /game/{id}/legal-actions`)
Existing shape. Frontend uses `priority_player` to detect human turns, and `legal_actions[]` to determine which cards/actions to highlight.

---

## New Entities

### HumanGameRequest (new — request body for `POST /human-game`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player1_type` | `"human" \| "ai" \| "heuristic"` | yes | Type for seat 1 |
| `player2_type` | `"human" \| "ai" \| "heuristic"` | yes | Type for seat 2 |
| `player1_deck` | `list[str]` | yes | Card names for player 1 |
| `player2_deck` | `list[str]` | yes | Card names for player 2 |
| `player1_name` | `str` | no | Defaults to `"Player1"` |
| `player2_name` | `str` | no | Defaults to `"Player2"` |
| `format` | `"standard" \| "commander"` | no | Defaults to `"standard"` |
| `ai_model` | `str` | no | LLM model for AI seats (ignored for human/heuristic) |
| `observer_model` | `str` | no | LLM model for observer commentary |
| `observer_enabled` | `bool` | no | Defaults to `true` |

**Constraint**: At least one seat must be `"human"`. (1v1 only; exactly 2 players.)

### HumanGameResponse (returned by `POST /human-game`)

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `str` | UUID for the new game |
| `human_player_name` | `str` | Name assigned to human seat(s) |
| `redirect_url` | `str` | Frontend URL for the human game board: `/ui/human-game/{game_id}` |

---

## Frontend State Model

### `useLegalActions` hook state

| Field | Type | Description |
|-------|------|-------------|
| `isMyTurn` | `bool` | `priority_player === humanPlayerName` |
| `legalActions` | `LegalAction[]` | All legal actions for current priority holder |
| `hasPendingChoice` | `bool` | Any `pending_*` field is non-null in GameState |
| `pendingChoiceType` | `string \| null` | E.g., `"scry"`, `"discard"`, `"target"` |

### ActionSelection (ephemeral UI state in `HumanGameBoard.tsx`)

| Field | Type | Description |
|-------|------|-------------|
| `selectedAttackers` | `Set<string>` | Permanent IDs toggled as attackers |
| `selectedBlockers` | `Map<string, string>` | Blocker permanent ID → attacker permanent ID |
| `pendingCast` | `CastAction \| null` | Spell being configured (targets, modal choice) |
| `autoPassPriority` | `bool` | Whether to skip response windows with no instant-speed actions |

---

## State Transitions

### Human Turn Flow
```
IDLE (AI turn)
  ↓ priority_player === humanName
HUMAN_PRIORITY (show action panel, highlight legal cards)
  ↓ user clicks card / button
ACTION_PENDING (disable UI, submit action to API)
  ↓ API responds 200, game state advances
IDLE (AI turn or next human priority window)
```

### Mid-Resolution Choice Flow
```
HUMAN_PRIORITY
  ↓ GameState has pending_* field set
CHOICE_PENDING (show modal for choice type)
  ↓ user selects / confirms
ACTION_PENDING (submit choice action to API)
  ↓ API responds 200
HUMAN_PRIORITY or IDLE
```

### Attacker Declaration Flow
```
HUMAN_PRIORITY (combat: declare-attackers step)
  ↓ user clicks creatures to toggle
ATTACKERS_SELECTED (show "Confirm Attackers" button)
  ↓ user clicks confirm
ACTION_PENDING → POST /declare-attackers
  ↓ 200 OK
IDLE (AI declares blockers or engine advances)
```

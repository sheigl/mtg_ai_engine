# Implementation Plan: Human vs AI Gameplay

**Branch**: `023-human-vs-ai-play` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/023-human-vs-ai-play/spec.md`

## Summary

Enable a human player to play MTG against an AI or Heuristic opponent entirely through the browser UI. The backend exposes a new `POST /human-game` endpoint that starts a hybrid game loop — the loop drives AI turns automatically and idles when it is the human's turn. The frontend detects human-priority turns via the existing `GET /game/{id}/legal-actions` polling endpoint and renders interactive controls (hand clicking, attacker/blocker selection, target modals) on top of the existing observer game board. The AI observer, verbose logging, and all existing debugging tools remain completely unchanged.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, Pydantic v2 (backend); React 18, TanStack Query v5 (frontend) — all existing, no new deps  
**Storage**: In-memory GameState (existing GameManager) — no persistence changes  
**Testing**: pytest (backend), manual browser testing (frontend)  
**Target Platform**: Desktop/tablet browsers, Linux server  
**Project Type**: Web application (FastAPI backend + React frontend)  
**Performance Goals**: Human priority window detects and displays within 750ms of engine state change; AI actions resolve within 5 seconds  
**Constraints**: Zero changes to existing observer, AI game loop, or action endpoints; no new dependencies  
**Scale/Scope**: 1-vs-1 games only; single human seat

## Constitution Check

No constitution file exists for this project. Proceeding without gate checks.

## Project Structure

### Documentation (this feature)

```text
specs/023-human-vs-ai-play/
├── plan.md              # This file
├── research.md          # Research decisions
├── data-model.md        # Entity definitions
├── quickstart.md        # Developer guide
├── contracts/
│   └── human_game_api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# Backend (Python 3.11 + FastAPI)
mtg_engine/api/
├── main.py                    # MODIFIED: register human_game router
└── routers/
    ├── human_game.py          # NEW: POST /human-game endpoint
    ├── game.py                # UNCHANGED
    └── ai_game.py             # UNCHANGED

ai_client/
├── hybrid_game_loop.py        # NEW: HybridGameLoop (extends GameLoop)
├── game_loop.py               # UNCHANGED
└── heuristic_player.py        # UNCHANGED

tests/api/
└── test_human_game.py         # NEW: endpoint + hybrid loop tests

# Frontend (React 18 + TypeScript)
frontend/src/
├── App.tsx                    # MODIFIED: add human-game routes
├── pages/
│   ├── GameList.tsx           # MODIFIED: add "Play vs AI" button
│   ├── HumanGameCreator.tsx   # NEW: game creation form
│   └── HumanGameBoard.tsx     # NEW: interactive game board
├── components/
│   ├── ActionPanel.tsx        # NEW: Pass Priority, End Turn, Confirm buttons
│   ├── InteractiveHand.tsx    # NEW: hand with clickable card actions
│   ├── AttackerSelector.tsx   # NEW: creature toggle for attack step
│   ├── BlockerAssigner.tsx    # NEW: blocker assignment for block step
│   ├── ChoiceModal.tsx        # NEW: modal for targets, modes, scry, discard
│   └── GameResultOverlay.tsx  # NEW: win/loss end screen
└── hooks/
    ├── useLegalActions.ts     # NEW: poll /legal-actions, expose isMyTurn
    └── useHumanAction.ts      # NEW: submit action to backend, loading state
```

**Structure Decision**: Web application layout (separate backend and frontend directories). Backend follows existing router-per-feature pattern. Frontend follows existing component/hook/page separation.

## Implementation Phases

### Phase A: Backend — Hybrid Game Loop + New Endpoint

**Goal**: `POST /human-game` creates a game where the AI drives its own turns and waits when the human holds priority.

**1. `ai_client/hybrid_game_loop.py`**

Subclass `GameLoop`. Override the main run loop to check `priority_player` before each action:
```python
if legal_data["priority_player"] == self.human_player_name:
    time.sleep(0.5)
    continue  # skip — human will submit action via frontend
```
All other logic (AI decides, submits, observer, verbose logging) remains identical to `GameLoop`.

Key details:
- `human_player_name: str` passed at construction
- Existing `GameLoop.run()` logic reused for AI turns
- Observer thread and verbose logging are unchanged — they observe `GameState` transitions regardless of who submits them

**2. `mtg_engine/api/routers/human_game.py`**

```python
@router.post("/human-game")
async def create_human_game(req: HumanGameRequest) -> HumanGameResponse:
    # validate at least one seat is "human"
    # create game via GameManager (same as ai_game.py)
    # start HybridGameLoop thread for the AI seat
    # return { game_id, human_player_name, redirect_url }
```

`HumanGameRequest` / `HumanGameResponse` Pydantic models (see data-model.md).

**3. `mtg_engine/api/main.py`**

Register the `human_game` router alongside existing routers.

---

### Phase B: Frontend — Game Creation

**Goal**: Human can navigate to a creation form, configure opponent type and decks, and start a game.

**1. `frontend/src/pages/HumanGameCreator.tsx`**

- Player type selectors (Human / AI / Heuristic) per seat
- Deck selection (reuse existing deck selection pattern)
- "Start Game" button → `POST /human-game` → navigate to `/ui/human-game/{game_id}`

**2. `frontend/src/pages/GameList.tsx`** (modified)

Add a prominent "Play vs AI" button linking to `/ui/human-game/create`.

**3. `frontend/src/App.tsx`** (modified)

Add routes:
- `/ui/human-game/create` → `HumanGameCreator`
- `/ui/human-game/:gameId` → `HumanGameBoard`

---

### Phase C: Frontend — Interactive Game Board (Core Loop)

**Goal**: Human can play a full turn (land, spell, attack, pass) through the UI.

**1. `frontend/src/hooks/useLegalActions.ts`**

Polls `GET /game/{id}/legal-actions` every 750ms. Exposes:
- `isMyTurn: boolean` — `priority_player === humanPlayerName`
- `legalActions: LegalAction[]`
- `legalActionsByCard: Map<string, LegalAction[]>` — keyed by card_id for fast lookup

**2. `frontend/src/hooks/useHumanAction.ts`**

- `submitAction(actionType: string, payload: object): Promise<void>`
- Manages `isPending` state to disable UI during submission
- On success: invalidates React Query cache for game state + legal actions

**3. `frontend/src/pages/HumanGameBoard.tsx`**

Builds on the existing observer game board view. When `isMyTurn`:
- Renders `InteractiveHand` instead of read-only hand
- Renders `AttackerSelector` overlay during `step === DECLARE_ATTACKERS`
- Renders `BlockerAssigner` overlay during `step === DECLARE_BLOCKERS`
- Renders `ActionPanel` footer/sidebar with context-sensitive buttons
- Renders `ChoiceModal` when pending choice detected
- Checks `is_game_over` → renders `GameResultOverlay`

When not `isMyTurn`: renders exactly the same as the existing observer board.

**4. `frontend/src/components/InteractiveHand.tsx`**

Displays the human's hand cards. Cards that appear in `legalActionsByCard` get a highlighted border and are clickable. Click:
- Land card → `POST /play-land` directly
- Spell → opens `ChoiceModal` for target/mode selection if needed, then `POST /cast`

**5. `frontend/src/components/ActionPanel.tsx`**

Context-sensitive buttons based on phase/step:
- Always: "Pass Priority" → `POST /pass`
- Main phase with land available: "Play Land" (as fallback if card click not used)
- `DECLARE_ATTACKERS` step: "Confirm Attackers" → `POST /declare-attackers`
- `DECLARE_BLOCKERS` step: "Confirm Blocks" → `POST /declare-blockers`
- Settings toggle: "Auto-pass Priority" checkbox (localStorage-persisted)

---

### Phase D: Frontend — Interaction Details

**Goal**: Target selection, modal spells, mid-resolution choices, blocker assignment.

**1. `frontend/src/components/ChoiceModal.tsx`**

Detects choice type from legal actions list:
- **Target selection**: shows list of valid targets (permanent names / player names) as clickable list
- **Modal spell modes**: shows mode options (e.g., Charm modes) as radio buttons
- **Scry**: shows top N cards, "put on top / put on bottom" buttons
- **Discard**: shows hand cards, click to discard
- **X value**: numeric input for X spells

**2. `frontend/src/components/AttackerSelector.tsx`**

Overlay on the human's battlefield during `DECLARE_ATTACKERS` step. Each creature gets a toggle (click to select as attacker, click again to deselect). Selected creatures get a red attack border highlight.

**3. `frontend/src/components/BlockerAssigner.tsx`**

During `DECLARE_BLOCKERS` step. Shows opponent's attacking creatures and allows assigning blockers by clicking blocker then clicking attacker.

**4. `frontend/src/components/GameResultOverlay.tsx`**

Full-screen overlay when `is_game_over`:
- "Victory!" or "Defeat" header
- Reason (life total, concede, etc.) from game log
- "Play Again" button → `/ui/human-game/create`
- "Watch Replay" button → `/ui/game/{id}` (existing observer)

---

### Phase E: Testing

**1. `tests/api/test_human_game.py`** (new)

- `POST /human-game` with valid request returns `game_id` and starts game
- `POST /human-game` with no human seat returns 422
- Human player can submit `POST /game/{id}/pass` when holding priority
- Human player cannot submit action when AI holds priority (422)
- Observer commentary still fires during human vs AI game
- Verbose log includes human player actions

**2. Manual browser test checklist**:
- [ ] Full turn: land drop + spell cast + attack + pass
- [ ] Response window: counterspell during AI's turn
- [ ] Blocker assignment with multiple attackers
- [ ] Mid-resolution target selection
- [ ] Auto-pass priority toggle
- [ ] Win/loss overlay and "Play Again" flow
- [ ] Observer commentary panel still shows commentary during human game

## Complexity Tracking

No constitution violations. All components are minimal extensions of existing patterns.

| Component | Complexity | Reason |
|-----------|-----------|--------|
| HybridGameLoop | Low | 10-line change to existing GameLoop — just add `if priority_player == human: sleep+continue` |
| POST /human-game | Low | Same structure as `ai_game.py`, just instantiates HybridGameLoop |
| useLegalActions hook | Low | Same pattern as existing useGameState hook |
| InteractiveHand | Medium | Card-click → action mapping requires legal action lookup |
| ChoiceModal | Medium | Multiple choice types require branching UI |
| AttackerSelector/BlockerAssigner | Medium | Multi-select UI with confirmation step |
| HumanGameBoard | Medium | Composing the above; most complexity is in sub-components |

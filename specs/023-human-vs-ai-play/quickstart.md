# Quickstart: Human vs AI Gameplay

**Branch**: `023-human-vs-ai-play` | **Date**: 2026-04-18

## How It Works

A human player creates a game via the UI, chooses their deck and opponent type (AI or Heuristic). The backend creates a game and starts a hybrid loop: the AI takes its turns automatically; when it is the human's turn, the loop simply waits. The frontend detects the human's turn via `priority_player` in the legal-actions response and shows interactive controls.

## Architecture Overview

```
Browser (Human)                   Backend
─────────────────────────────────────────────────────
POST /human-game ────────────────→ Creates game + starts HybridGameLoop thread
                 ←──── { game_id } 
Navigate to /ui/human-game/:id

Poll GET /legal-actions (750ms)  ←─ HybridGameLoop: sleeping when human's turn
  if priority_player == "You":
    show interactive controls

Click "Cast Lightning Bolt"
POST /game/:id/cast ─────────────→ Engine validates, updates GameState
                                   HybridGameLoop wakes, sees state advanced,
                                   AI takes next action

AI takes turn
                 ←── GameState    HybridGameLoop: AI decides + submits actions
Poll detects priority_player == "You" again → interactive controls shown
```

## Key Files Created/Modified

### Backend (new)
- `mtg_engine/api/routers/human_game.py` — `POST /human-game` endpoint
- `ai_client/hybrid_game_loop.py` — HybridGameLoop (extends GameLoop, skips when human's turn)

### Backend (modified)
- `mtg_engine/api/main.py` — register `human_game` router

### Frontend (new)
- `frontend/src/pages/HumanGameCreator.tsx` — game creation form
- `frontend/src/pages/HumanGameBoard.tsx` — interactive game board
- `frontend/src/components/ActionPanel.tsx` — pass priority, end turn, confirm attackers buttons
- `frontend/src/components/InteractiveHand.tsx` — hand with clickable cards
- `frontend/src/components/AttackerSelector.tsx` — creature toggle for attack declaration
- `frontend/src/components/BlockerAssigner.tsx` — drag/click to assign blockers
- `frontend/src/components/ChoiceModal.tsx` — modal for mid-resolution choices (targets, modes, scry, discard)
- `frontend/src/components/GameResultOverlay.tsx` — win/loss end screen
- `frontend/src/hooks/useLegalActions.ts` — poll GET /legal-actions, expose isMyTurn + legalActions
- `frontend/src/hooks/useHumanAction.ts` — submit action to backend, manage pending state

### Frontend (modified)
- `frontend/src/App.tsx` (or router file) — add `/ui/human-game/create` and `/ui/human-game/:id` routes
- `frontend/src/pages/GameList.tsx` — add "Play vs AI" button linking to `/ui/human-game/create`

## Running a Human Game (Development)

1. Start backend: `cd src && uvicorn mtg_engine.api.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173/ui/human-game/create`
4. Select opponent type (Heuristic recommended for testing), choose decks, click "Start Game"
5. Play — interactive controls appear when it is your turn

## Testing

```bash
# Backend: test new endpoint and hybrid loop
python -m pytest tests/api/test_human_game.py -v

# Frontend: run dev server and manually verify
# - Land play, spell cast, attacker declaration, blocker assignment, pass priority
# - Observer commentary still works (open /ui/game/:id in parallel)
# - Win/loss overlay triggers correctly
```

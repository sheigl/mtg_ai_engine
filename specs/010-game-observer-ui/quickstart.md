# Quickstart: Game Observer Web UI

**Feature**: 010-game-observer-ui
**Date**: 2026-03-21

## Prerequisites

- Python 3.11+ with the engine dependencies installed
- Node.js 18+ and npm (for building the frontend)

## Setup

### 1. Install frontend dependencies

```bash
cd frontend
npm install
```

### 2. Build the frontend

```bash
cd frontend
npm run build
```

This outputs static files to `frontend/dist/` which FastAPI serves automatically.

### 3. Start the engine

```bash
cd src
uvicorn mtg_engine.api.main:app --reload
```

### 4. Open the observer UI

Navigate to `http://localhost:8000/ui/` in your browser.

## Development Workflow

For active frontend development, run the Vite dev server with hot reloading:

```bash
# Terminal 1: Start the engine API
cd src
uvicorn mtg_engine.api.main:app --reload --port 8000

# Terminal 2: Start Vite dev server with API proxy
cd frontend
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies API requests to the engine on port 8000.

## Integration Scenario: Watching a Live Game

1. **Create a game** via the engine API:
   ```bash
   curl -X POST http://localhost:8000/game \
     -H "Content-Type: application/json" \
     -d '{
       "player1": "Alice",
       "player2": "Bob",
       "deck1": ["Mountain", "Lightning Bolt", ...],
       "deck2": ["Forest", "Llanowar Elves", ...]
     }'
   ```

2. **Open the observer UI** at `http://localhost:8000/ui/`

3. **Select the game** from the game list — the board view loads with both players' zones visible.

4. **Watch the game progress** — as the AI agents play (via the CLI client from feature 008), the board updates in real time showing card animations, life total changes, and combat.

5. **Read the action log** in the sidebar for a play-by-play of game events.

## Integration Scenario: Multiple Games

1. Create two or more games via the API.
2. Open the UI — the game list shows all active games with player names, format, and turn count.
3. Click a game to watch it. Use the back button to return to the list and select a different game.

## Integration Scenario: Commander Game

1. Create a commander-format game:
   ```bash
   curl -X POST http://localhost:8000/game \
     -H "Content-Type: application/json" \
     -d '{
       "player1": "Alice",
       "player2": "Bob",
       "format": "commander",
       "deck1": [...],
       "deck2": [...],
       "commander1": "Atraxa, Praetors Voice",
       "commander2": "Kenrith, the Returned King"
     }'
   ```

2. The board view shows:
   - Starting life at 40
   - Command zones for each player
   - Commander damage totals
   - Commander tax tracking

## Key URLs

| URL | Description |
|-----|-------------|
| `http://localhost:8000/ui/` | Observer UI home (game list) |
| `http://localhost:8000/ui/game/{id}` | Board view for a specific game |
| `http://localhost:8000/game` | API: List active games |
| `http://localhost:8000/game/{id}` | API: Full game state |
| `http://localhost:8000/health` | API: Health check |

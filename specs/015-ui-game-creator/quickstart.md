# Quickstart & Integration Scenarios: UI Game Creator

**Branch**: `015-ui-game-creator` | **Date**: 2026-03-23

## US1: Start a Standard Heuristic Game from the UI

**Scenario**: Simplest possible game — two heuristic players, default decks, no configuration.

1. Open the UI at `http://localhost:5173/ui/`
2. Click **"New AI Game"** button on the game list page
3. In the modal:
   - Player 1: name = "Alpha", type = "Heuristic"
   - Player 2: name = "Beta", type = "Heuristic"
   - Leave all other fields at defaults
4. Click **"Start Game"**
5. Expected: modal closes, browser navigates to `/ui/game/{game_id}`, game board shows autonomous play within seconds

**Verify via API**:
```bash
curl -X POST http://localhost:8000/ai-game \
  -H 'Content-Type: application/json' \
  -d '{
    "player1": {"name": "Alpha", "player_type": "heuristic", "base_url": "", "model": ""},
    "player2": {"name": "Beta", "player_type": "heuristic", "base_url": "", "model": ""}
  }'
# → {"data": {"game_id": "..."}}
```

---

## US1: Start a Standard LLM Game from the UI

**Scenario**: One LLM player vs one heuristic player.

```bash
curl -X POST http://localhost:8000/ai-game \
  -H 'Content-Type: application/json' \
  -d '{
    "player1": {
      "name": "LLM",
      "player_type": "llm",
      "base_url": "http://localhost:11434/v1",
      "model": "devstral"
    },
    "player2": {"name": "Heuristic", "player_type": "heuristic", "base_url": "", "model": ""}
  }'
```

---

## US2: Custom Deck Lists

**Scenario**: User provides specific cards for both players.

```bash
curl -X POST http://localhost:8000/ai-game \
  -H 'Content-Type: application/json' \
  -d '{
    "player1": {"name": "P1", "player_type": "heuristic", "base_url": "", "model": ""},
    "player2": {"name": "P2", "player_type": "heuristic", "base_url": "", "model": ""},
    "deck1": ["Lightning Bolt", "Lightning Bolt", "Lightning Bolt", "Mountain", "Mountain"],
    "deck2": ["Grizzly Bears", "Grizzly Bears", "Forest", "Forest"]
  }'
# → If deck too small, engine returns 422 with DECK_LOAD_ERROR
```

---

## US3: Commander Format

**Scenario**: Two commanders, default 99-card decks filled from built-in list.

```bash
curl -X POST http://localhost:8000/ai-game \
  -H 'Content-Type: application/json' \
  -d '{
    "player1": {"name": "P1", "player_type": "heuristic", "base_url": "", "model": ""},
    "player2": {"name": "P2", "player_type": "heuristic", "base_url": "", "model": ""},
    "format": "commander",
    "commander1": "Ghalta, Primal Hunger",
    "commander2": "Multani, Maro-Sorcerer"
  }'
```

---

## US4: Debug + Observer

**Scenario**: Debug enabled with observer AI.

```bash
curl -X POST http://localhost:8000/ai-game \
  -H 'Content-Type: application/json' \
  -d '{
    "player1": {
      "name": "Alice",
      "player_type": "llm",
      "base_url": "http://localhost:11434/v1",
      "model": "devstral"
    },
    "player2": {"name": "Bob", "player_type": "heuristic", "base_url": "", "model": ""},
    "debug": true,
    "observer_url": "http://localhost:11434/v1",
    "observer_model": "devstral"
  }'
# Debug panel auto-opens on the game board; observer commentary appears
```

---

## US5: Advanced Options

**Scenario**: Max turns cap + verbose logging.

```bash
curl -X POST http://localhost:8000/ai-game \
  -H 'Content-Type: application/json' \
  -d '{
    "player1": {"name": "P1", "player_type": "heuristic", "base_url": "", "model": ""},
    "player2": {"name": "P2", "player_type": "heuristic", "base_url": "", "model": ""},
    "max_turns": 10,
    "verbose": true
  }'
# Game ends after 10 turns maximum; play-by-play events appear in action log
```

---

## Error Scenarios

### Missing commander names
```bash
curl -X POST http://localhost:8000/ai-game \
  -d '{"player1": {...}, "player2": {...}, "format": "commander"}'
# → 422: {"error": "Commander format requires commander1 and commander2", "error_code": "INVALID_REQUEST"}
```

### Duplicate player names
```bash
curl -X POST http://localhost:8000/ai-game \
  -d '{"player1": {"name": "Alice", ...}, "player2": {"name": "Alice", ...}}'
# → 422: {"error": "player1 and player2 must have different names", "error_code": "DUPLICATE_PLAYER_NAME"}
```

### LLM player missing URL
```bash
curl -X POST http://localhost:8000/ai-game \
  -d '{"player1": {"name": "P1", "player_type": "llm", "base_url": "", "model": "devstral"}, ...}'
# → 422: {"error": "player1 has player_type=llm but base_url is missing or invalid", "error_code": "INVALID_PLAYER_CONFIG"}
```

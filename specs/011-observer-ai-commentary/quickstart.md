# Quickstart: Observer AI Debug Panel

**Feature**: 011-observer-ai-commentary

---

## Running with the debug panel

### 1. Start the engine (unchanged)

```bash
uvicorn mtg_engine.api.main:app --reload --host 0.0.0.0 --port 8999
```

### 2. Start a game with debug mode enabled

Pass `--debug` to the AI client. This enables prompt/response capture and observer AI commentary.

```bash
python -m ai_client \
  --player "Llama,http://localhost:8080/v1,devstral-2:24b" \
  --player "Llama2,http://localhost:8080/v1,devstral-2:24b" \
  --engine http://localhost:8999 \
  --debug
```

The observer AI uses the same Ollama endpoint by default. To use a different model for the observer:

```bash
python -m ai_client \
  --player "Llama,http://localhost:8080/v1,devstral-2:24b" \
  --player "Llama2,http://localhost:8080/v1,devstral-2:24b" \
  --engine http://localhost:8999 \
  --debug \
  --observer "http://localhost:8080/v1,devstral-2:24b"
```

### 3. Open the observer UI

Navigate to `http://localhost:8999/ui/`. Select the running game from the game list.

### 4. Enable the debug panel

Click the **"Debug Panel"** toggle button in the top-right of the game board. The panel slides in on the right side, showing:
- **Blue blocks** — Llama (Player 1) prompt + streaming response
- **Green blocks** — Llama2 (Player 2) prompt + streaming response
- **Amber blocks** — Observer AI commentary (rating badge: 🟢 Good / 🟡 Acceptable / 🔴 Suboptimal)

Click any block header to collapse/expand it.

---

## Viewing a completed game's debug log

The debug panel persists for the lifetime of the engine process. Select any completed game from the game list; enable the debug panel to see the full prompt/response and commentary history.

---

## Disabling debug (default)

Without `--debug`, the AI client sends no debug entries and the engine's debug log remains empty. The debug panel toggle in the UI still appears but shows "No debug data for this game."

---

## Running tests

```bash
# Backend debug log tests
python -m pytest tests/debug/ -v

# Frontend (from frontend/)
npm run test
```

# Quickstart: AI CLI Client for MTG Games

**Branch**: `008-ai-cli-client` | **Date**: 2026-03-21

## Prerequisites

1. **MTG engine API running**:
   ```bash
   cd /path/to/mtg_ai_engine
   uvicorn mtg_engine.api.main:app --reload
   ```

2. **At least one OpenAI-compatible LLM server running** (e.g. Ollama):
   ```bash
   ollama serve
   ollama pull llama3.2
   ```

3. **Python dependencies installed** (once `ai_client/` is implemented):
   ```bash
   pip install httpx openai
   ```

---

## Minimal Run (two AI players, default decks)

```bash
python -m ai_client \
  --player "Llama,http://localhost:11434/v1,llama3.2" \
  --player "Llama2,http://localhost:11434/v1,llama3.2"
```

Both players use the same local Ollama endpoint and the built-in 40-card test deck. The game plays out automatically with each turn logged to the console.

---

## Two Different AI Models

```bash
python -m ai_client \
  --player "Llama,http://localhost:11434/v1,llama3.2" \
  --player "Mistral,http://localhost:11434/v1,mistral"
```

---

## Custom Decks + Verbose Output

```bash
python -m ai_client \
  --player "Alpha,http://localhost:11434/v1,llama3.2" \
  --player "Beta,http://localhost:11435/v1,phi3" \
  --deck1 "Mountain,Mountain,Mountain,Mountain,Lightning Bolt,Lightning Bolt,Goblin Guide,Goblin Guide" \
  --deck2 "Forest,Forest,Forest,Forest,Llanowar Elves,Llanowar Elves,Grizzly Bears,Grizzly Bears" \
  --verbose
```

---

## Remote Engine

```bash
python -m ai_client \
  --player "Llama,http://localhost:11434/v1,llama3.2" \
  --player "Llama2,http://localhost:11434/v1,llama3.2" \
  --engine http://192.168.1.50:8000
```

---

## Sample Console Output

```
Starting MTG AI Game
Engine  : http://localhost:8000
Players : Llama (llama3.2 @ http://localhost:11434/v1)
          Mistral (mistral @ http://localhost:11435/v1)
Game ID : a3f7b219

─────────────────────────────────────────
Turn 1 | BEGINNING / DRAW
Player: Llama
Reasoning: I draw my card for the turn as required.
Action: Pass priority (automatic draw step)
─────────────────────────────────────────

─────────────────────────────────────────
Turn 1 | PRECOMBAT_MAIN / MAIN
Player: Llama
Reasoning: I have a Plains and two creatures in hand. I'll play the Plains
           to hit my land drop and hold the creatures for next turn.
Action: Play land: Plains
─────────────────────────────────────────

...

════════════════════════════════════════
GAME OVER
Winner : Llama
Game ID: a3f7b219
Turns  : 8
Decisions made: 31
Reason : game_over
════════════════════════════════════════
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` on start | Engine not running | Start `uvicorn mtg_engine.api.main:app` |
| AI turns show `[WARNING] Falling back to pass` | LLM endpoint not running | Start Ollama or your LLM server |
| `InvalidPlayerConfig` error | Malformed `--player` value | Ensure format is `name,url,model` with no spaces around commas |
| Game never ends | AI keeps passing | Increase `--max-turns` or check that AI is choosing non-pass actions |

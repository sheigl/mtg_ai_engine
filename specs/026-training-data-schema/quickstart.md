# Quickstart: Training Data Schema (026)

## Prerequisites

- MongoDB running and `MONGODB_URL` set (same as feature 025)
- Python 3.11 + `motor>=3.3.0` installed (already in `requirements.txt`)

## Running the engine with new schema

```bash
# Start engine (collection creation and indexes happen on startup)
cd /home/sheigl/code/mtg_ai_engine
uvicorn mtg_engine.api.main:app --reload
```

On startup, `ensure_indexes()` creates all required indexes on `decisions`, `rules_qa`, and `transcript` collections.

## Running a game and querying training data

```bash
# 1. Create a game (existing API — unchanged)
curl -X POST http://localhost:8000/game \
  -H "Content-Type: application/json" \
  -d '{"player_1": "Alice", "player_2": "Bob", "player_1_type": "llm", "player_2_type": "heuristic"}'

# 2. Run the AI client (unchanged invocation)
python ai_client/main.py --game-id <game_id>

# 3. Query all decisions for a completed game
curl http://localhost:8000/games/records/<game_id>/decisions

# 4. Filter decisions by outcome (directly in MongoDB)
# db.decisions.find({ game_id: "<game_id>", "outcome_context.active_player_won": true })

# 5. Query suboptimal observer evaluations
# db.decisions.find({ "observer_evaluation.rating": "suboptimal" })
```

## Running tests

```bash
python -m pytest tests/ -v
```

Integration tests against MongoDB use the configured `MONGODB_URL`. Unit tests mock the collections.

## Key environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | *(unset = disabled)* | MongoDB connection string |
| `MONGODB_DATABASE` | parsed from URL path, or `mtg_training` | Database name |
| `MONGODB_COLLECTION` | `games` | Games collection name (others derived: `decisions`, `rules_qa`, `transcript`) |

## Collection layout (new schema)

```
mtg_training/
├── games          — metadata only, one doc per game
├── decisions      — one doc per priority grant (training unit)
├── rules_qa       — one doc per Q&A pair
└── transcript     — one doc per game event
```

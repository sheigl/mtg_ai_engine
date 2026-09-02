# Quickstart: Feature 025 Development

## What's Being Built

Automatic live persistence of all game data to MongoDB as games are played, with a query API for training pipelines. Three independent deliverables:

1. **P1 — Live persistence**: All events auto-written to MongoDB as they occur
2. **P2 — Query API**: Training pipelines can query completed games
3. **P3 — File export compatibility**: Existing game log download unchanged

## Prerequisites

Start a local MongoDB instance:
```bash
docker run -d -p 27017:27017 --name mtg-mongo mongo:7
```

Set the environment variable before starting the engine:
```bash
export MONGODB_URL=mongodb://server.home:27017/mtg_training
```

## Key Files to Create

```text
mtg_engine/persistence/
├── __init__.py
├── mongo_client.py        # AsyncIOMotorClient singleton; is_configured(); get_games_collection()
└── game_persister.py      # MongoGamePersister — listens to recorders, writes to MongoDB
```

## Key Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `motor>=3.3.0` |
| `mtg_engine/export/snapshots.py` | Add listener registration + `_notify_finalized()` in `finalize_snapshot()` |
| `mtg_engine/export/store.py` | In `get_export_store()`, create and register `MongoGamePersister` if configured |
| `mtg_engine/api/game_manager.py` | Add `player_1_type`/`player_2_type` params to `create_game()` |
| `mtg_engine/api/routers/human_game.py` | Pass `player_1_type="human"` when creating human-vs-AI game |
| `mtg_engine/api/routers/debug.py` | Call `update_debug_entry()` on persister after annotate/rerate |
| `mtg_engine/api/routers/export.py` | Read from MongoDB when available for game-log generation |
| `mtg_engine/api/main.py` | Register `GET /games/records` router; extend `/health` |

## Key Files to Create (API)

```text
mtg_engine/api/routers/
└── game_records.py        # GET /games/records, GET /games/records/{game_id}
```

## Implementation Order

1. **MongoDB client** — `mongo_client.py` (no dependencies on other new code)
2. **SnapshotRecorder listener** — add listener to `snapshots.py` (5 lines)
3. **MongoGamePersister** — `game_persister.py` (core of the feature)
4. **Wire into export store** — `store.py` registers persister when configured
5. **Player type tracking** — `game_manager.py` + `human_game.py`
6. **Annotate/rerate persistence** — `debug.py` router calls persister
7. **Query API** — `game_records.py` router
8. **Health endpoint** — `main.py` extension
9. **File export compatibility** — `export.py` reads from MongoDB when available

## Testing

```bash
# Start engine with MongoDB configured
export MONGODB_URL=mongodb://server.home:27017/mtg_training
cd src && uvicorn mtg_engine.api.main:app --reload

# Verify MongoDB connectivity
curl http://localhost:8000/health

# Start a game, play a few turns, then query
curl "http://localhost:8000/games/records?is_complete=false&limit=5"

# Query completed human-vs-AI games
curl "http://localhost:8000/games/records?has_human_player=true&is_complete=true"

# Full record for a specific game
curl "http://localhost:8000/games/records/<game_id>"

# Verify file export still works
curl "http://localhost:8000/export/<game_id>/game-log"

# Verify no MongoDB startup failure when env var not set
unset MONGODB_URL
cd src && uvicorn mtg_engine.api.main:app --reload  # must start cleanly
```

## Verification Checklist

- [ ] `GET /health` shows `"mongodb": "connected"` when URL is set
- [ ] After any game action, MongoDB document has new transcript entry
- [ ] After game ends, `is_complete: true` and `outcome` are set in MongoDB
- [ ] `GET /games/records` returns results with correct filter behavior
- [ ] `GET /export/{game_id}/game-log` still returns correct plain text
- [ ] Starting engine without `MONGODB_URL` produces no errors

## Training Pipeline Usage

Direct MongoDB query (Python):
```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://server.home:27017/mtg_training")
db = client.mtg_training

# Fetch all completed human-vs-AI games from today
async def get_training_batch():
    cursor = db.games.find(
        {"has_human_player": True, "is_complete": True},
        {"snapshots": 0}   # exclude heavy snapshots for quick pass
    ).sort("created_at", -1).limit(100)
    return await cursor.to_list(length=100)
```

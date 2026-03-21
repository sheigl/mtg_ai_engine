# Quickstart: MTG Rules Engine

**Generated**: 2026-03-20  
**Source**: `/specs/006-plan-spec-from-existing/spec.md`

---

## Prerequisites

- Python 3.11+
- MongoDB instance (local or remote)
- Scryfall API access (or local card cache)

---

## Installation

```bash
# Clone repository
git clone https://github.com/your-org/mtg_ai_engine.git
cd mtg_ai_engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn pydantic httpx pymongo pytest pytest-asyncio

# Download comprehensive rules (required for rules engine)
curl -L "https://media.wizards.com/2025/downloads/MagicCompRules_20250404.txt" \
     -o cr.txt
```

---

## Configuration

Create `.env` file:

```bash
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=mtg_training_data
SCRYALFAY_API_KEY=your_api_key  # Optional, for rate limit increase
RANDOM_SEED=42  # For deterministic games
```

---

## Running the Server

```bash
# Development mode with auto-reload
uvicorn mtg_engine.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn mtg_engine.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Server available at: `http://localhost:8000`

---

## Quick Test: Play a Game

### 1. Create a game

```bash
curl -X POST "http://localhost:8000/api/v1/games" \
  -H "Content-Type: application/json" \
  -d '{
    "player_0_name": "Agent Alpha",
    "player_1_name": "Agent Beta",
    "starting_life": 20,
    "random_seed": 12345
  }'
```

Response:
```json
{
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "turn": 1,
    "step": "untap"
  }
}
```

### 2. Get game state

```bash
curl "http://localhost:8000/api/v1/games/550e8400-e29b-41d4-a716-446655440000"
```

### 3. Cast a spell (dry run first)

```bash
# Dry run to validate action without state change
curl -X POST "http://localhost:8000/api/v1/games/550e8400-e29b-41d4-a716-446655440000/actions" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "cast_spell",
    "card_id": "43d2d6a4-a3d4-4f0d-9b7e-1e8f5c6d7e8f",
    "dry_run": true
  }'
```

### 4. Execute the action

```bash
curl -X POST "http://localhost:8000/api/v1/games/550e8400-e29b-41d4-a716-446655440000/actions" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "cast_spell",
    "card_id": "43d2d6a4-a3d4-4f0d-9b7e-1e8f5c6d7e8f",
    "dry_run": false
  }'
```

### 5. Pass priority

```bash
curl -X POST "http://localhost:8000/api/v1/games/550e8400-e29b-41d4-a716-446655440000/actions" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "pass_priority"
  }'
```

### 6. Export training data (after game completes)

```bash
curl "http://localhost:8000/api/v1/games/550e8400-e29b-41d4-a716-446655440000/export?data_type=all"
```

---

## Testing

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run specific test file
PYTHONPATH=. pytest tests/rules/test_sba.py -v

# Run API integration tests
PYTHONPATH=. pytest tests/api/ -v

# Run with coverage
PYTHONPATH=. pytest tests/ --cov=mtg_engine --cov-report=html
```

---

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Common Actions

### Play a Land

```json
{
  "action_type": "play_land",
  "land_id": "card-uuid-from-hand"
}
```

### Activate an Ability

```json
{
  "action_type": "activate_ability",
  "card_id": "card-uuid-on-battlefield",
  "value": 3  # For abilities with X
}
```

### Declare Attackers

```json
{
  "action_type": "declare_attackers",
  "attackers": ["card-uuid-1", "card-uuid-2"]
}
```

### Declare Blockers

```json
{
  "action_type": "declare_blockers",
  "blockers": {
    "card-uuid-1": ["blocker-card-uuid"]
  }
}
```

### Surrender

```json
{
  "action_type": "surrender"
}
```

---

## Training Data Export

The engine exports 4 types of training data to MongoDB:

### 1. Game Snapshots

Board state at each priority grant.

```json
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn": 1,
  "step": "draw",
  "priority_player": 0,
  "game_state": {...},
  "legal_actions": [...],
  "chosen_action": {...}
}
```

### 2. Decision Transcripts

Full play-by-play with rules citations.

```json
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_sequence": [
    {
      "event_type": "spell_cast",
      "player": 0,
      "description": "Cast Lightning Bolt for 3 damage",
      "rules_citations": ["CR 601.2", "CR 118.7"],
      "stack_before": [...],
      "stack_after": [...]
    }
  ]
}
```

### 3. Rules Q&A Pairs

Automatic extraction of rules questions from gameplay.

```json
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "Can I respond to a split-second spell?",
  "answer": "No, CR 702.60b",
  "context": {...},
  "trigger_event": "split_second_spell_cast"
}
```

### 4. Outcome Records

Win/loss data for reinforcement learning.

```json
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "winner": 0,
  "loss_reason": "life_total_zero",
  "turn_count": 47,
  "duration_seconds": 1234.5,
  "training_tags": ["trample", "deathtouch", "stack_interaction"]
}
```

---

## Next Steps

1. **Read the spec**: `/specs/006-plan-spec-from-existing/spec.md`
2. **Review data model**: `/specs/006-plan-spec-from-existing/data-model.md`
3. **Study the API contract**: `/specs/006-plan-spec-from-existing/contracts/api-contract.md`
4. **Check research decisions**: `/specs/006-plan-spec-from-existing/research.md`
5. **Run tests**: `PYTHONPATH=. pytest tests/ -v`

---

## Troubleshooting

### MongoDB connection error

```bash
# Check MongoDB is running
mongod --version

# Start MongoDB (if not running)
mongod --dbpath /data/db --port 27017
```

### Scryfall API rate limit

```bash
# Use local card cache instead
# Cards will be cached in sqlite3 after first fetch
```

### Test failures

```bash
# Ensure PYTHONPATH is set correctly
PYTHONPATH=. pytest tests/ -v

# Check cr.txt exists
ls -la cr.txt
```

---

## Support

- Issues: GitHub Issues
- Documentation: `/specs/` directory
- Rules reference: `cr.txt` (Comprehensive Rules)

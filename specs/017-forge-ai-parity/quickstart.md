# Quickstart: Forge AI Parity

**Branch**: `017-forge-ai-parity` | **Date**: 2026-03-25

---

## Running an AI vs AI Game with the New Features

### 1. Run the engine

```bash
cd /home/sheigl/code/mtg_ai_engine
uvicorn mtg_engine.api.main:app --reload
```

### 2. Run a heuristic vs heuristic game with a personality profile

```bash
python -m ai_client \
  --player Alice:heuristic:personality=aggro \
  --player Bob:heuristic:personality=default \
  --deck1 decks/mono_red.txt \
  --deck2 decks/green_ramp.txt
```

### 3. Use the default profile (no change from current behavior)

```bash
python -m ai_client \
  --player Alice:heuristic \
  --player Bob:heuristic \
  --deck1 decks/mono_red.txt \
  --deck2 decks/green_ramp.txt
```

---

## Running Tests

```bash
# All tests (must all pass — no regressions)
python -m pytest tests/ -v

# New AI behavior tests only
python -m pytest tests/test_heuristic_ai.py tests/test_ai_memory.py tests/test_block_classification.py -v

# Lookahead performance test (must complete in <500ms per action)
python -m pytest tests/test_lookahead.py -v --tb=short

# Mulligan decision tests
python -m pytest tests/test_mulligan.py -v
```

---

## Key Extension Points for Implementors

### Adding a new spell scoring branch

All new scoring is added to `HeuristicPlayer._score_noncreature_spell()` in `ai_client/heuristic_player.py`. Pattern:

```python
# Detect effect pattern
if _FIGHT_RE.match(oracle_text):
    return self._score_fight(card, game_state, my_name)
```

Add the regex to the top of `heuristic_player.py` alongside existing patterns.

### Adding a new personality flag

1. Add field to `AiPersonalityProfile` dataclass in `ai_client/models.py`
2. Set a default value
3. Update `AiPersonalityProfile.DEFAULT` and `AiPersonalityProfile.AGGRO` class constants
4. Use the flag in the appropriate scoring method: `self._profile.my_new_flag`

### Adding a new AIMemory category

1. Add a `set[str]` or `dict` field to `AIMemory` in `ai_client/models.py`
2. Populate it in the scoring or game loop code that observes the relevant event
3. Clear it in `AIMemory.new_turn()` if it is a per-turn category

### Adding a new engine legal action type

1. Add detection logic to `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`
2. Add the handler endpoint in the same router file
3. Map the new action type in `_map_action_to_request()` in `ai_client/game_loop.py`
4. Add scoring in `HeuristicPlayer._score_action()` dispatcher

---

## Architecture Diagram

```
game_loop.py
    │
    ├── creates AIMemory (per player, per game)
    ├── calls HeuristicPlayer.evaluate_mulligan() before turn 1
    │
    └── per-priority-window:
            │
            ├── GET /game/{id}/legal-actions  → LegalActionsResponse
            │
            ├── HeuristicPlayer.choose_action(legal_actions, game_state, memory)
            │       │
            │       ├── _score_action() per action
            │       │       ├── uses AiPersonalityProfile for probabilities
            │       │       ├── LookaheadSimulator.evaluate_bonus() [depth-1]
            │       │       └── updates AIMemory (fog, trick_attackers, etc.)
            │       │
            │       └── returns (best_index, reasoning)
            │
            └── POST /game/{id}/{action_type}  → submit chosen action
```

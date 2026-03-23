# Quickstart: Heuristic AI Player

**Branch**: `012-heuristic-ai-player` | **Date**: 2026-03-22

## Running a Heuristic vs Heuristic Game

No LLM endpoints required. Both players make instant, rule-based decisions.

```bash
python -m ai_client \
  --player "Bot1,," \
  --player "Bot2,," \
  --player1-type heuristic \
  --player2-type heuristic \
  --max-turns 0
```

## Running Heuristic vs LLM

Player 1 uses an LLM; player 2 uses heuristics.

```bash
python -m ai_client \
  --player "Alice,http://localhost:11434/v1,devstral" \
  --player "Bot,," \
  --player1-type llm \
  --player2-type heuristic \
  --max-turns 0
```

## With Debug Panel

The debug panel shows LLM player prompts and responses. Heuristic player decisions appear in the Action Log only.

```bash
python -m ai_client \
  --player "Alice,http://localhost:11434/v1,devstral" \
  --player "Bot,," \
  --player1-type llm \
  --player2-type heuristic \
  --debug \
  --max-turns 0
```

## Running Tests

```bash
python -m pytest tests/test_heuristic_player.py -v
```

## What the Heuristic Player Does

The heuristic player evaluates available actions in priority order each time it has priority:

1. **Play a land** — if a land is in hand and not yet played this turn (main phase only)
2. **Cast the highest-cost affordable spell** — develops the board aggressively
3. **Put a triggered ability on the stack** — resolves pending triggers
4. **Declare attackers** — attacks with all eligible creatures every turn
5. **Declare blockers** — blocks to prevent lethal damage
6. **Activate a non-mana ability** — if available and no higher-priority action applies
7. **Pass priority** — default when nothing else applies

Mana activations (tapping lands) are handled automatically by the game loop before the heuristic player is consulted — the heuristic player always sees a full mana pool.

# CLI Contract: Heuristic AI Player

**Branch**: `012-heuristic-ai-player` | **Date**: 2026-03-22

## New Flags

### `--player1-type {llm,heuristic}`

Selects the decision engine for player 1.

| Value | Behaviour |
|-------|-----------|
| `llm` | Default. Uses AIPlayer with `--player1-url` and `--player1-model`. |
| `heuristic` | Uses HeuristicPlayer. `--player1-url` and `--player1-model` become optional. |

### `--player2-type {llm,heuristic}`

Same as above for player 2.

---

## Backwards Compatibility

All existing invocations remain valid. When `--player1-type` and `--player2-type` are omitted, both default to `llm` — identical to current behaviour.

```bash
# Existing invocation — unchanged behaviour
python -m ai_client \
  --player "Alice,http://localhost:11434/v1,devstral" \
  --player "Bob,http://localhost:11434/v1,qwen2.5-coder:32b"
```

---

## New Invocation Examples

```bash
# Heuristic vs LLM
python -m ai_client \
  --player "Alice,http://localhost:11434/v1,devstral" \
  --player "Bot,," \
  --player1-type llm \
  --player2-type heuristic

# Heuristic vs Heuristic (no LLM endpoints needed)
python -m ai_client \
  --player "Bot1,," \
  --player "Bot2,," \
  --player1-type heuristic \
  --player2-type heuristic

# LLM vs Heuristic with debug panel
python -m ai_client \
  --player "Alice,http://localhost:11434/v1,devstral" \
  --player "Bot,," \
  --player1-type llm \
  --player2-type heuristic \
  --debug
```

---

## Validation Rules

- If `--player1-type llm` (or defaulted), `--player` entry 1 must have non-empty url and model.
- If `--player1-type heuristic`, url and model fields in `--player` entry 1 are ignored.
- Invalid type values (not `llm` or `heuristic`) produce an argparse error and exit code 2.

---

## Player Interface Contract

Both `AIPlayer` and `HeuristicPlayer` satisfy this interface. `GameLoop` uses it to call decisions.

```python
class PlayerInterface(Protocol):
    _debug_callback: Callable[[str, str, str], None] | None

    def decide(
        self,
        prompt: str,
        legal_actions: list[dict] | None = None,
        game_state: dict | None = None,
    ) -> tuple[int, str]:
        """
        Returns (action_index, reasoning).
        - action_index: int in [0, len(legal_actions))
        - reasoning: non-empty string for console output
        - Never raises; returns (0, fallback_message) on error
        """
```

# Data Model: Heuristic AI Player

**Branch**: `012-heuristic-ai-player` | **Date**: 2026-03-22

## Modified Entity: PlayerConfig

```python
@dataclass
class PlayerConfig:
    name: str
    base_url: str = ""        # optional for heuristic players
    model: str = ""           # optional for heuristic players
    player_type: str = "llm"  # "llm" | "heuristic"
```

**Validation rules**:
- `player_type` must be `"llm"` or `"heuristic"`
- When `player_type == "llm"`, `base_url` and `model` must be non-empty
- When `player_type == "heuristic"`, `base_url` and `model` are ignored

---

## New Entity: HeuristicPlayer

```python
class HeuristicPlayer:
    """
    Competitive score-based player. Evaluates every legal action using a
    weighted function over board state, combat math, and card values.
    Duck-type peer of AIPlayer — same interface, no external calls.
    """
    _debug_callback: Callable[[str, str, str], None] | None
    _config: PlayerConfig

    def decide(
        self,
        prompt: str,
        legal_actions: list[dict] | None = None,
        game_state: dict | None = None,
    ) -> tuple[int, str]:
        """
        Return (action_index, reasoning).
        Scores all actions; returns the highest-scoring index.
        Never raises. Returns (0, reason) as fallback.
        """

    def _score_action(
        self,
        action: dict,
        game_state: dict,
        my_name: str,
    ) -> float:
        """Assign a numeric score to a single legal action."""

    def _simulate_combat(
        self,
        attackers: list[dict],
        blockers: list[dict],
        opp_life: int,
    ) -> float:
        """Return net score of declaring given attackers against available blockers."""

    def _score_block_assignment(
        self,
        incoming_attackers: list[dict],
        my_creatures: list[dict],
        my_life: int,
    ) -> float:
        """Return net score of the optimal blocking assignment."""
```

## New Entity: ActionScore

A transient value used only within a single `decide()` call — not persisted.

| Field | Type | Purpose |
|-------|------|---------|
| `index` | int | Position in `legal_actions` list |
| `score` | float | Computed evaluation score (higher = better) |
| `reason` | str | Human-readable explanation for console/log output |

**Fields in `legal_actions` items used by heuristic**:

| Field | Type | Used for |
|-------|------|----------|
| `action_type` | str | Rule matching (play_land, cast, declare_attackers, etc.) |
| `description` | str | Reasoning string in TurnRecord |
| `mana_options` | list[dict] | Determine converted mana cost for spell selection |

**Fields in `game_state` used by heuristic**:

| Field | Used for |
|-------|----------|
| `players[].mana_pool` | Determine affordable spells |
| `players[].hand` | Cross-reference card costs |
| `battlefield[].controller` | Identify own vs opponent permanents |
| `battlefield[].tapped` | Blocker availability |

---

## Modified Entity: AIPlayer.decide()

Signature extended (backward-compatible):

```python
def decide(
    self,
    prompt: str,
    legal_actions: list[dict] | None = None,  # new, ignored by AIPlayer
    game_state: dict | None = None,            # new, ignored by AIPlayer
) -> tuple[int, str]:
```

---

## Player Factory

```python
def _make_player(config: PlayerConfig) -> "AIPlayer | HeuristicPlayer":
    if config.player_type == "heuristic":
        return HeuristicPlayer(config)
    return AIPlayer(config)
```

Lives in `ai_client/__main__.py`.

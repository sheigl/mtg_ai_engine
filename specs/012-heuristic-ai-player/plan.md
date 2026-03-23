# Implementation Plan: Heuristic AI Player

**Branch**: `012-heuristic-ai-player` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-heuristic-ai-player/spec.md`

## Summary

Add a `HeuristicPlayer` that selects game actions using a competitive, score-based evaluation function (no LLM calls), and allow users to assign either `heuristic` or `llm` to each player seat via CLI flags. The heuristic player is designed to be a genuinely strong opponent: it scores every legal action using board state, life totals, power/toughness math, and combat simulation, always selecting the highest-impact play. It is a duck-type drop-in for `AIPlayer` — same `decide()` interface, same `_debug_callback` attribute, no external calls. All three player-type combinations (heuristic vs heuristic, heuristic vs LLM, LLM vs LLM) are supported with zero changes to existing LLM behaviour.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: None new — stdlib only for heuristic logic; existing `openai`, `httpx`, `argparse` unchanged
**Storage**: N/A — stateless, same as existing AI client
**Testing**: pytest (existing)
**Target Platform**: Linux server (same as existing AI client)
**Project Type**: CLI tool
**Performance Goals**: Heuristic decisions under 50ms per priority window (no network I/O)
**Constraints**: Fully backwards-compatible — existing `--player` flags with no `--player-type` flag behave identically
**Scale/Scope**: Two-player game, unlimited turns

## Constitution Check

No constitution file exists for this project. Proceeding without gate checks. Design follows existing project conventions:
- Single Python file per concern (`heuristic_player.py` mirrors `ai_player.py`)
- Models extended minimally — one new optional field on `PlayerConfig`
- No new dependencies

## Project Structure

### Documentation (this feature)

```text
specs/012-heuristic-ai-player/
├── plan.md              # This file
├── research.md          # Phase 0: interface analysis and design decisions
├── data-model.md        # Phase 1: PlayerConfig extension, HeuristicPlayer model
├── quickstart.md        # Phase 1: how to run with heuristic players
├── contracts/           # Phase 1: CLI contract, decide() interface
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
ai_client/
├── __main__.py          # Modified: --player1-type / --player2-type flags
├── models.py            # Modified: PlayerConfig gets optional player_type field
├── ai_player.py         # Modified: decide() accepts optional legal_actions/game_state
├── heuristic_player.py  # New: HeuristicPlayer class
└── game_loop.py         # Modified: passes legal_actions to decide(); accepts BasePlayer union type

tests/
└── test_heuristic_player.py   # New: unit tests for heuristic decision logic
```

**Structure Decision**: Single-project, extends existing `ai_client/` package. One new file (`heuristic_player.py`), minimal changes to existing files.

## Phase 0: Research

See [research.md](research.md) for full findings. Key decisions:

- **Interface**: `HeuristicPlayer` is a duck-type peer of `AIPlayer` — same `decide()` signature extended with optional `legal_actions` and `game_state` kwargs. No formal base class needed (Python duck typing).
- **Game state access**: `decide()` receives parsed `legal_actions: list[dict]` and `game_state: dict` alongside the prompt string; heuristic player uses these directly, AIPlayer ignores them.
- **Heuristic priority order**: play land → cast best spell → declare attackers → assign blockers → put trigger → pass priority.
- **CLI design**: Two new flags `--player1-type` and `--player2-type` accepting `llm` (default) or `heuristic`. Heuristic players do not require `--player1-url` / `--player1-model`.

## Phase 1: Design

### HeuristicPlayer Interface

```python
class HeuristicPlayer:
    _debug_callback: Callable | None  # mutable; set by GameLoop when --debug

    def __init__(self, config: PlayerConfig) -> None: ...

    def decide(
        self,
        prompt: str,
        legal_actions: list[dict] | None = None,
        game_state: dict | None = None,
    ) -> tuple[int, str]:
        """Return (action_index, reasoning). Never raises."""
```

### Scoring-Based Decision Engine

Rather than a fixed priority order, every legal action is assigned a numeric score. The highest-scoring action is selected (ties broken by index). This allows nuanced trade-offs — e.g., holding back a creature is scored higher than attacking into a losing trade, even though "attack" normally scores well.

#### Score Contributions by Action Type

| Action Type | Base Score | Modifiers |
|-------------|------------|-----------|
| `play_land` | 50 | Always high — land development is critical |
| `cast` | 10 × CMC of spell | +20 if creature with power ≥ 3; +15 if has trample/deathtouch/lifelink; -10 if opponent has a blocker that kills it without trading up |
| `declare_attackers` | Computed by combat simulator | See combat scoring below |
| `declare_blockers` | Computed by block evaluator | See blocking scoring below |
| `put_trigger` | 30 | Always resolve pending triggers |
| `activate` (non-mana) | 20 | Non-mana activated abilities |
| `pass` | 0 | Baseline — always available |

Mana-producing activate actions are already handled by `_auto_tap_mana` in `GameLoop` before `decide()` is called and will not appear in `legal_actions`.

#### Combat Scoring (declare_attackers)

The heuristic simulates the outcome of attacking with all available creatures:

1. **Lethal check**: If total attacker power ≥ opponent life total → score = 10,000 (always attack for lethal)
2. **Favourable trade**: For each attacker, find opponent's likely blocker assignment (highest toughness ≤ attacker power). If attacker kills the blocker and survives → score += (blocker CMC × 10)
3. **Chip damage**: If opponent has no blockers, any attack scores = total unblocked power × 15
4. **Unfavourable trade penalty**: If attacker dies and kills nothing worth more → score -= (attacker CMC × 8)
5. **Net score**: Sum of all attacker contributions. Attack if net score > 0.

#### Blocking Scoring (declare_blockers)

1. **Prevent lethal**: If total incoming unblocked damage ≥ own life total → must block; assign best available blocker to each lethal attacker (score = 1,000 per lethal attack blocked)
2. **Favourable trade**: Blocker can kill attacker and survives (or trades with a higher-CMC attacker) → score += (attacker CMC - blocker CMC) × 10
3. **Avoid bad trades**: Blocker dies without killing attacker and life total is not at risk → don't block (score penalty)

#### Spell Selection Scoring

When multiple `cast` actions are available in the same priority window, the one with the highest score is selected. Factors:

- **CMC**: Higher CMC generally = more powerful card → base score = CMC × 10
- **Power bonus**: Creatures with power ≥ 3 score higher (+20)
- **Keyword bonus**: Trample, deathtouch, lifelink, flying each add +15
- **Tempo**: If opponent's life total ≤ 6, aggressive creatures score ×1.5

### GameLoop Changes

```python
# game_loop.py — extend decide() call to pass structured data
chosen_index, reasoning = ai_player.decide(
    prompt,
    legal_actions=legal_actions,
    game_state={**gs, "priority_player": priority_player, "phase": phase, "step": step},
)
```

### PlayerConfig Extension

```python
@dataclass
class PlayerConfig:
    name: str
    base_url: str = ""       # not required for heuristic
    model: str = ""          # not required for heuristic
    player_type: str = "llm" # "llm" | "heuristic"
```

### CLI Changes

```
--player1-type {llm,heuristic}   Player 1 type (default: llm)
--player2-type {llm,heuristic}   Player 2 type (default: llm)
```

When `player_type == "heuristic"`, `--player1-url` and `--player1-model` become optional (default to empty strings).

### Player Factory

```python
def _make_player(config: PlayerConfig) -> AIPlayer | HeuristicPlayer:
    if config.player_type == "heuristic":
        return HeuristicPlayer(config)
    return AIPlayer(config)
```

Called in `__main__.py` instead of `[AIPlayer(pc) for pc in config.players]`.

## Implementation Sequence

1. **Extend `PlayerConfig`** — add `player_type: str = "llm"` field
2. **Create `HeuristicPlayer`** — full rule-based `decide()` implementation
3. **Update `AIPlayer.decide()`** — add optional `legal_actions`, `game_state` kwargs (ignored by AIPlayer)
4. **Update `GameLoop`** — pass `legal_actions` and `game_state` to `decide()`; update type annotation
5. **Update `__main__.py`** — add `--player1-type` / `--player2-type` flags; use `_make_player()` factory
6. **Add tests** — unit tests for each heuristic rule

# Data Model: AI CLI Client for MTG Games

**Branch**: `008-ai-cli-client` | **Date**: 2026-03-21

The CLI is stateless — all game state is owned by the engine. The client defines lightweight data structures for configuration and per-turn bookkeeping only.

---

## PlayerConfig

Represents one AI player as parsed from a `--player` CLI argument.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Display name used when creating the game (e.g. `"Llama"`) |
| `base_url` | `str` | Base URL of the OpenAI-compatible API (e.g. `"http://localhost:11434/v1"`) |
| `model` | `str` | Model identifier to pass in the chat completion request (e.g. `"llama3"`) |

**Parsing rule**: `--player` value is a comma-separated triple: `name,url,model`. Example: `"Bolt,http://localhost:11434/v1,llama3.2"`.

**Validation**:
- All three fields must be non-empty
- `base_url` must start with `http://` or `https://`
- At least two `--player` flags must be supplied

---

## GameConfig

Top-level configuration assembled from all CLI arguments before the game starts.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `players` | `list[PlayerConfig]` | required | Ordered list of players; index 0 = player 1 |
| `engine_url` | `str` | `"http://localhost:8000"` | MTG engine API base URL |
| `deck1` | `list[str]` | built-in test deck | Card names for player 1's deck |
| `deck2` | `list[str]` | built-in test deck | Card names for player 2's deck |
| `verbose` | `bool` | `False` | If true, enable engine verbose mode and print full game state each turn |
| `max_turns` | `int` | `200` | Safety limit to terminate infinite games |

---

## TurnRecord

Captures the inputs and outputs of a single turn decision for console logging. Not persisted.

| Field | Type | Description |
|-------|------|-------------|
| `turn_number` | `int` | Engine turn counter |
| `player_name` | `str` | Name of the player who acted |
| `phase` | `str` | Phase at the time of the decision (e.g. `"PRECOMBAT_MAIN"`) |
| `step` | `str` | Step at the time of the decision (e.g. `"MAIN"`) |
| `legal_actions` | `list[dict]` | Full list of legal actions as returned by the engine |
| `chosen_index` | `int` | Index into `legal_actions` of the chosen action |
| `reasoning` | `str` | AI-provided rationale text, or `"(no reasoning provided)"` |
| `action_description` | `str` | Human-readable description of the chosen action from the engine |
| `fallback_used` | `bool` | True if AI failed and action 0 was submitted as a fallback |

---

## GameSummary

Produced at game end and printed to the console.

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `str` | Engine-assigned game identifier |
| `winner` | `str \| None` | Name of winning player, or `None` if draw/timeout |
| `total_turns` | `int` | Total turn count at game end |
| `total_decisions` | `int` | Total number of AI decisions made (not counting pass-through steps) |
| `termination_reason` | `str` | `"game_over"`, `"max_turns_reached"`, or `"engine_error"` |

---

## Entity Relationships

```
GameConfig
  ├── players: [PlayerConfig, PlayerConfig, ...]
  ├── deck1: [str, ...]
  └── deck2: [str, ...]

GameLoop (runtime, not persisted)
  ├── config: GameConfig
  ├── game_id: str            ← from engine POST /game
  ├── turn_count: int
  ├── decision_count: int
  └── per-turn: TurnRecord    ← constructed and logged, then discarded

GameSummary                   ← built at game end from GameLoop state
```

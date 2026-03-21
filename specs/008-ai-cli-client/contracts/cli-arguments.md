# CLI Argument Contract: AI CLI Client

**Branch**: `008-ai-cli-client` | **Date**: 2026-03-21

## Invocation

```
python -m ai_client [OPTIONS]
```

or, if installed as a script entry point:

```
mtg-ai [OPTIONS]
```

---

## Required Arguments

### `--player NAME,URL,MODEL` (repeatable, minimum 2)

Define one AI player. This flag must appear at least twice.

| Part | Description | Example |
|------|-------------|---------|
| `NAME` | Display name for this player | `Llama` |
| `URL` | Base URL of an OpenAI-compatible API | `http://localhost:11434/v1` |
| `MODEL` | Model identifier passed in the chat completion request | `llama3.2` |

**Format**: comma-separated triple with no spaces around commas.

```bash
--player "Llama,http://localhost:11434/v1,llama3.2"
--player "Mistral,http://localhost:11435/v1,mistral"
```

Players are assigned to game slots in the order the `--player` flags appear. The first `--player` is player 1; the second is player 2.

---

## Optional Arguments

### `--engine URL`

Base URL of the MTG engine REST API.

| Default | `http://localhost:8000` |
|---------|------------------------|

```bash
--engine http://192.168.1.10:8000
```

---

### `--deck1 CARD[,CARD,...]`

Comma-separated list of card names for player 1's deck.

| Default | Built-in 40-card test deck |
|---------|---------------------------|

```bash
--deck1 "Plains,Plains,Plains,Grizzly Bears,Lightning Bolt"
```

---

### `--deck2 CARD[,CARD,...]`

Comma-separated list of card names for player 2's deck.

| Default | Same built-in 40-card test deck as `--deck1` default |
|---------|------------------------------------------------------|

---

### `--verbose`

Enable engine play-by-play logging and print full game state to the console between turns.

| Default | Off |
|---------|-----|

---

### `--max-turns N`

Maximum number of turns before the game is forcibly ended and results printed.

| Default | `200` |
|---------|-------|

---

### `--help`

Print usage information and exit.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Game completed normally (winner decided or max turns reached) |
| `1` | Unrecoverable error (engine unreachable at startup, invalid arguments) |

---

## Console Output Contract

Each turn prints a block in this format:

```
─────────────────────────────────────────
Turn 3 | PRECOMBAT_MAIN / MAIN
Player: Llama
Reasoning: I have three mana available. Casting Grizzly Bears is the best play
           to develop my board presence before the opponent stabilises.
Action: Cast Grizzly Bears
─────────────────────────────────────────
```

If verbose mode is enabled, the full board state is printed after each turn block.

On game end:

```
════════════════════════════════════════
GAME OVER
Winner : Llama
Game ID: abc123
Turns  : 12
Decisions made: 47
Reason : game_over
════════════════════════════════════════
```

If the AI endpoint failed and a fallback pass was used:

```
[WARNING] Llama AI endpoint failed (attempt 1/2): Connection refused
[WARNING] Llama AI endpoint failed (attempt 2/2): Connection refused
[WARNING] Falling back to pass priority for Llama
```

---

## Full Invocation Example

```bash
python -m ai_client \
  --player "Llama,http://localhost:11434/v1,llama3.2" \
  --player "Mistral,http://localhost:11435/v1,mistral-7b" \
  --engine http://localhost:8000 \
  --verbose \
  --max-turns 150
```

# Feature Specification: AI CLI Client for MTG Games

**Feature Branch**: `008-ai-cli-client`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "I would now like to create a command line client application that will use 2+ openai compatible AIs (local llm) to play a game via hitting the api endpoints. The turns and thoughts should be logged to the console. I should be able to pass each player AI and url via the command line"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch AI vs AI Game (Priority: P1)

A user invokes the CLI with two or more AI player configurations (each with a player name, model name, and API endpoint URL) and watches a full game play out automatically in the terminal. Both AIs make decisions each turn by querying their respective LLM endpoints, and every action and game event is printed to the console.

**Why this priority**: This is the core deliverable. Without the autonomous game loop, no other story has value.

**Independent Test**: Can be fully tested by running the CLI with two local LLM endpoints and observing a complete game from start to finish in the terminal.

**Acceptance Scenarios**:

1. **Given** two AI player configs supplied on the command line, **When** the CLI starts, **Then** a game is created via the engine API, both AIs are registered as players, and the game loop begins immediately.
2. **Given** the game is in progress, **When** it is a player's turn, **Then** that player's AI endpoint is queried with the current game state, and the returned action is submitted to the game API.
3. **Given** the game has ended, **When** a winner is determined, **Then** the CLI prints a final summary (winner, game ID, turn count) and exits cleanly with code 0.

---

### User Story 2 - Console Turn & Thought Logging (Priority: P2)

Every AI decision is accompanied by visible reasoning in the terminal. The user can follow what each AI is "thinking" before it acts, making it possible to audit, debug, or spectate the game.

**Why this priority**: Without visible reasoning the tool is a black box. Logging turns and thoughts is an explicit requirement and makes the tool useful for evaluation and debugging.

**Independent Test**: Can be tested independently by running a game and verifying that each turn logs the AI's reasoning text and chosen action before the action is submitted to the API.

**Acceptance Scenarios**:

1. **Given** it is an AI player's turn, **When** the AI endpoint returns a response, **Then** the console logs the player's name, the AI's stated reasoning/thought text, and the chosen action on clearly labelled lines.
2. **Given** the AI returns a response with no explicit reasoning, **When** the action is logged, **Then** the raw response or a placeholder is displayed so no output is silently dropped.
3. **Given** an optional verbose flag is supplied, **When** game events occur between turns, **Then** full game-state information and zone changes are also printed.

---

### User Story 3 - Flexible Per-Player CLI Configuration (Priority: P3)

Each player's AI model and API endpoint are independently configurable from the command line. The user can point player 1 at one local LLM server and player 2 at a different server (or a different model on the same server) without editing any file.

**Why this priority**: The ability to mix different models and endpoints per player is a stated requirement enabling A/B evaluation of different AIs.

**Independent Test**: Can be tested by supplying different endpoint URLs for each player and confirming each player sends requests only to its own configured URL during the game.

**Acceptance Scenarios**:

1. **Given** a CLI invocation with `--player "Player1,http://host1/v1,model-a" --player "Player2,http://host2/v1,model-b"`, **When** it is Player1's turn, **Then** the HTTP request goes to `http://host1/v1` using `model-a`, not to Player2's URL.
2. **Given** three or more `--player` flags are supplied, **When** the game starts, **Then** all players are registered and each routes independently to its own endpoint.
3. **Given** a required CLI argument is missing (e.g., no `--player` flags), **When** the CLI starts, **Then** a descriptive usage error is printed and the process exits with a non-zero code.

---

### Edge Cases

- What happens when an AI endpoint is unreachable or returns an HTTP error mid-game?
- How does the system handle an AI that returns an invalid or unrecognised action?
- What happens when the game API itself returns an error (e.g., illegal move)?
- How are infinite loops prevented if an AI repeatedly returns the same invalid action?
- What happens if more `--player` flags are supplied than the game engine supports?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST accept two or more player definitions via command-line arguments, each specifying a player name, an OpenAI-compatible API base URL, and a model identifier.
- **FR-002**: The CLI MUST create a new game via the MTG engine API at startup and register all configured AI players.
- **FR-003**: The CLI MUST query the appropriate AI endpoint on each player's turn, passing a prompt containing the current game state.
- **FR-004**: The CLI MUST parse the AI response and submit the chosen action to the game API.
- **FR-005**: The CLI MUST log each turn to the console, including the active player's name, the AI's reasoning/thought text, and the action taken.
- **FR-006**: The CLI MUST continue the game loop until the game API signals the game has ended.
- **FR-007**: The CLI MUST print a final summary (winner, game ID, turn count) upon game completion.
- **FR-008**: The CLI MUST handle AI endpoint errors gracefully — retrying once before logging the error and submitting a default/pass action to avoid game deadlock.
- **FR-009**: The CLI MUST support an optional verbose flag that enables additional game-state output (zone changes, full board state) between turns.
- **FR-010**: The CLI MUST exit with code 0 on clean game completion and a non-zero code on unrecoverable errors.
- **FR-011**: The CLI MUST provide a `--help` flag that documents all required and optional arguments.
- **FR-012**: The CLI MUST support an optional argument to specify the engine API base URL, defaulting to `http://localhost:8000`.

### Key Entities

- **Player**: A named participant in the game with an assigned AI endpoint URL, model identifier, and player slot in the game API.
- **Turn**: A single decision cycle for one player — includes the game-state prompt sent to the AI, the AI response received, and the action submitted to the game API.
- **Action**: A structured game move derived from the AI response and sent to the MTG engine API.
- **Game Session**: The active game identified by a game ID from the engine API, tracking all turns from start to finish.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A two-player AI game runs to completion without manual intervention from start to finish.
- **SC-002**: Every turn produces at least one visible console log entry containing the player name and chosen action — no silent turns.
- **SC-003**: Each player's AI requests are sent exclusively to that player's configured endpoint, with zero cross-player routing errors across a full game.
- **SC-004**: An unreachable AI endpoint causes the CLI to log a clear error message and continue the game rather than hanging or crashing silently.
- **SC-005**: A user unfamiliar with the tool can determine the correct invocation using only the `--help` output within 2 minutes.

## Assumptions

- The MTG engine API is already running and accessible; the engine base URL defaults to `http://localhost:8000` but is overridable via CLI argument.
- AI endpoints are OpenAI-compatible — they accept a chat completions request with a `model` and `messages` array and return a `choices[0].message.content` field.
- Deck selection for each player either defaults to a pre-configured test deck or is specifiable as an optional CLI argument.
- The game API's existing endpoints (`POST /game`, game action endpoints, `GET /game/{id}`) are sufficient to drive the game loop; no new engine API endpoints are required.
- Console output is plain text suitable for a standard terminal; no TUI or curses interface is required.
- A single sequential game loop is sufficient — parallel multi-game execution is out of scope for this feature.

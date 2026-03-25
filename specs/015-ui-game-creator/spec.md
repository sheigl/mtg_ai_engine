# Feature Specification: UI Game Creator

**Feature Branch**: `015-ui-game-creator`
**Created**: 2026-03-23
**Status**: Draft
**Input**: User description: "I would like to be able to create AI games from the UI, everything that the ai_client command line can do I would like to be able to do from the UI as well"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch a Standard AI Game (Priority: P1)

A user opens the web UI and creates a new AI vs AI game without leaving the browser. They configure both players (choosing LLM or heuristic engine for each), enter the endpoint and model for LLM players, optionally customise deck lists, and click a button to start the game. The UI then navigates directly to the live game board.

**Why this priority**: This is the core value — removing the need to drop to a terminal to start a game. Everything else is refinement on top.

**Independent Test**: Can be fully tested by filling out the game creation form and verifying that a live game board loads and progresses autonomously.

**Acceptance Scenarios**:

1. **Given** the game list page, **When** the user clicks "New AI Game", **Then** a game creation form is displayed with fields for both players.
2. **Given** the form with player type set to "LLM", **When** the user enters a valid endpoint URL and model name, **Then** those fields are accepted without error.
3. **Given** the form with player type set to "Heuristic", **When** the user submits, **Then** URL and model fields are not required and the game starts using the built-in heuristic engine.
4. **Given** a completed and valid form, **When** the user clicks "Start Game", **Then** the game is created and the UI navigates to the live game board for that game.
5. **Given** an invalid or unreachable LLM URL, **When** the user submits, **Then** an informative error is shown and the form remains open with the user's input intact.

---

### User Story 2 - Configure Decks (Priority: P2)

A user wants to play with specific card lists rather than the default built-in deck. They can enter a custom comma-separated list of card names for each player directly in the creation form.

**Why this priority**: Deck customisation is important for testing specific scenarios, but the default deck still provides a working game, so this is not blocking.

**Independent Test**: Can be tested by entering a known card list, starting a game, and verifying those cards appear in the game board for the correct player.

**Acceptance Scenarios**:

1. **Given** the creation form, **When** the user enters a comma-separated list of card names for Player 1, **Then** the game is created using those cards.
2. **Given** the creation form with no deck entered for a player, **When** the user submits, **Then** the default built-in deck is used for that player.
3. **Given** an invalid card name in the deck list, **When** creation is attempted, **Then** an error is shown identifying the problem and the game is not created.

---

### User Story 3 - Commander Format (Priority: P3)

A user wants to start a Commander-format game. They switch the format selector to "Commander", enter two commander names (one per player), and optionally provide full deck lists. The game starts with 40 starting life and commanders available in the command zone.

**Why this priority**: Commander is a supported format but less common for automated testing than standard. The standard flow must work first.

**Independent Test**: Can be tested by selecting Commander format, entering two legendary creature names, starting a game, and verifying 40 starting life and the command zone on the board.

**Acceptance Scenarios**:

1. **Given** format set to "Commander", **When** commander name fields appear and the user fills both in, **Then** the game is created as a commander game with the correct starting life.
2. **Given** Commander format with only one commander name entered, **When** the user submits, **Then** an error is shown requiring both commander names.
3. **Given** a non-legendary card entered as a commander, **When** submitted, **Then** the engine's validation error is surfaced clearly in the UI.

---

### User Story 4 - Debug and Observer Options (Priority: P4)

A user wants to capture AI reasoning during the game. They enable the debug toggle in the creation form and optionally specify a separate observer AI endpoint and model. When the game starts, the debug panel opens automatically and observer commentary appears alongside player decisions.

**Why this priority**: Debug/observer options are powerful for analysis but not needed for a basic game.

**Independent Test**: Can be tested by enabling debug in the form, starting a game, and verifying the debug panel is active and receiving entries on the game board.

**Acceptance Scenarios**:

1. **Given** the creation form with debug enabled, **When** the game starts, **Then** the debug panel is active automatically on the game board.
2. **Given** debug enabled and an observer URL and model entered, **When** the game runs, **Then** observer AI commentary appears in the debug panel.
3. **Given** debug enabled with LLM players and no separate observer specified, **Then** the first LLM player's endpoint is used as the observer.
4. **Given** debug enabled with only heuristic players and no observer endpoint entered, **When** submitted, **Then** a warning informs the user that no LLM is available for commentary, but the game still starts.

---

### User Story 5 - Advanced Options (Priority: P5)

A user wants to control the max-turns limit and verbose play-by-play logging. These are available as optional advanced fields collapsed by default, matching the CLI flags `--max-turns` and `--verbose`.

**Why this priority**: Useful for long-running tests and debugging but rarely needed for casual use.

**Independent Test**: Can be tested by setting max turns to 5, starting a game, and verifying the game ends after 5 turns with the appropriate termination reason.

**Acceptance Scenarios**:

1. **Given** the advanced options section expanded, **When** the user sets max turns to a specific number, **Then** that limit is applied to the game.
2. **Given** verbose logging enabled in the form, **When** the game runs, **Then** play-by-play events appear in the game's action log.
3. **Given** no max-turns value entered, **Then** the system default (200 turns) is applied.

---

### Edge Cases

- What happens when the engine is unreachable at submission time? → Show a clear connection error; do not navigate away from the form.
- What happens if the deck has fewer than the required minimum cards? → Surface the engine's validation error with the specific reason.
- What happens if both players are LLM but no endpoints are entered? → Client-side validation prevents submission with a clear field-level error.
- What happens if the user navigates away mid-form? → No game is created; form state is lost (no persistence required).
- What happens if the same player name is used for both players? → An error is shown; player names must be unique.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST provide a "New AI Game" entry point accessible from the game list page.
- **FR-002**: The creation form MUST allow configuring a name, type (LLM or Heuristic), endpoint URL, and model for each of the two players.
- **FR-003**: Endpoint URL and model fields MUST be required when player type is LLM, and hidden when type is Heuristic.
- **FR-004**: The form MUST allow entering a custom comma-separated card list for each player, with a clear indication that leaving it blank uses the default deck.
- **FR-005**: The form MUST include a format selector (Standard / Commander); selecting Commander MUST reveal two commander name fields.
- **FR-006**: The form MUST include a debug toggle; enabling it MUST reveal an optional observer endpoint and model field.
- **FR-007**: The form MUST include an advanced section (collapsed by default) with a max-turns numeric input and a verbose toggle.
- **FR-008**: On successful submission, the UI MUST navigate to the live game board for the newly created game.
- **FR-009**: Validation errors from the engine MUST be displayed on the form without losing the user's entered values.
- **FR-010**: Client-side validation MUST prevent submission when required fields are missing or invalid.
- **FR-011**: Player names MUST be unique; the form MUST reject identical names for both players.

### Key Entities

- **GameCreationConfig**: Captures all options for a new game — two player configs (name, type, URL, model), deck1, deck2, format, commander1, commander2, verbose, max_turns, debug, observer_url, observer_model.
- **Player Config**: name, type (llm | heuristic), endpoint URL (required for LLM), model (required for LLM).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can configure and launch an AI game entirely from the browser in under 2 minutes without using the command line.
- **SC-002**: All options available via the `ai_client` CLI are reachable from the UI form — no capability gap between CLI and UI.
- **SC-003**: Engine validation errors are surfaced in the UI within 3 seconds of form submission with actionable messages.
- **SC-004**: The form prevents 100% of submissions with missing required fields through client-side validation.
- **SC-005**: A game started from the UI behaves identically to one started via the CLI with equivalent arguments.

## Assumptions

- The AI decision loop runs via an existing backend mechanism triggered after game creation; the UI only needs to initiate creation and then observe via the game board.
- Player names default to "Player 1" / "Player 2" if left blank.
- The default max-turns value matches the CLI default (200).
- No authentication or user accounts are required — this is a local developer tool.
- Form state does not need to persist across page refreshes.
- The engine URL (where the MTG engine is running) is the same as the UI's backend and does not need to be configured separately.

# Feature Specification: Game Series Mode (Best-of-N)

**Feature Branch**: `032-game-series`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "I would like to set the number of consecutive games that the players will play against one another. So for example if I set 6 games, once one game ends another will start using the same settings as before."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Configure Game Series (Priority: P1)

As a user creating an AI vs AI or human vs AI game, I want to specify how many consecutive games the same players should play with the same settings, so that I can run a multi-game tournament or experiment.

**Why this priority**: This is the core feature request — without the ability to configure a series, users must manually recreate games.

**Independent Test**: Can be tested by opening the create-game modal or Play vs AI page and verifying a "Series count" field is present.

**Acceptance Scenarios**:

1. **Given** the user opens the create-game modal (AI vs AI), **When** they view the form, **Then** they see a "Series count" field defaulting to 1.
2. **Given** the user opens the Play vs AI page, **When** they view the form, **Then** they see a "Series count" field defaulting to 1.
3. **Given** the user sets series count to 6, **When** they submit the form, **Then** the backend creates a series with 6 scheduled games.
4. **Given** the user sets series count to 0 or leaves it blank, **When** they submit, **Then** it defaults to 1 (single game).

---

### User Story 2 — Automatic Series Progression (Priority: P1)

As a user who started a series, I want each game to automatically start after the previous one ends, using identical settings, so that the series runs without manual intervention.

**Why this priority**: Without automatic progression, the series feature provides no value.

**Independent Test**: Can be tested by creating a series of 3 games and verifying that after game 1 ends, game 2 appears in the game list, then game 3.

**Acceptance Scenarios**:

1. **Given** a 3-game series is running, **When** game 1 ends, **Then** game 2 automatically starts with the same player names, decks, format, and AI settings.
2. **Given** a series game ends, **When** the next game starts, **Then** the deck is reshuffled (new random seed) so each game is independent.
3. **Given** a human vs AI series, **When** the human finishes game 1, **Then** the human is redirected or can navigate to game 2.
4. **Given** all games in a series have completed, **When** the final game ends, **Then** no more games are spawned.

---

### User Story 3 — View Series Progress (Priority: P2)

As a user viewing the game list, I want to see which games belong to a series and the current score, so that I can track who is winning.

**Why this priority**: Visual feedback makes the series feature usable. Without it, users see many seemingly unrelated games.

**Independent Test**: Can be tested by looking at the game list and verifying series games show progress indicators.

**Acceptance Scenarios**:

1. **Given** a series is in progress, **When** the user views the game list, **Then** games in the series show "Game N of M" and the current win count (e.g., "Alice 2 — Bob 1").
2. **Given** a series game is active, **When** it appears in the game list, **Then** it shows the series badge and score.
3. **Given** a series has completed, **When** the user views the game list, **Then** the final game shows the completed series score.

---

### Edge Cases

- What happens if the server restarts mid-series? Series progress is lost (in-memory only) — this is acceptable for MVP.
- What happens if a game in a series is deleted? The series stops spawning new games.
- What happens if series count is set to 1? It behaves exactly like a normal single game.
- How are draws handled? Draws count toward the total but don't award a win to either player.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All game creation forms MUST have a "Series count" field (positive integer, default 1).
- **FR-002**: When series count > 1, the backend MUST create a series record tracking total games, settings, and results.
- **FR-003**: When a game in a series ends, the backend MUST automatically create the next game with identical settings (except a new random seed).
- **FR-004**: The series MUST stop spawning games when the target count is reached.
- **FR-005**: Games in a series MUST be visually grouped in the game list with win counts.
- **FR-006**: The series settings MUST include: player names, player types, decks, format, commanders, AI URLs/models, debug/observer settings.
- **FR-007**: Human vs AI series MUST allow the human to continue playing through all games in the series.

### Key Entities

- **GameSeries**: Tracks series state (total games, completed games, settings, results).
- **SeriesResult**: Per-game outcome (game_id, winner, turn count).
- **GameState.series_id**: Optional link from a game to its parent series.

## Success Criteria *(mandatory)*

- **SC-001**: A user can create a 5-game AI vs AI series from the modal and all 5 games complete without manual intervention.
- **SC-002**: A user can create a 3-game human vs AI series and play through all 3 games.
- **SC-003**: The game list shows series progress ("Game 2 of 5", score) for series games.
- **SC-004**: Series games use independent random seeds (reshuffled decks each game).
- **SC-005**: No regressions in single-game creation or gameplay.

## Assumptions

- Series state is stored in-memory only (acceptable for MVP).
- The same deck lists are reused each game but reshuffled.
- For human vs AI series, the human uses the same name each game.

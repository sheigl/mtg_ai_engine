# Feature Specification: MongoDB Game Data Persistence

**Feature Branch**: `025-mongodb-persistence`
**Created**: 2026-04-19
**Status**: Draft
**Input**: User description: "I would like to save all game data to mongodb instead of downloading a file. I want it to save as it is happening as well. Remember this is reinforcement learning for AI models."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Game Data Capture (Priority: P1)

As a researcher training AI models on MTG gameplay, all game events — actions, board states, AI decisions, observer commentary, and player annotations — are automatically saved to persistent storage as they occur during a game. No manual export step is required. The data is immediately available for training pipelines to read.

**Why this priority**: This is the core ask. Without persistent, live capture, the training data pipeline cannot run without manual intervention for every game. This is the MVP that makes the system useful for reinforcement learning at scale.

**Independent Test**: Start a game, play several turns, then query the storage system directly to confirm turn actions, board snapshots, and AI decisions were persisted without any download being triggered.

**Acceptance Scenarios**:

1. **Given** a game is in progress, **When** a player takes an action, **Then** that action is persisted to storage within 1 second without any user interaction.
2. **Given** a game is in progress, **When** the observer AI produces commentary, **Then** the commentary entry (including rating, explanation, and any player annotation) is persisted as it streams and finalized when complete.
3. **Given** a game ends, **When** the game-over state is reached, **Then** all remaining data (outcome, final board state) is flushed to storage and the game record is marked complete.
4. **Given** a game is in progress and the server restarts unexpectedly, **When** the game resumes (or a new game starts), **Then** previously persisted data for completed turns is not lost.

---

### User Story 2 - Training Data Export & Query (Priority: P2)

As a researcher, I can retrieve saved game data in a structured format suitable for feeding directly into an AI training pipeline — without downloading individual files or manually stitching together game logs. I can query games by outcome, player type (human vs AI), format, and date range.

**Why this priority**: Persistence alone is not enough — the training pipeline needs to read the data back in a structured, queryable way. This story makes the stored data actionable.

**Independent Test**: After completing several games, query the storage system to retrieve all games from today where a human player participated, and verify the returned records contain complete turn-by-turn action sequences, AI commentary, and game outcomes.

**Acceptance Scenarios**:

1. **Given** multiple completed games are stored, **When** a training script queries by game format and date range, **Then** it receives a list of matching game records with full action histories.
2. **Given** a completed game record, **When** the full game document is retrieved, **Then** it contains: all turn actions, board snapshots at key moments, AI decisions with prompts and responses, observer commentary with ratings, player annotations, and the final outcome.
3. **Given** a game with player rating overrides, **When** the training data is retrieved, **Then** both the original AI rating and the player override are present in each commentary record, preserving training data integrity.

---

### User Story 3 - Backward-Compatible File Export (Priority: P3)

The existing game log download (plain-text file export) continues to work alongside persistent storage. Researchers who prefer the file-based workflow are not disrupted.

**Why this priority**: Some existing workflows depend on the file download. This story ensures the new persistence layer does not break existing behavior — it is additive, not a replacement.

**Independent Test**: Complete a game, download the game log file, and verify it is identical in format to logs produced before this feature was introduced.

**Acceptance Scenarios**:

1. **Given** a completed game with data persisted to storage, **When** a user downloads the game log, **Then** the downloaded file is generated from the stored data and matches the existing format exactly.
2. **Given** the storage system is temporarily unavailable, **When** a user attempts to download the game log, **Then** the system falls back to generating the log from in-memory data and a clear warning is shown.

---

### Edge Cases

- What happens when the storage system is unavailable at game start? The game proceeds normally; events are queued in memory and flushed when storage reconnects.
- What happens if a game crashes mid-turn before a batch of events is persisted? Only events from completed flushes are in storage; partial turns are not written.
- What happens with very long games (100+ turns) where storage documents grow large? Documents are structured to handle incremental appending of turn data without full rewrites.
- How are concurrent games handled? Each game has an isolated document/record; concurrent writes from multiple games do not interfere.
- What happens if a player annotation is added after the game ends? The record is updated in place; the original AI data is never overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically persist every game action to persistent storage as it occurs, without requiring any user interaction.
- **FR-002**: System MUST persist AI player decisions (prompt, response, and any structured metadata) to storage as they complete streaming.
- **FR-003**: System MUST persist observer AI commentary entries (rating, explanation, alternative, and thinking tokens) to storage as they complete streaming.
- **FR-004**: System MUST persist board state snapshots at the start of each turn and at key phase transitions.
- **FR-005**: System MUST persist the final game outcome (winner, turn count, format) when a game ends.
- **FR-006**: System MUST persist player annotations and rating overrides to storage when they are saved, updating the corresponding entry in-place without overwriting original AI data.
- **FR-007**: System MUST support querying stored games by: game format, date/time range, presence of human player, and completion status.
- **FR-008**: System MUST mark each game record as complete when the game ends, distinguishing in-progress games from finished ones.
- **FR-009**: The existing plain-text game log download endpoint MUST continue to function correctly alongside the new persistence layer.
- **FR-010**: System MUST handle storage unavailability gracefully — games proceed without interruption; a reconnection mechanism retries pending writes.
- **FR-011**: Each persisted game record MUST include: game ID, format, player names, player types (human/AI), start timestamp, end timestamp (when complete), and a structured sequence of all events.
- **FR-012**: Storage writes for in-progress game events MUST complete within 2 seconds of the event occurring under normal conditions.

### Key Entities

- **Game Record**: The top-level document for a single game. Contains metadata (game ID, format, players, timestamps, completion status) and references to all sub-records.
- **Turn Action**: A single player action (play land, cast spell, declare attackers, pass priority, etc.) with the game state context at the time it occurred.
- **Board Snapshot**: A point-in-time capture of the full board state (all permanents, player life totals, hand sizes, graveyard contents) taken at turn boundaries and key phase transitions.
- **AI Decision Record**: An AI player's prompt and response for a given game state, including the chosen action and any chain-of-thought reasoning.
- **Commentary Entry**: An observer AI evaluation of an action, including the rating (good/acceptable/suboptimal), explanation, suggested alternative, and any player override or annotation.
- **Game Outcome**: The final result: winner, losing condition, total turns played, and any relevant end-game statistics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All game events are persisted within 2 seconds of occurring — verifiable by querying storage immediately after an event and confirming the record exists.
- **SC-002**: A completed game's full training record is retrievable in a single query — no multi-step joins or file assembly required.
- **SC-003**: 100% of game events from a completed game are present in storage — verifiable by comparing the stored record against the in-memory transcript at game end.
- **SC-004**: Training pipelines can query and retrieve 1,000 completed game records in under 10 seconds.
- **SC-005**: The existing file download continues to produce output identical to pre-feature behavior — verified by a diff against a known baseline log.
- **SC-006**: Storage failure does not cause game interruption — games complete normally even when the storage system is unavailable.

## Assumptions

- A document-oriented persistent store is accessible to the game engine server (connection string provided via environment variable or configuration file).
- The storage system supports atomic upserts/updates so that partial writes do not corrupt existing records.
- Training pipelines will read data directly from storage using the same query interface — no additional transformation layer is needed for the initial version.
- Human-vs-AI and AI-vs-AI games are both captured; human-vs-human is out of scope (not a supported game mode).
- Data retention policy is indefinite for now — all completed game records are kept; no automatic pruning.
- The storage connection is local or low-latency (same datacenter); high-latency remote storage is out of scope for the initial version.
- Authentication to the storage system (if required) is handled via environment configuration, not user-facing login.

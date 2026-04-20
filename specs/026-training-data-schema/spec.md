# Feature Specification: Training Data Schema — Decision-Centric MongoDB Persistence

**Feature Branch**: `026-training-data-schema`  
**Created**: 2026-04-20  
**Status**: Draft  
**Input**: Redesign the MongoDB persistence layer so that all game data is properly linked for AI model training purposes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Retrieve a Complete Training Example (Priority: P1)

A data scientist or ML engineer wants to retrieve a single decision point from a completed game and have everything needed to train a model immediately available — board state, legal actions, the LLM's reasoning, the observer's quality rating, and whether the player won — without writing any join logic.

**Why this priority**: This is the entire point of the feature. Without a self-contained decision record, the training pipeline cannot be built.

**Independent Test**: Query a single document from the `decisions` collection after a completed game and verify it contains board state, legal actions, action taken, llm_reasoning, observer_evaluation, and outcome_context all in one document.

**Acceptance Scenarios**:

1. **Given** a completed game with an LLM player and an observer, **When** a `decisions` document is fetched by `decision_id`, **Then** it contains `board_state`, `legal_actions`, `action_taken`, `llm_reasoning` (with prompt, thinking, response, rating), `observer_evaluation` (with rating, explanation, alternative), and `outcome_context` (with `active_player_won`).
2. **Given** a completed game with only a heuristic player, **When** a `decisions` document is fetched, **Then** `llm_reasoning` is `null` and `observer_evaluation` is `null`, but `board_state`, `legal_actions`, and `action_taken` are still present.
3. **Given** a completed game, **When** all `decisions` for that game are fetched and sorted by `sequence_number`, **Then** they represent the complete ordered sequence of decision points for that game.

---

### User Story 2 — Filter Training Data by Player and Outcome (Priority: P2)

A researcher wants to pull all decision points where the active player ultimately won, or all decisions made by a specific player, to create outcome-stratified training sets.

**Why this priority**: Outcome-stratified slices (win vs loss) and per-player slices are the most common training data queries; supporting them via indexes is essential.

**Independent Test**: Query `decisions` with `{ game_id: X, active_player: "Alice" }` and verify only Alice's decision points are returned, each with `outcome_context.active_player_won` correctly set.

**Acceptance Scenarios**:

1. **Given** multiple completed games, **When** querying decisions filtered by `active_player` and `outcome_context.active_player_won = true`, **Then** only winning-player decision points are returned.
2. **Given** a completed game, **When** `outcome_context` is checked on any decision document, **Then** `active_player_won` correctly reflects whether the active player at that decision point won the game.

---

### User Story 3 — Inspect Observer Evaluation Linked to a Specific Decision (Priority: P3)

A quality reviewer wants to find all decisions where the observer rated the action as `suboptimal` and inspect both the LLM's reasoning and the observer's explanation side-by-side.

**Why this priority**: Post-game review and human annotation workflows require decisions and their evaluations to be co-located.

**Independent Test**: Query `decisions` where `observer_evaluation.rating = "suboptimal"` and verify each result contains both `llm_reasoning` and `observer_evaluation` in the same document.

**Acceptance Scenarios**:

1. **Given** a game where the observer rated some decisions as `suboptimal`, **When** those decisions are queried, **Then** each document contains both the LLM reasoning and the observer's full evaluation (rating, explanation, alternative).
2. **Given** a decision where the player provided a manual annotation override, **When** that decision is fetched, **Then** `llm_reasoning.player_annotation` and `llm_reasoning.player_rating_override` reflect the updated values.

---

### User Story 4 — Retrieve Rules Q&A in Context (Priority: P4)

A researcher wants to see which rules questions were asked during a specific decision point to understand what ambiguity existed at that moment.

**Why this priority**: Rules Q&A records provide important context about why an LLM made a particular decision.

**Independent Test**: After a game where a rules Q&A was triggered, query `rules_qa` by `game_id` and verify each entry has a `decision_id` linking it to the correct decision point.

**Acceptance Scenarios**:

1. **Given** a rules Q&A that occurred during a specific priority grant, **When** that Q&A entry is fetched, **Then** its `decision_id` matches the corresponding `decisions` document.

---

### Edge Cases

- What happens when an LLM player's debug entry arrives before the corresponding snapshot is finalized? The decision document must be upserted incrementally so late-arriving entries are merged in correctly.
- What happens when the observer entry arrives before the player's debug entry? Both must be stored under the correct `snapshot_id` regardless of arrival order.
- What happens when a game ends abnormally (disconnect, timeout)? `outcome_context` on all decisions for that game should be backfilled with whatever outcome data is available, or left `null` if unavailable.
- What happens when a decision has no action taken (pass priority)? `action_taken` is `null` and `action_taken_by` is `null`; this is valid and must be stored.
- What about heuristic-vs-heuristic games with no debug enabled? All decisions are stored with `llm_reasoning: null` and `observer_evaluation: null` — still useful as board state / action data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store each priority grant as an individual document in a `decisions` collection, containing `board_state`, `legal_actions`, `action_taken`, `action_taken_by`, `turn`, `phase`, `step`, `active_player`, `game_id`, `snapshot_id`, and `sequence_number`.
- **FR-002**: Each `decisions` document MUST include an `llm_reasoning` sub-document when the active player is an LLM player, and `null` otherwise.
- **FR-003**: Each `decisions` document MUST include an `observer_evaluation` sub-document when an observer is configured for the game, and `null` otherwise.
- **FR-004**: At game completion, the system MUST backfill `outcome_context` onto every `decisions` document for that game, including `winner`, `winning_player`, `total_turns`, and `active_player_won`.
- **FR-005**: The `games` collection MUST store only top-level game metadata (players, format, timestamps, outcome) — no embedded arrays of decisions, snapshots, or debug entries.
- **FR-006**: The `rules_qa` collection MUST store each Q&A entry as a separate document with a `decision_id` field linking it to the priority grant during which it was triggered.
- **FR-007**: The `transcript` collection MUST store raw game events as individual documents, each with `game_id` and `sequence_number` for ordered replay.
- **FR-008**: The system MUST create indexes on `decisions` for `{ game_id, sequence_number }` and `{ game_id, active_player }` to support training set enumeration and per-player filtering.
- **FR-009**: `DebugEntry` MUST gain a `snapshot_id` field so LLM player and observer entries can be correlated to the board state that prompted them.
- **FR-010**: Observer `DebugEntry` MUST gain a `related_entry_id` field pointing to the player's `DebugEntry` it evaluated.
- **FR-011**: The persistence layer MUST remain entirely optional — all writes are fire-and-forget and failures must never affect game execution.
- **FR-012**: The `game_records` API router MUST be updated to query the new collections and return decisions in sequence order.
- **FR-013**: Human annotation updates (`player_annotation`, `player_rating_override`) MUST be persisted as in-place updates to the correct `decisions` document's `llm_reasoning` sub-document.

### Key Entities

- **Game**: Top-level record identifying two players, format, timestamps, and final outcome. Lives in the `games` collection.
- **Decision**: The primary training unit. One per priority grant. Contains the full board state, legal actions, action chosen, LLM reasoning (if applicable), observer evaluation (if applicable), and outcome context. Lives in the `decisions` collection.
- **LLM Reasoning**: Embedded in a Decision. Contains the full prompt, chain-of-thought thinking tokens, response, auto-rating, and any human annotation.
- **Observer Evaluation**: Embedded in a Decision. Contains the observer's prompt, response, rating, explanation, and suggested alternative action.
- **Outcome Context**: Embedded in a Decision (backfilled at game end). Contains winner name, total turns, and `active_player_won` for use as a training reward signal.
- **Rules Q&A**: Separate document per question, linked to both `game_id` and `decision_id`. Lives in the `rules_qa` collection.
- **Transcript Entry**: Raw game event. Separate document per event, linked to `game_id` with a `sequence_number`. Lives in the `transcript` collection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single `decisions` document fetch returns all data required to construct one training example — no secondary queries needed.
- **SC-002**: All decision documents for a completed game have `outcome_context` populated within 5 seconds of game completion.
- **SC-003**: Fetching all decisions for a game sorted by `sequence_number` produces a complete, gapless ordered sequence of every priority grant in that game.
- **SC-004**: 100% of LLM debug entries and observer entries are linked to their corresponding decision via `snapshot_id` — zero orphaned entries in completed games.
- **SC-005**: The persistence layer adds no observable latency to game execution — all writes are asynchronous and non-blocking.
- **SC-006**: A training dataset of 10,000 decisions can be enumerated and exported using indexed queries in under 60 seconds.

## Assumptions

- No migration of existing data is required. The redesigned schema targets the same MongoDB instance using new collection names; old embedded-array data is not migrated.
- The `MONGODB_URL` environment variable remains the feature flag — if unset, all persistence is silently skipped.
- A `snapshot_id` is already assigned at `SnapshotRecorder.record_snapshot()` time, before any action is taken. This ID is the correlation key passed through to debug entries and the persister.
- The observer always evaluates exactly one player decision per priority grant. If multiple observer entries are produced per grant, only the last completed one is stored as `observer_evaluation`.
- `sequence_number` is a monotonic per-game counter incremented by the persister each time a new decision document is created.
- The existing in-memory `GameExportStore` recorders (transcript, snapshots, debug_log, rules_qa) are unchanged — only the MongoDB write path changes.
- The `game_records` API router will return decisions in sequence order but is not responsible for constructing training batch files or export formats — that is out of scope.

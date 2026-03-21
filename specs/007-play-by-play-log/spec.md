# Feature Specification: Play-by-Play Game Log

**Feature Branch**: `007-play-by-play-log`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "I want to create a new feature to add verbose logging in the form of showing play by play output, mainly I want to see the moves the players make"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Player Moves in Real Time (Priority: P1)

As someone running a game simulation, I want to see a running log of every move each player makes — including spells cast, attacks declared, blockers assigned, and abilities activated — so that I can follow the game's progression without inspecting internal state.

**Why this priority**: This is the core of the feature. Without a readable, chronological record of player actions, there is no play-by-play log at all. Everything else builds on this.

**Independent Test**: Can be fully tested by running a game simulation with verbose mode enabled and verifying that a human-readable action appears in the output for each player decision made during the game.

**Acceptance Scenarios**:

1. **Given** a game is running with verbose logging enabled, **When** a player casts a spell, **Then** a log entry appears immediately identifying the player, the card played, and any relevant targets.
2. **Given** a game is running with verbose logging enabled, **When** a player declares attackers, **Then** a log entry lists each attacking creature and which player or planeswalker it is attacking.
3. **Given** a game is running with verbose logging enabled, **When** a player activates an ability, **Then** a log entry appears naming the source of the ability, the player who activated it, and the relevant targets (if any).
4. **Given** a game is running with verbose logging disabled, **When** the game progresses, **Then** no play-by-play output is produced.

---

### User Story 2 - Track Turn Structure and Phase Transitions (Priority: P2)

As someone reviewing a game log, I want to see clear markers for each turn and phase (e.g., "Player 1 — Main Phase 1", "Combat Phase") so that I can understand the context of each action without needing to count turns manually.

**Why this priority**: Player actions are meaningless without game phase context. Knowing a spell was cast during combat versus a main phase matters for rules and AI analysis.

**Independent Test**: Can be fully tested by running a multi-turn game and verifying that phase boundary markers appear in the log before the actions that occur within each phase.

**Acceptance Scenarios**:

1. **Given** verbose logging is enabled, **When** a new turn begins, **Then** the log displays a turn header identifying whose turn it is and the turn number.
2. **Given** verbose logging is enabled, **When** the game transitions between phases, **Then** a phase label appears in the log before any actions taken in that phase.
3. **Given** verbose logging is enabled and the game ends, **Then** the log includes a final entry stating the winner and the reason the game ended.

---

### User Story 3 - Review Life Total and Zone Changes (Priority: P3)

As a developer or AI trainer reviewing a completed game, I want to see life total changes and significant zone transitions (e.g., a creature dying and going to the graveyard) captured in the log so that I can understand the game's decisive moments.

**Why this priority**: Knowing a player's life total shifted or a key permanent was destroyed provides crucial context for evaluating AI decision quality; however, the core move log (P1) delivers value on its own first.

**Independent Test**: Can be fully tested by running a game with combat damage and verifying the log contains entries for life total changes and permanents that left the battlefield.

**Acceptance Scenarios**:

1. **Given** verbose logging is enabled, **When** a player loses life, **Then** the log records the amount of life lost, the source, and the player's new life total.
2. **Given** verbose logging is enabled, **When** a permanent moves from the battlefield to the graveyard, **Then** the log records the card name, controller, and destination zone.
3. **Given** verbose logging is enabled, **When** a card is drawn, **Then** the log records which player drew (but not the card's identity, since draws are private information).

---

### Edge Cases

- What happens when both players act simultaneously (e.g., both assign blockers)? Each player's action is logged separately in declaration order.
- How does the log handle triggered abilities that fire automatically without player input? Triggered abilities are logged as engine events attributed to the permanent that triggered them.
- What happens if the game ends mid-combat? The log should capture the game-ending state-based action before the final summary entry.
- How are priority passes handled? Priority passes by a player with no action are not logged individually — only substantive actions are recorded to keep the log readable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a mode that, when enabled, outputs a human-readable narrative log of all substantive player actions as they occur during a game.
- **FR-002**: Each log entry MUST identify the acting player, the action type (e.g., cast, attack, activate, block), and the card or object involved.
- **FR-003**: The log MUST include turn number and phase/step labels as section headers that appear before the actions within that phase.
- **FR-004**: The log MUST capture life total changes, including the amount changed, the source of the change, and the player's resulting life total.
- **FR-005**: The log MUST record permanent zone transitions (entering or leaving the battlefield, going to graveyard, being exiled) with card name, controller, and destination zone.
- **FR-006**: The log MUST record which player drew a card without revealing the card's identity.
- **FR-007**: The system MUST allow verbose logging to be toggled on or off without restarting or modifying game logic.
- **FR-008**: When verbose logging is disabled, the system MUST produce no play-by-play output, ensuring there is no performance overhead from log formatting.
- **FR-009**: The log MUST end with a closing entry naming the winning player and the reason for the game's conclusion (e.g., life total reached zero, decked out, concession).
- **FR-010**: Triggered abilities that resolve automatically MUST be logged as engine events attributed to the source permanent, not to the player.

### Key Entities

- **Game Action**: A discrete, substantive event in the game — a player casting a spell, declaring attackers, activating an ability, or the engine applying a state-based action. Has an actor (player or system), an action type, a subject (card/permanent), and optional targets.
- **Log Entry**: A formatted, human-readable record of a single game action or phase transition, including the turn number, phase, actor, and descriptive text.
- **Phase Marker**: A structural entry in the log that signals the start of a new turn or game phase, providing context for the actions that follow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every substantive player action (cast, attack, block, activate) is captured in the log — a reviewer can reconstruct the full game from the log alone without referring to game state snapshots.
- **SC-002**: The log is readable by a person unfamiliar with the engine's internals — each entry is a plain-language sentence requiring no decoding of internal identifiers.
- **SC-003**: Enabling or disabling verbose logging requires a single configuration change — no code modification is needed.
- **SC-004**: When verbose logging is disabled, game simulation throughput is unaffected — simulations run at the same speed as without the feature present.
- **SC-005**: 100% of game-ending conditions (life total zero, library empty, concession) are captured in the log's closing entry.

## Assumptions

- The game engine already tracks turn number, current phase/step, and player actions internally; this feature surfaces that information rather than introducing new tracking.
- Verbose logging is opt-in (off by default) to preserve performance for batch AI simulations.
- Card draw privacy (not revealing drawn cards in the log) is consistent with standard MTG rules; both players' draws are treated as private.
- The log is intended as text output (console or file) rather than a structured data format; a machine-readable export of game events is out of scope for this feature.
- Mana floating and mana pool state changes are not logged individually, as they are incidental to the actions that spend or produce mana (which are already logged).

# Feature Specification: Skip Empty Phases

**Feature Branch**: `029-skip-empty-phases`  
**Created**: 2026-04-21  
**Status**: Draft  
**Input**: User description: "I would like the app to skip phases for all players if there is no other option but to pass priority. The application currently auto passes the phase, however the phase still occurs making for unnecessary commentary. The phase shouldn't even be presented to the player it should present the phase to the player that can be acted upon. The transcript should still contain all of the phases, but just show it was skipped because pass priority was the only option"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Skip Phases With No Actions (Priority: P1)

When a game enters a phase where every player has no legal actions except to pass priority, the system should skip presenting that phase entirely and move directly to the next phase where actions are possible. This eliminates unnecessary waiting and commentary for phases where nothing can happen.

**Why this priority**: This is the core user-requested behavior. It directly reduces game duration and eliminates frustrating "empty" phases where players watch auto-passing occur.

**Independent Test**: Can be tested by creating a game state where both players have empty hands, no activated abilities, and no triggers — then verifying that the Upkeep/Draw/Main phases are skipped entirely without player interaction.

**Acceptance Scenarios**:

1. **Given** a game where both players have no cards in hand, no permanents with activated abilities, and no triggers on the stack, **When** the game enters the Main Phase, **Then** the Main Phase should be skipped entirely and the game should advance directly to Combat (or the next phase with possible actions).

2. **Given** a game where Player 1 has a card in hand but Player 2 does not, **When** the game enters Player 1's Main Phase, **Then** the phase should be presented to Player 1 normally because they have possible actions.

---

### User Story 2 - Transcript Records Skipped Phases (Priority: P1)

Even when phases are skipped, the game transcript must still contain a record of every phase that occurred, including those that were skipped. Each skipped phase entry should indicate that it was skipped and provide the reason (no available actions).

**Why this priority**: Complete game records are essential for debugging, analysis, and replay. Skipping phases in the presentation layer must not lose information in the persistence layer.

**Independent Test**: Can be tested by creating a game with skipped phases and then retrieving the transcript — verifying that skipped phases appear with a "skipped" status and a reason.

**Acceptance Scenarios**:

1. **Given** a game where multiple phases are skipped due to no available actions, **When** the transcript is retrieved, **Then** each skipped phase should appear as a transcript entry with status "skipped" and reason "no_actions_available".

2. **Given** a skipped phase in the transcript, **When** reviewing the transcript entry, **Then** it should contain the phase name, the turn number, and the active player at the time it was skipped.

---

### User Story 3 - Conditional Action Detection (Priority: P2)

The system must correctly identify when a player has actions available beyond passing priority. This includes cards in hand that can be played/cast, activated abilities on permanents, and special actions. Phases must not be skipped if any player has any of these options.

**Why this priority**: Correct action detection prevents accidentally skipping phases where players could have taken meaningful actions. This is a safety requirement for the core skip behavior.

**Independent Test**: Can be tested by creating game states with specific action types (land in hand, creature with activated ability, etc.) and verifying the phase is not skipped.

**Acceptance Scenarios**:

1. **Given** a player has a land card in hand and it is their Main Phase, **When** the skip logic evaluates the phase, **Then** the phase should NOT be skipped because playing a land is a legal action.

2. **Given** a player has a creature with an activated ability on the battlefield, **When** the skip logic evaluates a phase where that ability could be activated, **Then** the phase should NOT be skipped.

---

### Edge Cases

- What happens when a phase has triggered abilities waiting to be put on the stack? (The phase should NOT be skipped — triggers create actions.)
- How does the system handle phases with special actions like playing a face-down card or taking a special action? (Special actions count as non-pass actions.)
- What happens if both players have empty libraries but there are still permanents with activated abilities? (Phase should NOT be skipped — activated abilities are actions.)
- How are consecutive skipped phases represented in the transcript? (Each skipped phase gets its own transcript entry in sequence.)
- What if a player has cards in hand but cannot legally play any of them (e.g., no mana, wrong phase)? (The phase CAN be skipped — the card is not a legal action in the current context.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Before presenting a phase to any player, the system MUST evaluate whether any player has legal non-pass actions available in that phase.
- **FR-002**: If NO player has any non-pass legal actions, the system MUST skip presenting the phase to players and advance directly to the next phase.
- **FR-003**: Skipped phases MUST still be recorded in the game transcript with a "skipped" status and a reason indicating "pass priority was the only option".
- **FR-004**: If ANY player has one or more non-pass legal actions, the system MUST present the phase normally to the player(s) who can act.
- **FR-005**: The skip logic MUST evaluate all possible action types: playing lands, casting spells, activating abilities, declaring attackers/blockers, and special actions.
- **FR-006**: Triggered abilities waiting to be put on the stack MUST be treated as non-pass actions, preventing the phase from being skipped.
- **FR-007**: The transcript entry for a skipped phase MUST include the phase name, turn number, active player name, and the skip reason.
- **FR-008**: Consecutive skipped phases MUST each generate their own transcript entry rather than being collapsed into a single entry.

### Key Entities

- **PhaseSkipDecision**: The evaluation result for a phase — contains the phase name, whether it was skipped, the reason, and the turn number.
- **TranscriptEntry (SkippedPhase)**: A transcript record representing a skipped phase — extends the standard transcript entry with skip-specific fields.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Games where players have no actions in a phase experience zero UI presentation of that phase (measurable by game loop timing).
- **SC-002**: 100% of skipped phases are recorded in the transcript with complete metadata (phase name, turn, active player, skip reason).
- **SC-003**: Zero phases are incorrectly skipped when any player has a legal non-pass action (measurable by test coverage of action detection).
- **SC-004**: Game commentary verbosity is reduced by at least 50% for games with long stretches of no available actions (e.g., top-decking scenarios).

## Assumptions

- The existing legal action detection system (used for presenting options to players) can be reused or extended for skip evaluation.
- The transcript system supports adding new entry types without breaking existing consumers.
- Performance of action detection is acceptable to run before every phase presentation (assumed <50ms based on current system).
- Skipping phases does not affect game rules compliance — all state-based actions and trigger checks still occur at appropriate times.
- Human players prefer not seeing empty phases over having explicit confirmation that a phase was skipped in the UI.

# Feature Specification: Human vs AI Gameplay

**Feature Branch**: `023-human-vs-ai-play`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "I would like to implement a human player being able to play against a AI or heuristics player. I should be able to play from the UI and it should be a good experience for a human player. None of the AI observation and debugging should not change as AI should still be able to observe the human player and report on it."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Join a Human vs AI Game (Priority: P1)

A human player opens the game UI and starts a new game where they will play as one player and the AI (or heuristic AI) will automatically control the other player. The human picks their deck and the AI opponent type, then is taken to the game board where they are the active player for their side.

**Why this priority**: This is the core entry point to the entire feature — without being able to set up and join a human-controlled game, nothing else works.

**Independent Test**: Can be fully tested by creating a new game, selecting "Human" for player 1 and "AI" or "Heuristic" for player 2, observing that the game starts and the board is displayed with the human as the active controller.

**Acceptance Scenarios**:

1. **Given** the game creation UI, **When** the user selects "Human" for one seat and "AI" or "Heuristic" for the other seat, **Then** a game is created and the human is taken to the game board as the controlling player for their seat.
2. **Given** the game setup, **When** the user selects deck and opponent type, **Then** the AI opponent's deck is auto-assigned and the game begins without manual configuration of the AI side.
3. **Given** the game has started, **When** it is not the human player's turn, **Then** the AI takes its turn automatically without requiring human input.

---

### User Story 2 - Human Player Takes a Turn (Priority: P1)

On the human player's turn, they can see their hand, battlefield, mana, and graveyard clearly. They can play lands, cast spells, declare attackers, and pass priority through intuitive point-and-click interactions. The interface clearly communicates which actions are currently available.

**Why this priority**: The core gameplay loop — if the human cannot meaningfully act, the feature has no value.

**Independent Test**: Can be fully tested by playing several turns as the human player and verifying all major in-turn actions (land drop, spell cast, attack, block, pass priority) are completable through the UI.

**Acceptance Scenarios**:

1. **Given** it is the human player's main phase, **When** they click a land card in their hand, **Then** the land is played to their battlefield if a land drop is available.
2. **Given** it is the human player's main phase with sufficient mana, **When** they click a castable spell in hand, **Then** they are prompted to confirm the cast and it resolves normally.
3. **Given** it is the human player's combat phase, **When** they declare attackers by clicking creatures, **Then** those creatures are committed as attackers.
4. **Given** the human player's creatures are declared as blockers, **When** they assign blockers via the UI, **Then** the block assignment is submitted.
5. **Given** at any point, **When** the human clicks "Pass Priority" or an equivalent action, **Then** priority passes to the opponent (AI takes over as needed).
6. **Given** the human's turn ends, **When** no more actions are available, **Then** the turn passes to the AI and the human sees the AI playing its turn in real time.

---

### User Story 3 - Responding to AI Actions (Priority: P2)

When the AI plays spells or abilities, the human player receives the opportunity to respond with instants, flash creatures, or activated abilities before those spells resolve. The UI clearly signals that the human has priority and presents their available responses.

**Why this priority**: Proper priority passing at instant speed is fundamental to MTG gameplay; without it the game experience is broken for interactive decks.

**Independent Test**: Can be tested by loading a deck with counterspells or removal instants and verifying the human is prompted to act when the AI casts spells during the AI's turn.

**Acceptance Scenarios**:

1. **Given** the AI has cast a spell on its turn, **When** priority passes to the human, **Then** the UI presents an opportunity to respond with available instant-speed actions or pass.
2. **Given** the human has no instant-speed actions, **When** the AI casts a spell, **Then** the human can choose to automatically pass priority (with an option to always auto-pass).
3. **Given** the human responds with an instant, **When** the instant resolves, **Then** priority returns and the human can continue to respond before the original spell resolves.

---

### User Story 4 - AI Observer Still Functions (Priority: P2)

The existing AI observer/commentary feature continues to work during human vs AI games. The observer can watch the human player's moves, analyze the game state, and produce commentary just as it does during AI vs AI games.

**Why this priority**: The user explicitly requires that AI observation and debugging are preserved — this is a hard constraint, not an enhancement.

**Independent Test**: Can be tested by starting a human vs AI game with the observer UI open and verifying commentary is produced after the human takes actions.

**Acceptance Scenarios**:

1. **Given** an AI observer is attached to the game, **When** the human player takes any action (casts spell, attacks, blocks), **Then** the observer produces commentary on that action as normal.
2. **Given** a human vs AI game, **When** the game observer UI is loaded, **Then** the play-by-play log shows both human and AI actions interleaved correctly.
3. **Given** verbose logging is enabled on the game, **When** the human player takes actions, **Then** those actions appear in the verbose log just like AI actions.

---

### User Story 5 - Game Completion and Result (Priority: P3)

When the game ends (either player wins), the human is shown a clear win/loss screen and can return to the main menu or start a new game.

**Why this priority**: Clean game endings complete the experience but do not block the core gameplay loop.

**Independent Test**: Can be tested by playing through to a win or loss condition and verifying a clear result is displayed.

**Acceptance Scenarios**:

1. **Given** the human player's life total reaches 0, **When** the game engine detects loss condition, **Then** the UI displays a loss result and offers restart or main menu options.
2. **Given** the AI player's life total reaches 0, **When** the game engine detects win condition, **Then** the UI displays a win result and offers restart or main menu options.

---

### Edge Cases

- What happens when the human takes too long to act — does the game wait indefinitely or time out?
- How does the UI handle a situation where the human has many available responses (e.g., multiple instants in hand during the AI's turn)?
- What happens if the human closes the browser tab mid-game?
- How does the UI handle triggered abilities and stack ordering when both human and AI choices are involved?
- What happens when the game requires the human to make a choice mid-resolution (e.g., modal spells, "choose a target", ETB triggers)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow game creation with a mix of player types: one seat designated as "Human" (UI-controlled) and the other as "AI" or "Heuristic" (auto-controlled).
- **FR-002**: System MUST present the human player with a clear, interactive game board view showing their hand, battlefield, library count, graveyard, life total, and available mana.
- **FR-003**: Human player MUST be able to play a land from hand during their main phase via the UI.
- **FR-004**: Human player MUST be able to cast spells from hand by clicking them, with the system automatically computing mana costs and available mana.
- **FR-005**: Human player MUST be able to declare attackers during the attack step by selecting creatures on the battlefield.
- **FR-006**: Human player MUST be able to assign blockers during the opponent's attack step.
- **FR-007**: Human player MUST be able to activate tap abilities of permanents they control.
- **FR-008**: System MUST provide a "Pass Priority" action that the human can invoke at any point they hold priority.
- **FR-009**: System MUST visually indicate when it is the human player's priority window (their turn to act).
- **FR-010**: System MUST visually indicate which actions are currently legal for the human player (e.g., highlighting playable cards).
- **FR-011**: AI opponent MUST take its turns automatically without any required human interaction.
- **FR-012**: Human player MUST receive a priority window to respond with instant-speed actions when the AI casts spells or activates abilities.
- **FR-013**: Human player MUST be able to make mid-resolution choices (e.g., select targets, choose modes for modal spells) via the UI.
- **FR-014**: AI observer and commentary system MUST continue to function and observe both human and AI player actions without modification.
- **FR-015**: Verbose play-by-play log MUST include human player actions alongside AI actions.
- **FR-016**: System MUST display a clear win/loss result when the game ends.
- **FR-017**: Human player MUST be able to enable an "auto-pass priority" option to skip response windows when no instant-speed actions are available.

### Key Entities

- **Human Player Session**: Represents the human's connection to a specific game seat; tracks which player index is under human UI control.
- **Action Request**: A pending decision the game engine is waiting on from the human player (e.g., choose attackers, select target, choose mode).
- **Priority Window**: A time slice in which the human holds priority and the UI awaits input before the game progresses.
- **Game Result**: Win/loss/draw outcome with reason (life total, concede, deck-out) displayed at game end.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Human player can complete a full game turn (draw, play land, cast spell, attack, pass) using only the UI without any external tools or workarounds.
- **SC-002**: The AI opponent takes its turns without any human input, with no UI blocking states lasting more than 5 seconds per AI action.
- **SC-003**: All existing AI observer and game commentary features continue to work in human vs AI games with no regression — 100% of observer scenarios that pass today still pass after this feature.
- **SC-004**: Human player receives a priority window in 100% of game situations where they legally hold priority at instant speed.
- **SC-005**: Human player can complete a full game (start to win/loss result) entirely within the existing game UI with no page refreshes or manual API calls required.
- **SC-006**: Game result (win/loss) is displayed clearly to the human player at game end with no dead-end states requiring a browser reload.

## Assumptions

- The existing frontend game observer UI (features 010/011) will serve as the base for the human player board view; human gameplay UI extends it rather than replaces it.
- Only 1-vs-1 games (one human seat, one AI seat) are in scope; multi-player or 2-human games are out of scope.
- Deck selection for the human player uses the same deck/card pool already available in the existing game creation flow.
- The AI opponent deck is auto-assigned (same as current AI vs AI games) unless the game creation UI already exposes per-player deck selection.
- The human player plays as Player 1 (first seat) by default; explicit seat selection is out of scope unless trivially available.
- Auto-pass priority is opt-in; by default the human is always given a chance to respond.
- No authentication or user accounts are required — the human player is anonymous, matching existing app behavior.
- Mobile layout is out of scope for v1; the UI targets desktop/tablet browsers.
- The existing verbose logging and observer APIs require no backend changes; only the frontend and game-creation flow need updating to support a human-controlled seat.

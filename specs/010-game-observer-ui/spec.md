# Feature Specification: Game Observer Web UI

**Feature Branch**: `010-game-observer-ui`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "I would like to create a very visually appealing web ui front end to observe the currently running games that AI are playing. It doesn't need 3d effects, but I would like to see cards etc move around the board"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live Game Board View (Priority: P1)

An observer opens the web UI and sees a live, visually animated view of an ongoing AI vs AI MTG game. The board shows each player's life total, hand size, battlefield permanents, graveyard count, library count, and the stack. As game actions occur — cards being played, attacking, going to the graveyard — the UI animates the movement so the observer can follow along without reading raw data.

**Why this priority**: This is the core value proposition. Without a live visual board, the entire feature is unfulfilled. Everything else enhances this foundation.

**Independent Test**: Open the UI while an AI game is running. The board updates in real time and card movements are visibly animated (e.g., a card slides from hand to battlefield when played). Delivers full standalone value as a read-only observer.

**Acceptance Scenarios**:

1. **Given** an AI game is in progress, **When** the observer loads the UI, **Then** the current board state is displayed within 2 seconds including both players' life totals, battlefield, hand size, library size, and graveyard count.
2. **Given** the AI plays a land, **When** the zone change occurs, **Then** the card visibly animates from the hand area to the battlefield area.
3. **Given** a creature attacks and is blocked, **When** combat damage is assigned, **Then** the board visually reflects the result with creatures moving to the graveyard via animation.
4. **Given** a spell is cast, **When** it is placed on the stack, **Then** it appears in the stack zone and resolves with a visible transition.
5. **Given** the game ends, **When** a player loses, **Then** the UI displays the winner clearly without requiring a page reload.

---

### User Story 2 - Game Selection and List View (Priority: P2)

An observer can see a list of all currently running AI games and select one to watch. Each entry shows which two AI players are competing, the current turn number, and the game format.

**Why this priority**: Without game selection, the UI can only hardcode one game. Multi-game support greatly increases utility, and the list view is the natural entry point for choosing which game to watch.

**Independent Test**: Start two simultaneous AI games. Open the UI. A list shows both games with player names, turn count, and format. Clicking one opens the live board for that game.

**Acceptance Scenarios**:

1. **Given** multiple AI games are running, **When** the observer opens the UI home page, **Then** a list of all active games is displayed with player names, current turn, and format (standard/commander).
2. **Given** the game list is shown, **When** the observer clicks a game, **Then** the live board for that game loads.
3. **Given** a game ends while the list is visible, **When** the list refreshes, **Then** the completed game is no longer shown or is clearly marked as finished.
4. **Given** no games are running, **When** the observer opens the UI, **Then** a clear "No active games" message is shown.

---

### User Story 3 - Play-by-Play Action Log (Priority: P3)

Alongside the visual board, the observer can see a running log of recent game actions in plain English — e.g., "Alice cast Llanowar Elves", "Bob attacked with Grizzly Bears", "Alice's creature died to lethal damage". This supplements the animation for observers who want more detail.

**Why this priority**: Enhances comprehension but the board view alone is sufficient to observe a game. The log adds context for fast-moving sequences that may be hard to follow visually.

**Independent Test**: Watch a game from the board view. The action log on the side updates with each action in readable text, correctly describing what just happened.

**Acceptance Scenarios**:

1. **Given** a card is played, **When** the action resolves, **Then** a new plain-English entry appears in the log within 1 second.
2. **Given** the log has accumulated many entries, **When** new entries arrive, **Then** the log auto-scrolls to show the latest action.
3. **Given** the observer is watching a Commander game, **When** commander damage is dealt, **Then** the log notes the commander damage total for that player.

---

### Edge Cases

- What happens when the engine becomes unreachable mid-game? The UI should show a reconnecting indicator and retry automatically rather than showing a blank board.
- What happens when a game is deleted from the engine while being observed? The UI should display a "Game ended" message gracefully.
- What if a player controls many permanents (10+)? Cards should scale or scroll rather than overflow outside the board area.
- What if an animation is still playing when the next state arrives? Animations should complete quickly enough that the displayed state does not fall more than one action behind the real game state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST display a list of all currently active games, refreshing at least every 5 seconds.
- **FR-002**: The UI MUST provide a live board view for a selected game that updates within 2 seconds of any state change in the engine.
- **FR-003**: The board MUST display both players' life totals, hand card count, library count, graveyard count, current phase/step, and turn number.
- **FR-004**: The board MUST display all permanents on the battlefield with their names, tapped/untapped state, and controller.
- **FR-005**: The board MUST animate zone changes — hand to battlefield, battlefield to graveyard, etc. — with a visible transition of 300–600ms duration.
- **FR-006**: The UI MUST display the current stack contents when spells or abilities are on the stack.
- **FR-007**: The UI MUST display a running action log of game events in plain English, updated as actions occur.
- **FR-008**: The UI MUST support Commander-format games by showing each player's command zone and accumulated commander damage totals.
- **FR-009**: The UI MUST gracefully handle engine connection loss by showing a reconnection status indicator and retrying automatically.
- **FR-010**: The board layout MUST remain readable and usable when a player controls 10 or more permanents on the battlefield.
- **FR-011**: The UI MUST be accessible from a standard modern web browser with no installation or plugins required.
- **FR-012**: The UI MUST be strictly read-only — observers cannot submit actions or influence the game in any way.

### Key Entities

- **Game**: An active AI vs AI game — has two players, a format, a turn number, and live game state.
- **Player**: One side of the game — has a name, life total, hand count, library count, graveyard count, mana pool, and optionally a command zone.
- **Permanent**: A card on the battlefield — has a name, controller, tapped/untapped state, and optional power/toughness.
- **Stack Object**: A spell or ability currently awaiting resolution — has a name, source, and controller.
- **Action Log Entry**: A timestamped plain-English description of a single game event (zone change, damage, phase transition, etc.).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The live board reflects the actual engine game state within 2 seconds of any action being submitted.
- **SC-002**: All zone changes (hand → battlefield, battlefield → graveyard, etc.) are accompanied by a visible animation — 100% of zone changes during normal play.
- **SC-003**: The board remains readable with up to 15 permanents per player without any element overflowing or being hidden.
- **SC-004**: An observer unfamiliar with the system can identify the current leader, active phase, and most recent action within 10 seconds of opening the board view.
- **SC-005**: The UI recovers automatically from a temporary engine outage of under 30 seconds without requiring a manual page reload.

## Assumptions

- The engine's existing REST API (`GET /game`, `GET /game/{id}`) is sufficient for polling game state; no new engine endpoints are required for the MVP.
- Card artwork is not required — card names on styled card-shaped visual elements are sufficient for a visually appealing experience.
- The UI is served locally alongside the engine; no authentication, user accounts, or public hosting is in scope.
- Polling the engine on a regular interval is acceptable for real-time updates; WebSocket push is a future enhancement.
- The UI targets modern desktop browsers; mobile responsiveness is not in scope for this feature.

## Out of Scope

- Submitting actions or controlling the game in any way
- Card artwork or image integration
- Mobile browser support
- User accounts or persistent preferences
- Historical game replay (live games only)
- Chat or social spectator features
- WebSocket / server-push real-time updates (polling is sufficient for MVP)

# Feature Specification: Commander Format Support

**Feature Branch**: `009-commander-format`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "implement commander format into the engine and ai client"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Start a Commander Game (Priority: P1)

A user creates a two-player Commander game by supplying two 100-card singleton decks and designating one legendary creature per player as their commander. The engine enforces Commander-specific rules: 40 starting life totals, the command zone, and commander tax on re-cast.

**Why this priority**: Without a functioning Commander game loop, none of the other Commander stories are possible. This is the foundational story.

**Independent Test**: POST a game creation request with two valid 100-card Commander decks and two commander designations. Confirm the game starts with each player at 40 life and that each player's commander appears in the command zone rather than the library.

**Acceptance Scenarios**:

1. **Given** two 100-card singleton decks each with a designated commander, **When** a Commander game is created, **Then** each player starts at 40 life and their commander is in the command zone.
2. **Given** a commander has been cast once from the command zone, **When** it returns to the command zone and is cast again, **Then** its mana cost is increased by 2 for each previous command-zone cast (commander tax).
3. **Given** a commander would move to the graveyard or exile, **When** that zone change occurs, **Then** its controller may instead return it to the command zone.
4. **Given** a deck contains two copies of the same non-basic-land card, **When** the game is created, **Then** the engine rejects the deck with a clear singleton-violation error identifying the offending card.
5. **Given** a deck has fewer or more than 100 cards, **When** the game is created, **Then** the engine rejects the deck with a clear size-violation error.
6. **Given** a non-legendary card is designated as the commander, **When** the game is created, **Then** the engine rejects the request with a descriptive error.

---

### User Story 2 — Commander Damage Tracking (Priority: P2)

The engine tracks how much combat damage each commander has dealt to each opponent across the entire game. A player who has taken 21 or more combat damage from a single commander loses the game, regardless of their current life total.

**Why this priority**: Commander damage is one of the defining win conditions of the format and directly affects how games conclude.

**Independent Test**: Submit combat damage actions until a player accumulates 21 combat damage from one commander. Confirm that player is marked as having lost via state-based action.

**Acceptance Scenarios**:

1. **Given** a commander deals combat damage to an opponent, **When** the damage is applied, **Then** the engine records that commander's cumulative combat damage to that opponent.
2. **Given** a player has accumulated 21 or more combat damage from one opponent's commander, **When** state-based actions are checked, **Then** that player loses the game.
3. **Given** two different commanders each deal 10 combat damage to the same opponent, **When** SBAs are checked, **Then** the opponent does NOT lose (each commander's damage is tracked separately).
4. **Given** a commander returns to the command zone and is re-cast, **When** it later deals combat damage, **Then** cumulative damage continues to accumulate from before — the counter is not reset.
5. **Given** the game state is queried, **When** a client requests it, **Then** the response includes each player's commander damage received per attacking commander.

---

### User Story 3 — AI Client Commander Mode (Priority: P3)

The AI CLI client supports launching Commander games with custom deck lists and commander designations via command-line flags. The AI game loop correctly handles command-zone casting and presents commander-specific actions in the decision prompt.

**Why this priority**: Extends the existing AI client to support the new format without requiring separate tooling or manual API calls.

**Independent Test**: Run the AI client with Commander-mode flags and two decks. Confirm the startup banner shows Commander mode, life totals reflect 40 starting life, and the game concludes with a winner.

**Acceptance Scenarios**:

1. **Given** `--format commander` and two `--commander NAME` flags, **When** the AI client is invoked, **Then** a Commander game is created and the game loop runs to completion.
2. **Given** a commander is in the command zone with legal actions available, **When** the AI decides, **Then** the decision prompt includes casting the commander as an explicitly labelled option showing the current mana cost with tax.
3. **Given** a commander would be sent to the graveyard or exile, **When** the AI's turn arrives, **Then** the prompt presents the option to return it to the command zone.
4. **Given** verbose mode is enabled, **When** a turn is logged, **Then** the output includes each player's commander name, its current zone, and accumulated commander damage totals.
5. **Given** no `--deck` flags are provided with `--format commander`, **When** the client starts, **Then** a built-in legal 100-card singleton Commander deck is used as the default.

---

### Edge Cases

- What happens if a player's life reaches 0 and they have also received 21 commander damage simultaneously — life-zero loss applies as a state-based action; both conditions trigger but the result is the same.
- What happens if a player has no legal actions and their commander is in the command zone — casting the commander from the command zone is always a legal action if the player can pay the full mana cost including tax.
- What happens if a commander is exiled by an opponent's effect — the controlling player still has the option to redirect it to the command zone before the exile becomes permanent.
- What happens when color identity is violated (e.g., a blue card in a mono-red commander deck) — the engine rejects the deck at creation time with a specific color-identity error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The engine MUST support a Commander game mode with two players, each starting at 40 life.
- **FR-002**: The engine MUST enforce 100-card singleton deck composition — at most one copy of each card except basic lands — and reject non-compliant decks with a descriptive error identifying the violation.
- **FR-003**: Each player MUST designate exactly one legendary creature (or eligible planeswalker with commander designation) at game creation.
- **FR-004**: The engine MUST place each player's commander in the command zone at game start rather than shuffling it into the library.
- **FR-005**: The engine MUST allow a player to cast their commander from the command zone, applying commander tax (2 additional generic mana per previous command-zone cast for that commander).
- **FR-006**: Whenever a commander would move to the graveyard or exile, the engine MUST give the controlling player the option to return it to the command zone instead.
- **FR-007**: The engine MUST track cumulative combat damage dealt by each commander to each opponent, persisted for the full game and never reset by zone changes.
- **FR-008**: The engine MUST apply a state-based loss to any player who has received 21 or more cumulative combat damage from a single commander.
- **FR-009**: The engine MUST enforce color identity: every non-land card in a player's deck must only contain mana symbols that appear in their commander's color identity.
- **FR-010**: The game state response MUST expose each player's command zone contents, each commander's cast count, and per-commander cumulative damage dealt to each opponent.
- **FR-011**: The AI client MUST accept a `--format commander` flag to activate Commander mode.
- **FR-012**: The AI client MUST accept a `--commander NAME` flag (one per player) to designate each player's commander by card name.
- **FR-013**: The AI client MUST include command-zone casting and return-to-command-zone as explicit, labelled choices in the AI decision prompt.
- **FR-014**: The AI client MUST use a built-in legal 100-card singleton Commander deck as the default when no deck flags are provided in Commander mode.

### Key Entities

- **Commander**: A designated legendary creature or eligible planeswalker owned by one player; tracks cast count from the command zone and cumulative combat damage dealt to each opponent.
- **Command Zone**: A per-player zone that holds the player's commander when it is not on the battlefield or in another zone.
- **Commander Tax**: The additional mana cost applied each time a commander is cast from the command zone; equals 2 × the number of times it has previously been cast from the command zone.
- **Commander Damage Record**: A mapping of attacking commander to defending player to total combat damage, maintained for the entire game and unaffected by zone changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A two-player Commander game can be created, played, and concluded end-to-end with a winner declared via any legal win condition (life loss, commander damage, library empty).
- **SC-002**: Deck validation correctly rejects 100% of tested decks that violate singleton rules, the 100-card requirement, non-legendary commander designation, or color identity.
- **SC-003**: Commander damage win condition triggers correctly in 100% of tested scenarios where a player accumulates 21 or more combat damage from one commander.
- **SC-004**: Commander zone transitions (cast from command zone, return to command zone) work correctly across 100% of tested scenarios including multiple re-casts with increasing tax.
- **SC-005**: The AI client completes a full Commander game without manual intervention when both AI endpoints are reachable.
- **SC-006**: All pre-existing standard game mode tests continue to pass with no regressions introduced by Commander changes.

## Assumptions

- Two-player Commander (Duel Commander) only; four-player multiplayer is out of scope for this feature.
- Partner commanders (two-commander pairs) are out of scope.
- The command zone holds exactly one commander per player.
- Color identity enforcement is included as part of deck validation at game creation.
- Emblems, the monarch mechanic, and dungeon mechanics are out of scope.
- Commander mode is activated explicitly via `--format commander` in the AI client; standard mode remains the default.
- The built-in default Commander deck will be a simple mono-green stompy list using only cards already supported by the engine's card data.

# Feature Specification: Deck Randomizer from MTGGoldfish

**Feature Branch**: `033-deck-randomizer`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "I would like to implement a deck randomizer that will randomly choose a deck given the format of the players. This should be randomized per game if no decks are input when the initial game is created. If the number of games in the series is greater than 1, then there should be a checkbox in the start game modal that lets the user check to randomize the decks for each series game or not. The decks should be created from https://www.mtggoldfish.com/metagame/standard#paper for standard gameplay, and https://www.mtggoldfish.com/metagame/commander#paper for commander gameplay. The decks should be saved to mongodb as to cache the information. I would also like to have a deck dropdown list when creating a game to pick previously created decks from this method."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Random Deck on Game Creation (Priority: P1)

As a user creating a game without providing decks, I want the system to randomly select a competitive deck from MTGGoldfish for each player, so that I can quickly start playing with real-world decks.

**Why this priority**: This is the core value proposition — users can jump into games without manually building or importing decks.

**Independent Test**: Can be tested by creating a game with empty deck fields and verifying that real MTG cards are dealt.

**Acceptance Scenarios**:

1. **Given** the user creates a Standard game with no deck input, **When** the game starts, **Then** each player gets a random deck from the MTGGoldfish Standard metagame.
2. **Given** the user creates a Commander game with no deck input, **When** the game starts, **Then** each player gets a random Commander deck from the MTGGoldfish Commander metagame.
3. **Given** the user provides a deck for player 1 but not player 2, **When** the game starts, **Then** player 1 uses the provided deck and player 2 gets a random deck.
4. **Given** the user provides decks for both players, **When** the game starts, **Then** no randomization occurs and the provided decks are used.

---

### User Story 2 — Per-Series Deck Randomization (Priority: P1)

As a user creating a series of games, I want an option to randomize decks for each game in the series, so that the same players can experience different matchups across the series.

**Why this priority**: Series games with the same decks every time would be repetitive. Per-game randomization makes series more interesting.

**Independent Test**: Can be tested by creating a 3-game series with the "Randomize decks per game" checkbox enabled and verifying different decks each game.

**Acceptance Scenarios**:

1. **Given** the user creates a 3-game series with "Randomize decks per game" checked and no decks provided, **When** each game starts, **Then** each player gets a new random deck (potentially different from previous games).
2. **Given** the user creates a 3-game series with "Randomize decks per game" unchecked and no decks provided, **When** the first game starts, **Then** both players get random decks, and those same decks are reused for all 3 games.
3. **Given** the user creates a series with "Randomize decks per game" checked but provides a deck for player 1, **When** each game starts, **Then** player 1's deck is fixed and player 2 gets a new random deck each game.

---

### User Story 3 — Deck Dropdown Selection (Priority: P2)

As a user creating a game, I want to pick from previously fetched MTGGoldfish decks via a dropdown, so that I can choose a specific archetype instead of random.

**Why this priority**: Users may want to play specific matchups (e.g., Aggro vs Control) rather than purely random ones.

**Independent Test**: Can be tested by opening the create-game modal and verifying a dropdown shows cached deck names.

**Acceptance Scenarios**:

1. **Given** the system has cached decks from MTGGoldfish, **When** the user opens the create-game modal, **Then** they see a dropdown for each player listing cached deck names by format.
2. **Given** the user selects a deck from the dropdown for player 1, **When** the game starts, **Then** player 1 uses that exact deck.
3. **Given** no decks have been cached yet, **When** the user opens the dropdown, **Then** they see a "Fetch decks" option or an empty list with instructions.

---

### User Story 4 — MongoDB Deck Caching (Priority: P2)

As the system, I want to cache fetched MTGGoldfish decks in MongoDB so that subsequent requests are fast and don't hit MTGGoldfish repeatedly.

**Why this priority**: Scraping MTGGoldfish is slow and we should respect their servers. Caching makes deck selection instant after the first fetch.

**Independent Test**: Can be tested by fetching decks once, then verifying subsequent requests don't make HTTP calls to MTGGoldfish.

**Acceptance Scenarios**:

1. **Given** the system fetches Standard decks for the first time, **When** the fetch completes, **Then** the decks are stored in MongoDB with format, name, card list, and fetch timestamp.
2. **Given** decks are already cached in MongoDB, **When** the user requests random Standard decks, **Then** the system returns cached decks without making external HTTP requests.
3. **Given** cached decks are older than 7 days, **When** a new fetch is triggered, **Then** the system refreshes the cache from MTGGoldfish.

---

### Edge Cases

- What if MTGGoldfish is down or blocks requests? Fall back to the built-in default decks and log a warning.
- What if a scraped deck has cards that fail Scryfall resolution? Skip that deck and try another.
- What if the user selects "Random" from the dropdown? Pick a random cached deck.
- What if there are no cached decks for the selected format? Trigger an automatic fetch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST fetch deck lists from MTGGoldfish metagame pages (Standard and Commander).
- **FR-002**: Fetched decks MUST be cached in MongoDB with format, deck name, card list, commander (if applicable), and fetch timestamp.
- **FR-003**: If a user creates a game without providing decks, the system MUST randomly assign a cached deck per player based on the selected format.
- **FR-004**: If series count > 1, the game creation form MUST show a "Randomize decks per game" checkbox (default: unchecked).
- **FR-005**: When "Randomize decks per game" is checked and no decks are provided, each game in the series MUST get new random decks.
- **FR-006**: When "Randomize decks per game" is unchecked and no decks are provided, the same randomly selected decks MUST be reused for all games in the series.
- **FR-007**: The game creation forms MUST show a dropdown for each player to select from cached decks.
- **FR-008**: The dropdown MUST be filterable by format and MUST show deck names.
- **FR-009**: The system MUST provide an endpoint to trigger a manual deck refresh from MTGGoldfish.
- **FR-010**: The system MUST provide an endpoint to list all cached decks by format.

### Key Entities

- **MetagameDeck**: A cached deck from MTGGoldfish with name, format, card list, commander.
- **DeckCache**: MongoDB collection storing all fetched decks.
- **DeckRandomizer**: Service that fetches, caches, and selects random decks.

## Success Criteria *(mandatory)*

- **SC-001**: A game can be created with no deck input and both players receive valid 60-card Standard decks or 99+1 Commander decks.
- **SC-002**: A 3-game series with "Randomize decks per game" produces 3 different matchups.
- **SC-003**: Decks are fetched from MTGGoldfish and cached in MongoDB within 30 seconds.
- **SC-004**: Subsequent random deck selections return cached decks in under 100ms.
- **SC-005**: The deck dropdown shows at least 5 cached decks per format.
- **SC-006**: No regressions in manual deck import or custom deck creation.

## Assumptions

- MTGGoldfish HTML structure is stable enough to scrape.
- MongoDB is available (it's already used for other features).
- Cards from MTGGoldfish decks can be resolved via Scryfall.
- We will fetch ~10-20 top decks per format (not the entire metagame).

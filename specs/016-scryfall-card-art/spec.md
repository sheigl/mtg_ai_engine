# Feature Specification: Scryfall Card Art Integration

**Feature Branch**: `016-scryfall-card-art`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User description: "I would like to use card art from scryfall in the UI"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Display Card Art in Game UI (Priority: P1)

Users can view high-quality card art from Scryfall while playing games in the UI, enhancing the visual experience and making it easier to identify cards.

**Why this priority**: This is the core feature request - users want to see card art in the UI to improve gameplay experience and card recognition.

**Independent Test**: Can be fully tested by launching the UI and verifying that card images are displayed correctly during gameplay.

**Acceptance Scenarios**:

1. **Given** a game is in progress, **When** a player's hand is displayed, **Then** each card shows its art from Scryfall
2. **Given** a card is played onto the battlefield, **When** the card appears in the zone, **Then** the card's full art image is displayed
3. **Given** a player views their library, **When** the library is displayed, **Then** card faces show Scryfall art (or back face for face-down cards)
4. **Given** a player searches for a card, **When** search results are shown, **Then** each result displays the card's art

---

### User Story 2 - Fallback to Default Art (Priority: P2)

When Scryfall art is unavailable, the system gracefully falls back to default card representations without breaking the UI.

**Why this priority**: Ensures the UI remains functional even if Scryfall is unavailable or specific card art cannot be retrieved.

**Independent Test**: Can be tested by simulating API failures or missing card data and verifying fallback behavior.

**Acceptance Scenarios**:

1. **Given** Scryfall API is unavailable, **When** a card is displayed, **Then** the system shows a placeholder with card name and type
2. **Given** a card doesn't exist in Scryfall, **When** the card is rendered, **Then** the system displays a generic card back
3. **Given** network connectivity is lost, **When** attempting to load card art, **Then** previously cached art remains visible

---

### User Story 3 - Card Image Hover Zoom (Priority: P3)

When a player hovers their mouse over a card in any game zone, a large, clear version of the card image appears so they can read card text and inspect art details without leaving the current view.

**Why this priority**: Small card thumbnails make text unreadable at a glance; a hover zoom gives quick access to full card detail without navigating away.

**Independent Test**: Hover over any card during a live game and verify a large card image appears near the cursor within 100ms, is fully readable, and disappears when the cursor leaves the card.

**Acceptance Scenarios**:

1. **Given** a card is displayed in any zone (hand, battlefield, graveyard, exile), **When** the user hovers over it, **Then** a zoomed card image appears at readable size (≥300px wide) within 100ms
2. **Given** the zoom panel is visible, **When** the cursor leaves the card, **Then** the zoom panel disappears without requiring any additional interaction
3. **Given** the card is near the edge of the viewport, **When** the zoom panel would overflow the screen, **Then** the panel repositions so it remains fully within the viewport
4. **Given** the card has no Scryfall art, **When** the user hovers, **Then** the zoom panel shows the card's name and type text instead of a broken image

---

### User Story 4 - Mobile & Responsive UI (Priority: P4)

The full game UI — including card art, game zones, and controls — is usable on a phone or tablet. Card art and layout adapt to small screens so a player can follow and interact with a game from a mobile browser.

**Why this priority**: Players want to spectate or play games on their phone without needing a desktop browser. The existing UI targets desktop; this story makes it genuinely usable at mobile viewport widths.

**Independent Test**: Open the game UI on a phone browser (or Chrome DevTools mobile emulation at 390px width). Create a game and verify all zones are visible, card art is legible, and no content is clipped or requires horizontal scrolling.

**Acceptance Scenarios**:

1. **Given** the UI is opened on a phone (≤480px viewport), **When** the page loads, **Then** all game zones (hand, battlefield, graveyard) are visible without horizontal scrolling
2. **Given** the UI is opened on a phone, **When** cards are displayed, **Then** card art is clearly visible and card name/stats remain legible
3. **Given** the UI is opened on a phone, **When** a card is tapped (rotated), **Then** the tapped state is visually clear and does not overlap adjacent cards in an unreadable way
4. **Given** the UI is viewed on a tablet (≤1024px viewport), **When** the game board is displayed, **Then** the layout scales proportionally without breaking zone boundaries
5. **Given** the UI is viewed on a desktop browser, **When** the window is resized to a narrow width, **Then** the layout degrades gracefully rather than breaking

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- What happens when Scryfall API rate limits are reached?
- How does the system handle cards not in Scryfall's database?
- What happens when a card has multiple art versions (e.g., different releases)?
- How does the system handle copyright restrictions on displaying card art?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST fetch card art images from Scryfall's API based on card name and set
- **FR-002**: System MUST cache retrieved card art to minimize API calls and improve performance
- **FR-003**: System MUST display card art in all game zones (hand, battlefield, library, graveyard, exile)
- **FR-004**: System MUST implement fallback mechanisms when Scryfall art is unavailable
- **FR-005**: System MUST handle API rate limits gracefully without breaking gameplay
- **FR-006**: System MUST respect Scryfall's terms of service for image usage
- **FR-007**: System MUST be fully usable on mobile phones (viewport ≤480px) without horizontal scrolling or clipped content
- **FR-009**: System MUST scale the game board layout for tablet viewports (≤1024px) so all zones remain visible
- **FR-010**: Card art MUST remain legible (card name and stats visible) at mobile card sizes
- **FR-008**: System MUST handle face-down cards appropriately (showing only the card back)
- **FR-011**: System MUST display a zoomed card image on hover in all game zones
- **FR-012**: The hover zoom panel MUST reposition automatically to stay within the viewport when near screen edges

### Key Entities *(include if feature involves data)*

- **CardArt**: Represents card image data with attributes like image URL, card name, set code, and cache status
- **CardDisplay**: Represents how cards are rendered in the UI with different states (face-up, face-down, tapped, etc.)
- **ArtCache**: Manages cached card images to reduce API calls and improve performance
- **[Entity 2]**: [What it represents, relationships to other entities]

## Dependencies & Assumptions

- **DEP-001**: Cards must have been loaded via the Scryfall lookup path so that `scryfall_id` is populated; tokens and engine-generated cards without a Scryfall lookup will not display art.
- **DEP-002**: The user's browser must have internet access to reach the Scryfall CDN (`cards.scryfall.io`) for initial image loads; subsequent views use the browser cache.
- **DEP-003**: Scryfall's CDN URL scheme (`/small|normal/{face}/{id[0]}/{id[1]}/{uuid}.jpg`) remains stable — Scryfall documents this as a public, stable interface.
- **DEP-004**: The existing game API already returns `scryfall_id` on every `Card` object; no backend schema migration is required.
- **ASM-001**: Non-commercial, personal use of Scryfall card images is permitted under their image usage policy provided attribution is displayed.
- **ASM-002**: Browser-level HTTP caching is sufficient for this use case; no server-side image proxy or service worker is required.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Users can view card art for 95% of displayed cards during gameplay
- **SC-002**: Card art loads within 2 seconds for 90% of cards in a typical game session
- **SC-003**: The UI remains functional and responsive even when Scryfall API is unavailable
- **SC-004**: Users report improved card recognition and gameplay experience in user feedback
- **SC-005**: Average number of Scryfall API calls per game session is less than 50 (through caching)
- **SC-006**: The system handles API rate limits without disrupting gameplay flow
- **SC-007**: The game UI is fully usable on a phone browser at 390px viewport width with no horizontal scroll
- **SC-008**: Card art and stats (name, P/T, mana cost) are legible at mobile card sizes without zooming
- **SC-009**: Hover zoom panel appears within 100ms of cursor entering a card and shows a ≥300px wide image

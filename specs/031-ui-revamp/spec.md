# Feature Specification: UI Revamp — Top-Notch Design

**Feature Branch**: `031-ui-revamp`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "The UI needs a revamp, it's ugly and not very appealing. Please make the design top notch, keeping the light and dark modes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Polished Landing / Game List (Priority: P1)

As a user visiting the app, I want to see a professional, visually appealing game list with clear hierarchy, so that the app feels modern and trustworthy.

**Why this priority**: The game list is the first screen users see. An unpolished first impression undermines the entire experience.

**Independent Test**: Can be tested by loading the home page and verifying visual polish, proper spacing, readable typography, and working navigation.

**Acceptance Scenarios**:

1. **Given** the user visits the home page, **When** the page loads, **Then** they see a branded header, well-spaced game cards with clear status indicators, and a prominent CTA.
2. **Given** the user is on the home page, **When** they view active vs completed games, **Then** visual distinction (color, opacity, badges) makes status immediately obvious.
3. **Given** the user is on mobile, **When** they view the game list, **Then** the layout adapts gracefully with proper touch targets.

---

### User Story 2 — Immersive Game Board (Priority: P1)

As a user watching or playing a game, I want the board to feel like a polished digital tabletop with clear visual hierarchy, so that I can easily read game state at a glance.

**Why this priority**: The game board is where users spend most of their time. Poor visual design makes it hard to parse board state.

**Independent Test**: Can be tested by opening any game and verifying that player info, battlefield, stack, and phase tracker are all visually distinct and readable.

**Acceptance Scenarios**:

1. **Given** a game is in progress, **When** the user views the board, **Then** player life totals are large and color-coded, active player is clearly highlighted, and cards are large enough to read.
2. **Given** the stack has items, **When** the user looks at the center bar, **Then** stack items are visually distinct from phase info.
3. **Given** the user is in a human game, **When** they view their hand, **Then** cards are large, interactive, and clearly indicate playable actions.

---

### User Story 3 — Beautiful Forms and Modals (Priority: P2)

As a user creating a game, I want forms and modals to feel modern and polished with consistent styling, so that configuration is pleasant rather than tedious.

**Why this priority**: Forms are used frequently. Good design reduces friction and errors.

**Independent Test**: Can be tested by opening the create-game modal and verifying consistent spacing, focus states, error styling, and smooth open/close animations.

**Acceptance Scenarios**:

1. **Given** the user opens the create-game modal, **When** it appears, **Then** it has a smooth animation, backdrop blur, and clear section hierarchy.
2. **Given** the user submits an invalid form, **When** validation fails, **Then** errors are clearly highlighted with consistent styling.
3. **Given** the user is in light mode, **When** they open any modal, **Then** it looks equally polished as in dark mode.

---

### User Story 4 — Cohesive Design System (Priority: P2)

As a developer or user, I want the entire app to use a consistent design language (colors, spacing, typography, components), so that nothing feels out of place.

**Why this priority**: A design system ensures consistency, makes future changes easier, and gives the app a professional feel.

**Independent Test**: Can be tested by auditing any two pages/components for consistent use of colors, spacing, typography, and component styles.

**Acceptance Scenarios**:

1. **Given** any two pages in the app, **When** compared side by side, **Then** they use the same spacing scale, color palette, and typography.
2. **Given** a button appears in any context, **When** hovered or focused, **Then** it has consistent interactive states.

---

### Edge Cases

- What happens when the viewport is very narrow (320px)? All layouts must remain usable.
- What happens when a player has 20+ permanents on the battlefield? Grid must handle overflow gracefully.
- What happens when the action log has 500+ entries? Scroll performance must remain smooth.
- How does the UI handle missing card images? Fallbacks must look intentional, not broken.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST have a cohesive design system with a documented color palette, spacing scale, and typography scale.
- **FR-002**: All pages MUST use the design system consistently — no inline one-off styles.
- **FR-003**: The app MUST have a persistent top navigation bar with branding, page title/breadcrumb, and theme toggle.
- **FR-004**: The Game List MUST display games as cards (not just link rows) with clear visual status indicators.
- **FR-005**: The Game Board MUST have improved visual hierarchy: larger cards, better player info bars, clearer phase/stack display.
- **FR-006**: All modals MUST have backdrop blur, smooth open/close animations, and consistent internal spacing.
- **FR-007**: All forms MUST have consistent input styling, focus rings, error states, and section grouping.
- **FR-008**: Buttons MUST have consistent sizes, colors, hover states, and icon support across the app.
- **FR-009**: Loading states MUST use skeletons or spinners, not just text.
- **FR-010**: Both light and dark themes MUST be equally polished with no visual regressions in either mode.
- **FR-011**: The UI MUST remain fully functional on viewports from 320px to 4K.

### Key Entities

- **Design System**: CSS custom properties for colors, spacing, typography, shadows, radii, transitions.
- **App Shell**: Persistent header/nav with branding and global controls.
- **Game Card**: Visual card component for game list items.
- **Player Bar**: Redesigned player info component with life, zones, and status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No inline `style={{...}}` props remain in any page component (exceptions for dynamic positioning like drag-and-drop).
- **SC-002**: All interactive elements have visible focus states for accessibility.
- **SC-003**: Light and dark themes both pass basic visual inspection with no broken colors or unreadable text.
- **SC-004**: Game list renders identically across Chrome, Firefox, and Safari.
- **SC-005**: Card text is readable at default zoom level on a 1080p display.

## Assumptions

- No new npm dependencies needed — pure CSS + React.
- The existing CSS custom property approach is the right foundation.
- MTG card images from Scryfall are the primary visual element and should be showcased.
- Users expect a modern web app aesthetic (clean, spacious, subtle shadows, rounded corners).

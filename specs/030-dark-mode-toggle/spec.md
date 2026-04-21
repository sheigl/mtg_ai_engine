# Feature Specification: Dark Mode Toggle

**Feature Branch**: `030-dark-mode-toggle`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "Toggle between light mode and dark mode in the UI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Toggle Theme Manually (Priority: P1)

As a user viewing the MTG Game Observer UI, I want to toggle between light and dark themes via a button, so that I can choose the visual mode that is most comfortable for my viewing environment.

**Why this priority**: This is the core feature request — without a manual toggle, the feature delivers no value.

**Independent Test**: Can be fully tested by clicking the theme toggle button on any page and observing that all UI elements switch between light and dark color schemes.

**Acceptance Scenarios**:

1. **Given** the user is on any page of the UI, **When** they click the theme toggle button, **Then** the entire UI switches from dark to light (or light to dark) instantly with a smooth transition.
2. **Given** the user has toggled to light mode, **When** they navigate to a different page, **Then** the light theme persists.
3. **Given** the user has toggled to a specific theme, **When** they refresh the browser, **Then** the previously selected theme is restored.

---

### User Story 2 - Respect System Preference (Priority: P2)

As a first-time visitor, I want the UI to default to my operating system's preferred color scheme, so that the app feels native to my environment without requiring manual configuration.

**Why this priority**: Good UX default that reduces friction for new users, but the manual toggle (P1) is the primary requirement.

**Independent Test**: Can be tested by clearing localStorage, changing the OS theme preference, and reloading the page to verify the UI matches the system preference.

**Acceptance Scenarios**:

1. **Given** a user visits the site for the first time (no saved preference), **When** their OS is set to dark mode, **Then** the UI renders in dark mode by default.
2. **Given** a user visits the site for the first time (no saved preference), **When** their OS is set to light mode, **Then** the UI renders in light mode by default.

---

### Edge Cases

- What happens when the user has JavaScript disabled? The UI falls back to the default dark theme (no toggle available).
- How does the system handle an invalid/corrupted theme value in localStorage? It falls back to the system preference, then dark as ultimate fallback.
- What happens during the brief moment before React hydrates? The theme is applied via a script in index.html to prevent flash of incorrect theme.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST provide a visible theme toggle button accessible from all pages.
- **FR-002**: Clicking the toggle MUST switch all styled components between light and dark color schemes.
- **FR-003**: The selected theme preference MUST be persisted to localStorage.
- **FR-004**: On initial load, the system MUST detect the user's OS color scheme preference (`prefers-color-scheme`).
- **FR-005**: The theme MUST apply instantly without requiring a page reload.
- **FR-006**: All existing CSS custom properties (`var(--*)`) MUST continue to work in both themes.
- **FR-007**: Card images and MTG color indicators MUST remain visually correct in both themes.

### Key Entities

- **ThemeContext**: React context providing `theme` ('light' | 'dark') and `toggleTheme` function.
- **ThemeToggle**: Button component that displays the current theme and triggers a toggle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Theme toggle is accessible within 1 click from any page.
- **SC-002**: Theme switch completes in under 300ms with CSS transitions.
- **SC-003**: Theme preference persists across browser sessions (localStorage).
- **SC-004**: No visual regressions in either theme — all existing UI elements render correctly.
- **SC-005**: No FOUC (flash of unstyled content) or flash of wrong theme on page load.

## Assumptions

- The frontend uses CSS custom properties (variables) which makes dual-theme support straightforward.
- localStorage is available (modern browsers).
- No new dependencies needed — implementation uses React context + CSS.
- Card art images are served from Scryfall and are independent of theme.

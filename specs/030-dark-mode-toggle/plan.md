# Implementation Plan: Dark Mode Toggle

**Branch**: `030-dark-mode-toggle` | **Date**: 2026-04-21 | **Spec**: `/specs/030-dark-mode-toggle/spec.md`
**Input**: Feature specification from `/specs/030-dark-mode-toggle/spec.md`

## Summary

Add a light/dark theme toggle to the MTG Game Observer React frontend. The implementation uses a React context to manage theme state, CSS custom properties scoped to a `data-theme` attribute, localStorage for persistence, and a small inline script in `index.html` to prevent flash-of-wrong-theme on load.

## Technical Context

**Language/Version**: TypeScript 5.x, React 18
**Primary Dependencies**: React (built-in context), no new npm packages
**Storage**: `localStorage` (browser)
**Testing**: Manual browser verification
**Target Platform**: Modern browsers (Chrome, Firefox, Safari, Edge)
**Project Type**: Web SPA (Vite + React)
**Performance Goals**: Theme switch < 300ms
**Constraints**: Must not break existing CSS variable usage; must avoid FOUC
**Scale/Scope**: Single frontend feature; ~5 files touched

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- No new backend work required.
- No new dependencies required.
- Pure frontend CSS + React context feature.

## Project Structure

### Documentation (this feature)

```text
specs/030-dark-mode-toggle/
├── spec.md              # Feature specification
├── plan.md              # This file
```

### Source Code (repository root)

```text
frontend/
├── index.html                          # Add FOUC-prevention inline script
├── src/
│   ├── main.tsx                        # Wrap app in ThemeProvider
│   ├── App.tsx                         # Add ThemeToggle to layout
│   ├── context/
│   │   └── ThemeContext.tsx            # Theme state, toggle, localStorage, system pref
│   ├── components/
│   │   └── ThemeToggle.tsx             # Toggle button UI
│   └── styles/
│       └── index.css                   # Add light-theme variable overrides
```

## Implementation Tasks

1. **Create `ThemeContext.tsx`** — React context with:
   - `theme: 'light' | 'dark'`
   - `toggleTheme: () => void`
   - Reads initial value from `localStorage` or `matchMedia('prefers-color-scheme')`
   - Persists changes to `localStorage`
   - Sets `data-theme` on `<html>` element

2. **Create `ThemeToggle.tsx`** — Button component:
   - Shows sun icon for dark mode (click to go light)
   - Shows moon icon for light mode (click to go dark)
   - Uses `ThemeContext`
   - Styled with CSS variables

3. **Update `index.css`** — Add light theme variable overrides under `[data-theme="light"]` selector. Keep current dark values as default (for backwards compat).

4. **Update `index.html`** — Add small inline `<script>` before any render-blocking resources to read saved theme / system pref and set `data-theme` on `<html>` immediately, preventing FOUC.

5. **Update `main.tsx`** — Wrap `<App />` with `<ThemeProvider>`.

6. **Update `App.tsx`** — Import and render `<ThemeToggle />` in a consistent location (e.g., top-right corner or near the header).

7. **Verify all CSS files** use `var(--*)` consistently — no hardcoded dark colors that would break light mode.

## Test Plan

- [ ] Load page with OS dark mode, no localStorage → dark theme shown
- [ ] Load page with OS light mode, no localStorage → light theme shown
- [ ] Click toggle → theme switches, icon updates
- [ ] Refresh page → previously selected theme persists
- [ ] Navigate between pages (GameList ↔ GameBoard) → theme persists
- [ ] Check card borders, battlefield, debug panel, create-game modal in both themes
- [ ] Verify no FOUC on hard refresh

## Rollback

Revert all file changes; no database or persistent state outside localStorage.

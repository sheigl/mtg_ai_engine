# Implementation Plan: UI Revamp — Top-Notch Design

**Branch**: `031-ui-revamp` | **Date**: 2026-04-21 | **Spec**: `/specs/031-ui-revamp/spec.md`
**Input**: Feature specification from `/specs/031-ui-revamp/spec.md`

## Summary

A comprehensive visual overhaul of the MTG Game Observer frontend. The revamp introduces a cohesive design system (CSS custom properties), a persistent app shell with header navigation, card-based game list, polished game board with better visual hierarchy, redesigned forms/modals with animations, and consistent component styling across both light and dark themes.

## Technical Context

**Language/Version**: TypeScript 5.x, React 18
**Primary Dependencies**: React (built-in), no new npm packages
**Storage**: N/A
**Testing**: Manual browser verification
**Target Platform**: Modern browsers (Chrome, Firefox, Safari, Edge)
**Project Type**: Web SPA (Vite + React)
**Performance Goals**: 60fps animations, <100ms interaction feedback
**Constraints**: Must support 320px–4K viewports; must keep existing game logic untouched
**Scale/Scope**: Frontend-only; ~15 files touched

## Constitution Check

- No new backend work.
- No new dependencies.
- Pure frontend CSS + React refactoring.

## Project Structure

### Documentation (this feature)

```text
specs/031-ui-revamp/
├── spec.md              # Feature specification
├── plan.md              # This file
```

### Source Code Changes

```text
frontend/
├── index.html                          # (unchanged — FOUC script already there)
├── src/
│   ├── main.tsx                        # Wrap app in Layout
│   ├── App.tsx                         # Simplify — Layout handles shell
│   ├── components/
│   │   ├── Layout.tsx                  # NEW: App shell with header + nav + footer
│   │   ├── ThemeToggle.tsx             # UPDATE: Move to header, better styling
│   │   ├── GameList.tsx                # UPDATE: Card-based redesign
│   │   ├── GameBoard.tsx               # UPDATE: Remove inline styles, use classes
│   │   ├── HumanGameBoard.tsx          # UPDATE: Remove inline styles
│   │   ├── HumanGameCreator.tsx        # UPDATE: Consistent form styling
│   │   ├── CreateGameForm.tsx          # UPDATE: Modal animation + form polish
│   │   ├── PlayerZone.tsx              # UPDATE: Redesigned player bar
│   │   ├── ConnectionStatus.tsx        # UPDATE: Better positioning
│   │   ├── ActionLog.tsx               # UPDATE: Better visual hierarchy
│   │   └── CardView.tsx                # (minimal — card art already good)
│   └── styles/
│       ├── index.css                   # UPDATE: Complete design system overhaul
│       ├── board.css                   # UPDATE: Better game board layout
│       ├── card.css                    # UPDATE: Larger cards, better shadows
│       ├── create-game.css             # UPDATE: Consistent form styling
│       └── debug.css                   # (minimal changes for theme compat)
```

## Implementation Tasks

### Phase 1: Design System (index.css)

Overhaul CSS custom properties with a proper design system:

- **Colors**: Semantic naming (surface, elevated, text, border, accent, success, warning, danger). Define full light + dark palettes.
- **Spacing**: 4px base unit scale (0.25rem, 0.5rem, 0.75rem, 1rem, 1.5rem, 2rem, 3rem).
- **Typography**: Font sizes from xs (0.75rem) to 3xl (1.875rem), font weights, line heights.
- **Shadows**: Subtle elevation system (shadow-sm, shadow-md, shadow-lg, shadow-glow).
- **Radii**: Consistent border radius scale (sm, md, lg, xl, full).
- **Transitions**: Standardized timing (150ms, 200ms, 300ms) with ease curves.

### Phase 2: App Shell (Layout.tsx)

Create a persistent layout component:

- **Header**: Fixed top bar with app branding ("MTG Engine"), breadcrumb/page context, theme toggle, connection status.
- **Main content area**: Proper padding to account for fixed header.
- **Footer**: Simplified, stays at bottom.
- Remove the fixed-position theme toggle from App.tsx; integrate into header.

### Phase 3: Component Redesigns

**GameList**:
- Hero section with title + description + CTA buttons.
- Game cards (not rows) with: gradient top border for active games, player avatars (colored circles), life totals, turn/phase badge, format chip, delete button.
- Empty state with illustration/icon and clear CTA.
- Loading skeleton or spinner.

**PlayerZone**:
- Larger life total with dynamic color.
- Better zone count layout (icons or compact badges).
- Active player glow/pulse indicator.
- Commander info styled as a compact badge.

**GameBoard / HumanGameBoard**:
- Remove all inline `style={{...}}` props.
- Use CSS classNames for layout.
- Better spacing between zones.
- Improved center bar with distinct stack vs phase areas.

**CreateGameForm / HumanGameCreator**:
- Consistent card-style form sections.
- Better input focus rings.
- Error states with red borders + text.
- Modal backdrop blur + scale-in animation.

**ConnectionStatus**:
- Move into header area (inside Layout) instead of floating top-right.
- Better styling: pill shape, subtle animation.

**ThemeToggle**:
- Move into header.
- Better button styling: icon-only with tooltip, smooth rotation animation on toggle.

### Phase 4: Build & Verify

- TypeScript compilation.
- Vite production build.
- Verify light and dark themes.
- Verify responsive behavior.
- Verify no console errors.

## Test Plan

- [ ] Home page renders with new design in dark mode
- [ ] Home page renders with new design in light mode
- [ ] Game list cards show correct status (active/complete)
- [ ] Game board renders correctly with player bars, battlefield, stack
- [ ] Create game modal opens with animation and backdrop blur
- [ ] Human game creator page has consistent styling
- [ ] Theme toggle works and persists
- [ ] Responsive on 375px, 768px, 1440px viewports
- [ ] No inline styles remain in page components
- [ ] Accessibility: focus rings visible, color contrast acceptable

## Rollback

Revert all file changes; no database or persistent state changes.

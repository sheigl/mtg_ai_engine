# Research: Game Observer Web UI

**Feature**: 010-game-observer-ui
**Date**: 2026-03-21

## Decision 1: Frontend Framework

**Decision**: React 18 + Vite 5 + TypeScript

**Rationale**: React is the most widely-known SPA framework with the largest ecosystem. Vite provides fast HMR and instant dev server. TypeScript adds type safety when mirroring the engine's Pydantic models. For a local development tool, ecosystem maturity and developer familiarity outweigh the performance advantages of alternatives.

**Alternatives considered**:
- **Svelte**: Excellent built-in animation primitives (`transition:`, `animate:`), smaller runtime, no VDOM overhead. Would be ideal for animation-heavy UIs but has a smaller ecosystem and the team has no existing Svelte code.
- **Vue 3**: Solid alternative but no compelling advantage over React for this use case.
- **Vanilla JS (no framework)**: No build step required, but managing complex UI state (game board with multiple zones, animations, polling) without a framework leads to spaghetti code quickly.

## Decision 2: Animation Library

**Decision**: Framer Motion (Motion for React)

**Rationale**: Motion's `layoutId` prop automatically handles FLIP animations when cards move between zones. A card rendered in the hand component with `layoutId={card.id}` and re-rendered in the battlefield component with the same `layoutId` will automatically animate its position change. This is exactly the zone-transition pattern needed (hand → battlefield, battlefield → graveyard, etc.). 30.7k GitHub stars, 3.6M weekly npm downloads.

**Usage pattern**:
```tsx
<motion.div layout layoutId={card.id} transition={{ duration: 0.4 }}>
  <CardView card={card} />
</motion.div>
```

**Alternatives considered**:
- **Pure CSS transitions/keyframes**: Possible but requires manual FLIP implementation and doesn't handle cross-component animations natively.
- **React Spring**: More performant for high-frequency animations but overkill for 300-600ms zone transitions. API is more verbose.
- **GSAP**: Powerful but heavyweight; designed for complex timeline animations beyond what's needed.

## Decision 3: Data Fetching / Polling

**Decision**: TanStack Query (React Query) v5

**Rationale**: Built-in polling via `refetchInterval`, automatic retry on failure, request deduplication, and DevTools for debugging game state changes. The `staleTime` and `gcTime` configuration prevents unnecessary re-renders when state hasn't changed. The `state_hash` from the engine's GameState can be used for conditional fetching.

**Configuration**:
```tsx
useQuery({
  queryKey: ['game', gameId],
  queryFn: () => fetch(`/game/${gameId}`).then(r => r.json()),
  refetchInterval: 1500,
  refetchIntervalInBackground: false,
});
```

**Alternatives considered**:
- **SWR**: Lighter (5.3KB vs 16.2KB) but lacks DevTools. For a dev tool where bundle size is irrelevant, TanStack Query's debugging capabilities are worth the extra bytes.
- **Custom useEffect + setInterval**: Works but reimplements error handling, retry logic, and stale data management that TanStack Query provides out of the box.

## Decision 4: State Diffing for Animations

**Decision**: Compare previous/current game state via `useRef`, rely on Motion's `layoutId` for animation triggers.

**Rationale**: Each card in the engine has a unique UUID (`card.id`). By assigning this as the `layoutId` on Motion components, zone transitions are handled automatically — when a card disappears from the hand component and appears in the battlefield component across renders, Motion detects the shared `layoutId` and animates the position change. No manual diffing or animation triggering needed.

**For the action log**: Poll the transcript endpoint with `since_seq` tracking (store last seen sequence number, request only newer entries) to avoid re-fetching the full history.

## Decision 5: Serving Frontend from FastAPI

**Decision**: Mount Vite's `dist/` output via FastAPI `StaticFiles` with a catch-all route for SPA routing.

**Rationale**: The engine already runs on uvicorn/FastAPI. Serving the frontend from the same process means no CORS configuration, no separate dev server in production, and a single URL for the user.

**Implementation**:
1. Vite builds to `frontend/dist/` with hashed assets in `frontend/dist/assets/`
2. FastAPI mounts `StaticFiles(directory="frontend/dist")` at `/ui`
3. API routes remain at `/game/*`, `/export/*`, `/deck/*`
4. A catch-all route at `/ui/{path:path}` serves `index.html` for client-side routing

**Dev workflow**: During development, run Vite dev server on port 5173 with a proxy to the FastAPI backend on port 8000. For production/demo, build and serve from FastAPI directly.

## Decision 6: Board Layout

**Decision**: CSS Grid for main layout, CSS Grid with `auto-fill`/`minmax` for battlefield permanents.

**Rationale**: The main board uses a 3-row grid: opponent zone (top), central area (stack + phase), player zone (bottom). Each player zone uses nested grids for its sub-zones. The battlefield uses `grid-template-columns: repeat(auto-fill, minmax(100px, 1fr))` which auto-wraps cards to new rows as the count increases, naturally handling the 15-permanent requirement (FR-010).

**Layout (2-player observer view)**:
```
┌──────────────────────────────────────────────────┐
│ Opponent: Life | Hand | Library | Graveyard      │
│ ┌──────────────────────────────────────────────┐ │
│ │ Opponent Battlefield (auto-fill grid)        │ │
│ └──────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│ Stack (if non-empty) │ Phase: Combat - Attackers │
├──────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐ │
│ │ Player Battlefield (auto-fill grid)          │ │
│ └──────────────────────────────────────────────┘ │
│ Player: Life | Hand | Library | Graveyard        │
└──────────────────────────────────────────────────┘
│ Action Log (right sidebar, ~25% width)           │
```

## Decision 7: Card Visual Design

**Decision**: Styled card elements with color-coded borders, no artwork.

**Rationale**: The spec explicitly states card artwork is out of scope. Cards are `120px × 168px` (standard 2.5:3.5 aspect ratio) with a dark background, colored border matching MTG color identity (W=gold-white, U=blue, B=dark purple, R=red, G=green, multicolor=gradient border, colorless=grey), card name, type line, and power/toughness badge. Tapped cards rotate 90 degrees via CSS transform.

**Mana symbols**: Use the [Mana icon font by Andrew Gioia](https://mana.andrewgioia.com/) — a CSS font library providing professional MTG mana symbols as icon glyphs. No image files needed.

## Decision 8: New Backend Endpoint

**Decision**: Add `GET /game` to list all active games.

**Rationale**: The GameManager already stores all games in `_games: dict[str, GameState]`. A simple list endpoint iterates this dict and returns a summary for each game (game_id, player names, format, turn, phase, is_game_over). No new models or storage needed — just a lightweight projection of existing in-memory state.

All other data (full game state, transcript, stack) is already available via existing endpoints.

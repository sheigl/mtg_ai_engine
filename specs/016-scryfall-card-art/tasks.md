# Tasks: Scryfall Card Art Integration

**Input**: Design documents from `/specs/016-scryfall-card-art/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story. All changes are frontend-only (`frontend/src/`). No backend changes required.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: No project structure changes needed — `frontend/src/utils/` directory is new but created implicitly by writing the file.

*(No tasks — all setup is handled by Phase 2 foundational task.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the Scryfall URL utility that all user stories depend on.

**⚠️ CRITICAL**: US1, US2, US3, and US4 all import from this utility. Must be complete first.

- [x] T001 Create `frontend/src/utils/scryfall.ts` with exported `scryfallImageUrl(scryfallId, face, size)` function and `CARD_BACK_URL` constant. Function signature: `scryfallImageUrl(scryfallId: string, face: 'front' | 'back' = 'front', size: 'small' | 'normal' = 'small'): string`. URL pattern: `https://cards.scryfall.io/${size}/${face}/${scryfallId[0]}/${scryfallId[1]}/${scryfallId}.jpg`. CARD_BACK_URL constant: `https://cards.scryfall.io/small/back/0/0/0aeebaf5-8c7d-4636-9e82-8c27447861f7.jpg`

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Display Card Art in Game UI (Priority: P1) 🎯 MVP

**Goal**: Cards in all game zones (hand, battlefield, graveyard, exile) display their Scryfall art image as a background fill with stat overlays (name, type, mana cost, P/T).

**Independent Test**: Launch the game UI, start a game, verify card images appear on cards in hand and on the battlefield. Tapped cards should show the rotated image.

### Implementation for User Story 1

- [x] T002 [US1] Add art image rendering to `frontend/src/components/CardView.tsx`: import `scryfallImageUrl` from `../utils/scryfall`; derive `imageUrl` from `card.scryfall_id` (null when absent); render a `<img>` element with `className="card-art"`, `src={imageUrl}`, `loading="lazy"`, positioned absolutely inside the `.card` div; only render when `imageUrl` is truthy
- [x] T003 [P] [US1] Add `.card-art` CSS to `frontend/src/styles/card.css`: `position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center top; border-radius: inherit; z-index: 0;`. Add `position: relative` to `.card` (already set). Add `z-index: 1` to `.card-name`, `.card-type`, `.card-mana-cost`, `.card-pt`, `.card-loyalty`, `.card-counters`, `.card-token-badge`, `.card-auras`. Add `.card-has-art .card-type` rule: `background: rgba(0,0,0,0.65); padding: 2px 4px;` and text-shadow on `.card-has-art .card-name`: `text-shadow: 0 1px 3px rgba(0,0,0,0.9)`
- [x] T004 [US1] Add `card-has-art` class to `.card` div in `frontend/src/components/CardView.tsx` when `imageUrl` is truthy (used by CSS to apply overlay styles)

**Checkpoint**: User Story 1 complete — cards should display Scryfall art in game zones.

---

## Phase 4: User Story 2 — Fallback to Default Art (Priority: P2)

**Goal**: When art fails to load or `scryfall_id` is absent (tokens), the card renders cleanly with name/type text. Face-down cards show the MTG card back.

**Independent Test**: Open DevTools → Network → block `cards.scryfall.io` → verify cards still render with readable name and type. Also verify tokens (no `scryfall_id`) display text layout without broken image icon.

### Implementation for User Story 2

- [x] T005 [US2] Add `const [artError, setArtError] = useState(false)` to `CardView` in `frontend/src/components/CardView.tsx`; set `onError={() => setArtError(true)}` on the `<img className="card-art">` element; conditionally suppress the img render when `artError` is true (show text layout only)
- [x] T006 [US2] Add face-down card back logic in `frontend/src/components/CardView.tsx`: import `CARD_BACK_URL`; when `permanent?.is_face_down` is true, set `imageUrl = CARD_BACK_URL` regardless of `scryfall_id`. Reset `artError` when `imageUrl` changes (use `useEffect` to call `setArtError(false)` on `imageUrl` change)

**Checkpoint**: User Story 2 complete — graceful degradation works for all failure scenarios.

---

## Phase 5: User Story 3 — Card Image Hover Zoom (Priority: P3)

**Goal**: Hovering over any card in any game zone pops up a large, readable version of the card image (300px wide, `normal` size from Scryfall CDN). The panel repositions automatically to stay within the viewport. Cards without art show a text fallback in the zoom panel.

**Independent Test**: Start a game in the UI, hover over a card on the battlefield, verify a large clear image appears within 100ms. Move the cursor to a card near the right/bottom edge and verify the zoom panel flips sides to stay on screen. Hover over a token (no art) and verify the zoom panel shows card name and type.

### Implementation for User Story 3

- [x] T012 [US3] Add hover zoom state and positioning to `frontend/src/components/CardView.tsx`: import `useRef` (already imported); add `cardRef = useRef<HTMLDivElement>(null)` and attach to the root `.card` div; add `const [zoomPos, setZoomPos] = useState<{x: number, y: number} | null>(null)`; implement `handleMouseEnter` that calls `cardRef.current.getBoundingClientRect()`, defaults zoom panel to appear at `right + 10` (right of card), clamps horizontally: if `right + 10 + 310 > window.innerWidth` then place at `left - 320`; clamps vertically: `Math.min(top, window.innerHeight - 440)`; calls `setZoomPos({x, y})`; attach `onMouseEnter={handleMouseEnter}` and `onMouseLeave={() => setZoomPos(null)}` to the `.card` div
- [x] T013 [P] [US3] Add zoom panel CSS to `frontend/src/styles/card.css`: `.card-zoom-panel { position: fixed; z-index: 1000; pointer-events: none; border-radius: 10px; overflow: hidden; box-shadow: 0 8px 40px rgba(0,0,0,0.75); animation: card-zoom-in 0.1s ease; }` and `@keyframes card-zoom-in { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }` and `.card-zoom-panel img { display: block; width: 300px; border-radius: 10px; }` and `.card-zoom-fallback { width: 300px; padding: 1rem 0.75rem; background: #1a1a2e; color: #ddd; font-size: 0.9rem; line-height: 1.5; border-radius: 10px; border: 1px solid #333; }`
- [x] T014 [US3] Render zoom panel in `frontend/src/components/CardView.tsx`: import `createPortal` from `react-dom`; when `zoomPos !== null`, derive `zoomImageUrl` using `scryfallImageUrl(card.scryfall_id, 'front', 'normal')` when `card.scryfall_id` is set (ignore `artError` for zoom — small art failure doesn't mean normal art fails); build zoom panel JSX: a `<div className="card-zoom-panel" style={{ left: zoomPos.x, top: zoomPos.y }}>` containing `<img src={zoomImageUrl} alt={card.name}/>` when `zoomImageUrl` is set, else `<div className="card-zoom-fallback"><strong>{card.name}</strong><br/><span>{card.type_line}</span></div>`; render via `createPortal(zoomPanel, document.body)` so fixed positioning escapes any parent stacking context

**Checkpoint**: User Story 3 complete — hover zoom appears on all cards, repositions near viewport edges, shows text fallback for tokens.

---

## Phase 6: User Story 4 — Mobile & Responsive UI (Priority: P4)

**Goal**: The full game board is usable on a phone (≤480px) without horizontal scrolling. The 300px ActionLog sidebar is hidden on mobile so the board has full width. Card sizes shrink to fit small screens. All zones remain visible and scrollable.

**Independent Test**: Open DevTools → toggle device emulation to iPhone (390px). Create a game. Verify: no horizontal scroll bar, all zones visible, card art and name legible, tapped cards readable.

### Implementation for User Story 4

- [x] T007 [US4] Add mobile board layout to `frontend/src/styles/board.css`: at `@media (max-width: 768px)`, override `.game-board.with-sidebar` to `grid-template-columns: 1fr` (remove sidebar column) and set `.action-log-container` to `display: none`. Change `.game-board` `overflow: hidden` to `overflow-y: auto` so the board scrolls vertically on small screens. Set `.game-board` `height: auto; min-height: 100vh` at mobile to allow content to expand beyond viewport height.
- [x] T008 [P] [US4] Add mobile card sizing to `frontend/src/styles/index.css`: at `@media (max-width: 480px)` override `--card-width: 72px` and `--card-height: 100px` so more cards fit across the battlefield without overflowing. At `@media (max-width: 768px)` use `--card-width: 88px` and `--card-height: 123px` for tablet sizing.
- [x] T009 [US4] Add mobile player info layout to `frontend/src/styles/board.css`: at `@media (max-width: 480px)`, set `.player-info` to `flex-wrap: wrap` and reduce `.player-name` font-size to `0.85rem` and `.player-life` font-size to `1.1rem` so the info bar fits on one or two lines without overflow.

**Checkpoint**: User Story 4 complete — game UI fully usable on a phone browser.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Scryfall attribution (required by ToS) and final validation.

- [x] T010 [P] Add Scryfall attribution to `frontend/src/App.tsx` or the main layout wrapper: add a footer element with text `Card images © Wizards of the Coast. Powered by Scryfall.` where "Scryfall" links to `https://scryfall.com`. Style with small muted text. Ensure footer does not interfere with mobile layout.
- [x] T011 Validate the full quickstart.md checklist: start backend (`uvicorn mtg_engine.api.main:app --reload`), start frontend dev server (`cd frontend && npm run dev`), create a game, verify art loads in hand and battlefield, verify hover zoom appears and repositions at screen edges, verify tokens show text fallback in zoom panel, verify face-down shows card back, verify mobile layout at 390px viewport width in DevTools

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **User Stories (Phase 3–6)**: All depend on T001 (Phase 2)
  - T002, T003, T004 depend on T001
  - T005, T006 depend on T002 (same file)
  - T012, T013, T014 depend on T002 (same file for CardView changes)
  - T007, T008, T009 are independent of US1/US2/US3 (different files)
- **Polish (Phase 7)**: Can begin after Phase 3 is complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 (T001)
- **US2 (P2)**: Depends on US1 completion (T002 must exist before T005/T006)
- **US3 (P3)**: Depends on US1 completion (T002 must exist before T012/T014); T013 is independent (CSS only)
- **US4 (P4)**: Independent of US1/US2/US3 — touches different files (`board.css`, `index.css`)

### Within Each User Story

- T002 → T004 sequential (both in CardView.tsx)
- T003 [P] independent (different file — card.css)
- T005 → T006 sequential (both modify CardView.tsx state logic)
- T012 → T014 sequential (both modify CardView.tsx)
- T013 [P] independent (card.css — can run parallel with T012)
- T007 → T009 sequential (both modify `board.css`)
- T008 [P] independent (touches only `index.css`)

### Parallel Opportunities

- T003 [P] ∥ T002 (different files: CardView.tsx vs card.css)
- T013 [P] ∥ T012 (different files: CardView.tsx vs card.css)
- T008 [P] ∥ T007 or T009 (different files: index.css vs board.css)
- T010 [P] ∥ any task (App.tsx is independent)

---

## Parallel Example: User Story 3 (Hover Zoom)

```bash
# These two tasks can run in parallel (different files):
Task T012: "Add hover state + positioning logic to frontend/src/components/CardView.tsx"
Task T013: "Add .card-zoom-panel CSS to frontend/src/styles/card.css"
# T014 must follow T012 (same file: CardView.tsx)
```

---

## Implementation Strategy

### Remaining Work (US3 Hover Zoom)

1. Complete T012 + T013 (parallel): CardView hover state + zoom CSS
2. Complete T014: Render zoom panel via portal
3. **VALIDATE**: Hover over cards in all zones, check edge repositioning, check token fallback
4. Update T011 validation checklist entry

### Complete Delivery Order

1. Phase 2 → Phase 3 → MVP with card art ✅
2. Phase 4 → Robust fallbacks ✅
3. Phase 5 → Hover zoom (remaining)
4. Phase 6 → Responsive polish ✅
5. Phase 7 → Attribution + final validation

---

## Notes

- Total tasks: 14 (11 complete, 3 remaining)
- US1 tasks: 3 (T002–T004) ✅
- US2 tasks: 2 (T005–T006) ✅
- US3 tasks: 3 (T012–T014) ← **REMAINING**
- US4 tasks: 3 (T007–T009) ✅
- Polish tasks: 2 (T010–T011, T011 pending re-validation)
- Parallel opportunities: T002 ∥ T003, T012 ∥ T013, T007 ∥ T008, T010 ∥ any
- No backend changes, no new npm dependencies
- Zoom panel uses `createPortal` to `document.body` to escape any parent `overflow: hidden` or stacking context
- Zoom uses `normal` size (488×680px rendered at 300px CSS width) for crisp detail; in-card art uses `small` for fast loading
- Hover zoom is desktop-only in practice (touch devices don't fire `mouseenter`)

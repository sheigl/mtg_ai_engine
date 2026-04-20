# Research: Human vs AI Gameplay

**Branch**: `023-human-vs-ai-play` | **Date**: 2026-04-18

## Decision 1: Human Input Model

**Decision**: Human player submits actions directly to existing action endpoints (`POST /game/{id}/pass`, `/play-land`, `/cast`, etc.). The backend game loop for hybrid games simply skips (polls and waits) when `priority_holder` equals the human player's name.

**Rationale**: The existing action endpoints already validate that the requesting player holds priority — they will reject any action submitted for the wrong player. The game loop can safely poll and skip its turn when priority belongs to the human, since the human will submit actions externally via the frontend. No new action submission protocol is needed.

**Alternatives considered**:
- WebSocket/SSE push channel for human input: adds significant backend complexity with no clear advantage since the existing REST endpoints already satisfy the need.
- A "pending action" queue in GameManager: unnecessary abstraction — the game state itself already encodes "whose turn it is" via `priority_holder`, which is sufficient for the loop to know to wait.

---

## Decision 2: New Endpoint vs. Extend Existing `/ai-game`

**Decision**: Add a new `POST /human-game` endpoint (in a new `human_game.py` router) that creates the game and starts a hybrid game loop thread. The existing `POST /ai-game` endpoint is left untouched.

**Rationale**: `POST /ai-game` hardcodes both players as AI/Heuristic. Adding a `player_type` flag would create branching complexity there. A separate endpoint keeps concerns isolated and matches the existing pattern (`ai_game.py` already exists as its own router).

**Alternatives considered**:
- Extend `POST /ai-game` with optional `player_types` array: possible, but bloats the existing endpoint and risks breaking existing AI vs AI flows.

---

## Decision 3: Hybrid Game Loop Architecture

**Decision**: The hybrid game loop runs in a background thread (same pattern as `ai_game.py`). It drives AI player turns normally and simply polls-and-sleeps (500ms) when `priority_player` equals the human player name, waiting for the human to submit an action via the frontend.

**Rationale**: The game loop already polls `GET /game/{id}/legal-actions` before every action. When `priority_player == human_name`, the loop just re-polls after a short sleep. When the human submits an action, the game state advances and the loop naturally resumes.

**Loop pseudocode**:
```
while not game_over:
    legal_data = GET /legal-actions
    if legal_data.priority_player == human_name:
        sleep(0.5)   # wait for human to act via frontend
        continue
    # AI decides and submits action normally
```

**Alternatives considered**:
- Blocking call with a threading.Event: cleaner but requires backend state changes; the sleep-poll approach works with zero additional state.

---

## Decision 4: Frontend Architecture

**Decision**: Extend the existing `GameBoard.tsx` observer component into a `HumanGameBoard.tsx` that adds an interactive action layer. A new `useLegalActions` hook polls `GET /game/{id}/legal-actions` on a 750ms interval when it is the human's turn. The interactive layer overlays action controls on top of the existing observer view.

**Rationale**: The observer UI already displays all the game state the human needs (hand, battlefield, life, mana, stack, phase). Building on top of it avoids duplicating game state rendering. The interactive layer is additive — it shows nothing when it is not the human's turn.

**Alternatives considered**:
- Fully separate human game board: large duplication of observer component logic.
- Inline interactive elements into existing observer: would require conditionally rendering interactive controls throughout the observer, making it complex.

---

## Decision 5: Legal Action Display in the UI

**Decision**: The frontend highlights playable actions visually (glowing border on cards in hand that can be played/cast, highlight on tappable creatures during combat) and presents an `ActionPanel` sidebar or footer with context-sensitive buttons (Pass Priority, End Turn, Confirm Attackers, etc.). Clicking a card in hand that is legally playable triggers the appropriate action.

**Rationale**: This is the standard pattern for digital MTG interfaces (Arena, Cockatrice). Highlighting legal actions is more discoverable than requiring the user to remember what to do at each game step.

**Card click flow**:
- Click land in hand → `POST /game/{id}/play-land` with `{card_id}`
- Click castable spell → open target/cost modal → `POST /game/{id}/cast`
- Click creature during attack declaration → toggle attacker
- Click "Confirm Attackers" button → `POST /game/{id}/declare-attackers`

---

## Decision 6: Mid-Resolution Choice Handling

**Decision**: Mid-resolution choices (target selection, modal spells, scry/surveil, discard) are presented as modal dialogs. The frontend detects pending choices by examining the `pending_*` fields in GameState (e.g., `pending_scry_choice`, `pending_discard_choice`) or by examining the legal actions list which will contain only choice-related actions when a choice is pending.

**Rationale**: The engine already represents pending choices as explicit GameState fields. When these are set, `_compute_legal_actions()` returns only choice-related actions, so the frontend can detect "a choice is pending" and present the right UI.

---

## Decision 7: AI Observer Preservation

**Decision**: No changes to the AI observer system. The observer (`DebugPanel`, commentary, verbose logging, AI game observer loop) all operate on `GameState` and `TranscriptRecorder`. Since human actions go through the same action endpoints and update the same `GameState`, the observer will naturally see human player actions in the transcript and play-by-play log without modification.

**Rationale**: The observer is decoupled from who submits actions — it only observes `GameState` transitions. Human and AI actions update state through the same code path.

---

## Decision 8: Game Creation UI

**Decision**: Extend the existing `GameCreator.tsx` (or game creation form in the UI) to add player type selectors per seat. Each seat gets a `<select>` with options: "AI (GPT)", "Heuristic", "Human (You)". When "Human" is selected for a seat, the form posts to `POST /human-game` instead of `POST /ai-game`. Deck selection for the human seat is identical to existing deck selection.

**Rationale**: The existing game creator already handles deck selection and game configuration. Adding player type per seat is a minimal UI change.

---

## Decision 9: Mana Payment for Human Casts

**Decision**: For initial implementation, mana is auto-tapped by the backend (same logic as `_auto_tap_mana()` in the AI game loop, which is server-side accessible). The human selects which spell to cast; the system handles mana payment automatically. Manual mana selection is deferred to a future enhancement.

**Rationale**: Auto-tapping mana already exists in the game loop. Exposing manual mana selection requires significant additional UI work (drag-and-drop mana selection, floating mana pool display) that is out of scope for v1.

---

## Decision 10: Win/Loss Display

**Decision**: The `HumanGameBoard.tsx` checks `game_state.is_game_over` on each poll. When true, an overlay modal displays the result (`winner == human_name ? "You Win!" : "You Lose"`) with buttons to return to the game list or restart with the same decks.

**Rationale**: The existing `GameState` already has `is_game_over: bool` and `winner: str`. No new backend API is needed for game result detection.

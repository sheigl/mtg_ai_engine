# Feature Specification: Observer AI Debug Panel

**Feature Branch**: `011-observer-ai-commentary`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "add observer ai to analyze each AIs current state and potential plays, when a play is made it outputs it to a debug panel in the UI and adds commentary if it were good or bad play, or what they could have done differently or better"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Real-Time Decision Commentary (Priority: P1)

A developer or researcher watching a live game in the observer UI can optionally enable a debug panel alongside the game board. When enabled, the panel shows two types of live activity: (1) the prompt sent to each playing AI and its streaming response as it decides each action, and (2) the observer AI's commentary on each non-pass action — rating the play and explaining what alternatives were available. When disabled, the panel is hidden and no additional requests are made.

**Why this priority**: This is the core value of the feature. Seeing both the raw AI reasoning (prompt + stream) and the observer's evaluation in one place is the primary debugging utility. All other stories build on this foundation.

**Independent Test**: Load any in-progress game in the observer UI. Enable the debug panel. Wait for the next player action. Verify the panel shows: the prompt sent to the acting AI, the streamed response as it arrives, and (for non-pass actions) a commentary entry with a rating and explanation. Then disable the panel and verify no further activity appears.

**Acceptance Scenarios**:

1. **Given** the debug panel is enabled and it is a player's turn to act, **When** the engine requests a decision from that player's AI, **Then** the panel shows the full prompt sent to that AI, labeled with the player's name.
2. **Given** a prompt has been sent, **When** the AI streams its response token-by-token, **Then** the panel displays the response appearing incrementally in real time (not all at once after completion).
3. **Given** the debug panel is enabled and a player takes a non-pass action, **When** the action resolves, **Then** the observer AI's commentary entry appears in the panel with a rating (e.g., "Good play" or "Suboptimal") and a brief explanation.
4. **Given** commentary is enabled and two or more legal non-pass actions were available, **When** the player chose one, **Then** the commentary mentions at least one alternative and explains the trade-off.
5. **Given** the only legal action is "pass", **When** the player passes, **Then** no observer AI commentary entry is generated, though the prompt and response for that pass are still shown.
6. **Given** the debug panel is disabled, **When** any action is taken, **Then** no prompts, responses, or commentary appear and no extra requests are made.

---

### User Story 2 — Streaming AI Prompt & Response Visibility (Priority: P2)

For every decision made by any AI in the game (playing agents and the observer AI), the debug panel shows the exact prompt that was sent and the response as it streams in. Each entry is collapsible so the observer can focus on just the turns they care about. This gives developers full visibility into why an AI made a particular choice.

**Why this priority**: Commentary tells you whether a play was good — the raw prompt and stream tell you *why the AI chose it*. Both are needed for debugging model behavior.

**Independent Test**: Observe a game with both players taking at least 3 non-pass actions each. Verify that for every decision (including observer AI analysis), the debug panel contains a collapsible block showing the prompt and the full streamed response.

**Acceptance Scenarios**:

1. **Given** the debug panel is enabled and Player 1's AI is deciding an action, **When** the prompt is sent, **Then** a labeled block appears in the panel immediately showing the full prompt text for Player 1.
2. **Given** a prompt block is visible, **When** the AI streams its response, **Then** the response text grows incrementally within the same block, character by character or token by token.
3. **Given** the observer AI is analyzing an action, **When** its prompt is sent and response streams, **Then** a block labeled "Observer AI" appears in the panel showing the observer's prompt and streaming analysis — visually distinct from the playing AI blocks.
4. **Given** many prompt/response blocks exist, **When** the observer clicks on a block header, **Then** the block collapses or expands to manage panel space.
5. **Given** the debug panel is viewing a completed game, **When** persisted prompt/response logs exist, **Then** they are shown in the panel in the same chronological interleaved order as during the live game.

---

### User Story 3 — Per-Player Attributed History (Priority: P3)

Every entry in the debug panel — whether a prompt/response block or a commentary entry — is clearly labeled with the source (player name or "Observer AI"), the turn number, and the game step. The observer can scroll the full panel to review the entire decision history of the game.

**Why this priority**: Without attribution and context, entries from two playing AIs and one observer AI become indistinguishable in long games.

**Independent Test**: Observe a 5-turn game. Verify each prompt/response block and commentary entry is labeled with the correct source, turn, and step. Verify all entries are in chronological order.

**Acceptance Scenarios**:

1. **Given** Player 1 plays a land on Turn 2 precombat main, **When** the debug panel shows the prompt/response block, **Then** it is labeled "Player 1 — Turn 2 / precombat_main".
2. **Given** an observer AI commentary entry is generated, **When** it appears in the panel, **Then** it is labeled "Observer AI — Turn 2 / precombat_main" and visually distinct from playing AI blocks.
3. **Given** multiple entries exist, **When** the observer scrolls the panel, **Then** entries appear oldest-first (top to bottom), interleaving player prompts and observer commentary in the order they occurred.
4. **Given** a game has concluded, **When** the observer views the completed game, **Then** the full history of all prompt/response and commentary entries is visible and scrollable.

---

### User Story 4 — Alternative Play Suggestions for Suboptimal Actions (Priority: P4)

When the observer AI rates an action as suboptimal, the commentary entry includes a concrete "Better play" suggestion that references the actual cards or actions available at that moment. This helps developers and researchers understand exactly what the playing AI missed.

**Why this priority**: Saying "this was bad" without explaining why has limited educational or training-data value. Suggestions are the key differentiator from a simple action log.

**Independent Test**: Cause the playing AI to make a clearly inferior play (e.g., tap all lands during upkeep before the fix, or cast a creature when passing to hold mana for a counter would be better). Verify the commentary identifies the play as suboptimal and names a specific alternative.

**Acceptance Scenarios**:

1. **Given** the active player casts a small creature when attacking with an existing creature would deal lethal damage, **When** commentary is generated, **Then** it notes the missed lethal attack as the better alternative.
2. **Given** a play is rated "Good play", **When** commentary is generated, **Then** no "Better play" suggestion is required and the section may be omitted.
3. **Given** the observer AI cannot determine a clearly better alternative, **When** commentary is generated, **Then** it outputs a neutral assessment rather than fabricating a suggestion.

---

### Edge Cases

- What happens when the observer AI service is unavailable or times out? A placeholder entry ("Analysis unavailable") appears rather than blocking the UI or crashing.
- What happens if actions occur faster than the AI can analyze them? Commentary requests are queued; entries appear in order once analysis completes without dropping any.
- What happens when a game ends before commentary for the final action is returned? The entry still appears once analysis finishes, marked with the final turn/step.
- What happens when a game has 100+ turns with hundreds of prompt/response and commentary blocks? The panel uses efficient rendering (e.g. collapsed blocks by default) so it remains responsive.
- What happens if the observer AI hallucinates a card name or action that was not in the legal action set? Commentary is shown as-is; no validation of AI-generated text is required for this debug tool.
- What happens if a playing AI's response stream is interrupted mid-token? The panel shows whatever was received up to the interruption and marks the block as incomplete.
- What if prompts contain sensitive internal state (full hand contents, deck order)? This is an internal developer tool; no redaction is required.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The observer UI MUST provide a toggle to enable or disable the debug panel. The panel is off by default.
- **FR-002**: When the debug panel is enabled, the UI MUST display it alongside the existing game board view. When disabled, the panel MUST be hidden and no prompt logging or observer AI requests MUST be made.
- **FR-003**: When the debug panel is enabled, the system MUST capture the exact prompt sent to each playing AI for every decision and display it in the panel, labeled with the player name, turn, and game step.
- **FR-004**: When the debug panel is enabled, the system MUST display each playing AI's response as it streams in, updating the panel incrementally in real time.
- **FR-005**: When the debug panel is enabled, the system MUST capture and display the observer AI's prompt and streaming response for each non-pass action, in the same panel, visually distinct from playing AI blocks.
- **FR-006**: Each block in the debug panel (prompt/response or commentary) MUST be labeled with its source (player name or "Observer AI"), turn number, and game step.
- **FR-007**: Prompt/response blocks MUST be collapsible so the observer can manage panel space in long games.
- **FR-008**: The system MUST expose an endpoint that accepts a game state snapshot, the chosen action, and the full legal action set at decision time, and returns a commentary object with: a rating (good / acceptable / suboptimal), a natural-language explanation, and an optional alternative play suggestion.
- **FR-009**: Observer AI commentary MUST only be generated for non-pass actions (cast, play land, activate ability, declare attackers, declare blockers).
- **FR-010**: When a play is rated "suboptimal", the commentary entry MUST include at least one concrete alternative action that was available at decision time.
- **FR-011**: The observer AI MUST receive the full legal action set at decision time so it can reason about alternatives, not just the chosen action.
- **FR-012**: If observer AI commentary generation fails or exceeds a timeout, the UI MUST display a non-blocking placeholder entry.
- **FR-013**: The debug panel MUST be available when viewing completed (historical) games, showing the full persisted log of prompts, responses, and commentary in chronological order.
- **FR-014**: All prompt/response logs and commentary entries MUST be persisted per game so they survive page refreshes and are retrievable for historical games.

### Key Entities

- **DebugEntry**: A single record in the debug panel log. Has a type (prompt_response or commentary), source (player name or "Observer AI"), turn, phase/step, and timestamp. Prompt/response entries include the prompt text and the full streamed response. Commentary entries additionally include a rating and optional alternative suggestion.
- **DebugLog**: Ordered collection of DebugEntry records for a single game. Persisted alongside the game record and retrievable via the export API.
- **ObserverAI**: The analysis component that receives game state + chosen action + legal actions and produces a commentary DebugEntry. Stateless per request; shares LLM infrastructure with playing agents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Prompt/response blocks begin appearing in the debug panel within 1 second of a decision request being sent to a playing AI.
- **SC-002**: Streaming responses render token-by-token with no visible batching delay — the panel updates at least 5 times per second while a response is streaming.
- **SC-003**: Observer AI commentary entries appear in the panel within 10 seconds of each non-pass action resolving.
- **SC-004**: 100% of non-pass actions in a completed game have a corresponding commentary entry in the persisted debug log.
- **SC-005**: All debug panel entries correctly attribute the source (player name or "Observer AI") and game step across a 10-game test run with zero labeling errors.
- **SC-006**: The debug panel remains visually responsive with up to 400 entries (200 prompt/response blocks + 200 commentary entries) loaded at once.
- **SC-007**: For at least 80% of actions rated "suboptimal", the entry names a specific alternative action present in the legal action set at that moment.

## Assumptions

- The debug panel is opt-in and disabled by default; no prompt logging or LLM calls beyond normal gameplay are made unless the observer explicitly enables it.
- The observer AI uses the same LLM infrastructure already in use by the playing agents (Ollama-compatible endpoint), so no new AI service is required.
- Prompt/response logging is handled by the backend (the AI client already knows what prompt it sends and what it receives); the backend streams this to the UI.
- Observer AI commentary is asynchronous — the game does not pause or wait for analysis before the next action can be taken.
- The debug panel is a read-only view; observers cannot interact with or modify game state through it.
- Pass-only actions are excluded from observer AI commentary but their prompts and responses are still shown (the AI still "thinks" about passing).
- The feature targets standard-format two-player games; commander-specific commentary is deferred.
- All AI output (prompts, responses, commentary) is shown verbatim; no redaction or moderation is required for this internal debugging tool.

## Out of Scope (v1)

- Observer AI commentary on "pass" actions (prompts/responses for passes are still shown)
- Commander-format-specific commentary
- User-adjustable commentary verbosity or AI model selection in the UI
- Ability to copy/export individual prompt or response blocks from the panel
- Side-by-side comparison of two games
- Content validation or fact-checking of AI-generated text
- Token-count or latency metrics displayed per block

# Feature Specification: Commentary Annotations, Rating Override & Card Ordering

**Feature Branch**: `024-commentary-annotation-card-order`  
**Created**: 2026-04-19  
**Status**: Draft  
**Input**: User description: "I want to create a few new features. 1. I want to be able to make comments on the observer AI commentary, if I want to counter what it thinks. This should be exportable as well when downloading the game log. I want to be able to comment on the AI thought process if the player is an AI player. 2. I want to be able to drag my cards in my hand as well as on the board to change their order (just personal preference on ordering) 3. When the AI observer rates a move as Good, Acceptable etc, I want to be able to change that if I think it's wrong and rerate the move. However this still needs to be kept track of in the game log (remember the point of this is to teach AI later on in training)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Annotate Observer & AI Commentary (Priority: P1)

A player watches the observer AI rate a move (e.g. "Suboptimal") or reads an AI player's reasoning and wants to write a short counter-argument or additional note. They click an "Add Comment" button next to the commentary block, type their annotation, and save it. The annotation is attached to that specific debug entry and visible in the debug panel. When the player downloads the game log, the annotation is included alongside the observer's original commentary for that action.

**Why this priority**: This is the core training-data capture mechanism — human corrections and counter-arguments to AI reasoning are high-value labels for future model training. It directly fulfills the stated purpose of the feature.

**Independent Test**: Can be fully tested by adding a comment to an observer commentary entry and verifying it appears in the downloaded game log.

**Acceptance Scenarios**:

1. **Given** an observer AI commentary entry is visible in the debug panel and marked complete, **When** the player clicks "Add Comment" and submits text, **Then** the annotation appears beneath that commentary entry in the panel.
2. **Given** an AI player's prompt/response entry is visible in the debug panel and marked complete, **When** the player clicks "Add Comment" and submits text, **Then** the annotation appears beneath that entry.
3. **Given** one or more annotations exist, **When** the player downloads the game log, **Then** each annotation appears inline with the commentary it belongs to, clearly labeled as a player comment.
4. **Given** a saved annotation, **When** the player edits it and saves again, **Then** the updated text replaces the previous annotation.
5. **Given** an annotation exists, **When** the player deletes it, **Then** the annotation is removed from both the panel and future log exports.
6. **Given** a commentary entry still streaming, **When** the player views it, **Then** the "Add Comment" option is not yet available.

---

### User Story 2 - Override Observer AI Rating (Priority: P2)

The observer AI rates a move as "Good", "Acceptable", or "Suboptimal". The player disagrees and wants to change the rating. They click the current rating badge on a commentary entry, select a different rating from a small picker, and confirm. The overridden rating is displayed (visually distinct from the AI's original rating) and the original AI rating is preserved alongside it. Both the original and overridden ratings are recorded in the game log for training purposes.

**Why this priority**: Rating corrections are explicit training signals — a human override is stronger ground-truth than the AI's self-assessment. Both original and corrected values must be tracked for training data integrity.

**Independent Test**: Can be fully tested by overriding a rating on a commentary entry and confirming the game log export shows both the original AI rating and the player's override.

**Acceptance Scenarios**:

1. **Given** an observer commentary entry with a rating, **When** the player selects a different rating, **Then** the new rating is displayed prominently with a visual indicator that it was overridden by the player.
2. **Given** an overridden rating, **When** the player downloads the game log, **Then** the log shows both the original AI rating and the player-provided override, labeled distinctly.
3. **Given** an overridden rating, **When** the player changes it to yet another value, **Then** the most recent player rating is used; the original AI rating is never altered.
4. **Given** an overridden rating, **When** the player removes their override, **Then** only the original AI rating is shown and no override appears in log exports.

---

### User Story 3 - Reorder Cards in Hand and on Battlefield (Priority: P3)

A player wants to rearrange the visual order of cards in their hand and on their side of the battlefield to match their personal organizational preference (e.g., group lands together, sort creatures by toughness). They drag a card and drop it to a new position. The reordering is purely cosmetic — it does not affect game rules, legal actions, or the game state on the server. The order persists for the duration of the browser session.

**Why this priority**: Quality-of-life feature with no impact on training data or game correctness. Valuable but not blocking any other feature.

**Independent Test**: Can be fully tested by dragging a card to a new position and confirming it stays there until the player moves it again or the page is refreshed.

**Acceptance Scenarios**:

1. **Given** cards in the player's hand, **When** the player drags a card to a new position in the hand, **Then** the card occupies the new position and adjacent cards shift accordingly.
2. **Given** permanents on the player's side of the battlefield, **When** the player drags a permanent to a new position, **Then** the permanent appears at the new position.
3. **Given** a reordered hand, **When** a new card is drawn, **Then** the new card appears at the end of the hand without disturbing the existing order.
4. **Given** a reordered hand or battlefield, **When** the player refreshes the page, **Then** the ordering resets to server order (persistence across refreshes is out of scope for v1).
5. **Given** a card being dragged, **When** the player drops it outside a valid drop zone, **Then** the card returns to its original position with no change.
6. **Given** a pending action submission, **When** the player attempts to drag a card, **Then** dragging is disabled and no reordering occurs.

---

### Edge Cases

- What happens when a player submits an empty annotation? The system must not save blank or whitespace-only annotations.
- What happens if a commentary entry is still streaming when the player tries to annotate? The "Add Comment" action must only be available after the entry is fully complete.
- What happens when the player attempts to drag a card during a pending action? Drag interactions must be disabled while an action is in flight.
- What if both an annotation and a rating override exist on the same entry? Both must be stored independently and both must appear in the exported log.
- What if the game log is downloaded before any annotations are added? The log must include only AI-generated content with no placeholder annotation fields.
- What if a card is removed from the hand or battlefield (played, countered, destroyed)? The remaining cards maintain their relative order; the removed card's slot closes.

## Requirements *(mandatory)*

### Functional Requirements

**Annotations**

- **FR-001**: Users MUST be able to add a free-text annotation to any completed observer AI commentary entry.
- **FR-002**: Users MUST be able to add a free-text annotation to any completed AI player prompt/response entry.
- **FR-003**: Annotations MUST be editable and deletable after creation.
- **FR-004**: Annotations MUST be persisted server-side for the duration of the game and included in all subsequent log exports.
- **FR-005**: The game log export MUST include each player annotation inline with the commentary entry it belongs to, clearly labeled (e.g., "Player Comment:").
- **FR-006**: The annotation input MUST only be available once the commentary entry is fully complete (not mid-stream).
- **FR-007**: The system MUST NOT save blank or whitespace-only annotations.

**Rating Override**

- **FR-008**: Users MUST be able to override the observer AI's rating (Good / Acceptable / Suboptimal) on any completed observer commentary entry.
- **FR-009**: The player override MUST be visually distinguishable from the original AI-assigned rating in the debug panel.
- **FR-010**: The original AI-assigned rating MUST always be preserved and never overwritten.
- **FR-011**: Both the original rating and the player override MUST appear in the game log export, labeled distinctly.
- **FR-012**: Users MUST be able to remove their rating override, reverting the display to show only the original AI rating.

**Card Reordering**

- **FR-013**: Users MUST be able to drag cards within their hand to reorder them visually.
- **FR-014**: Users MUST be able to drag permanents on their side of the battlefield to reorder them visually.
- **FR-015**: Card reordering MUST be purely cosmetic — it MUST NOT affect game state, legal actions, or any server-side data.
- **FR-016**: Drag interactions for reordering MUST be disabled while an action submission is pending.
- **FR-017**: Newly drawn cards MUST appear at the end of the hand without disturbing the existing visual order.

### Key Entities

- **DebugEntry**: An observer commentary or AI player prompt/response record. Extended with: `player_annotation` (text, nullable), `player_rating_override` (one of Good/Acceptable/Suboptimal, nullable).
- **PlayerAnnotation**: The free-text comment a human attaches to a DebugEntry. Attributes: entry_id, text, created_at, updated_at.
- **RatingOverride**: The player's replacement rating for an observer entry. Attributes: entry_id, original_rating (preserved), override_rating (player-supplied).
- **CardDisplayOrder**: Client-side ordering state for a player's hand and battlefield. Attributes: zone (hand or battlefield), ordered card/permanent IDs. Stored in browser memory only (v1).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A player can add, edit, and delete an annotation on any completed commentary entry in under 30 seconds with no additional navigation.
- **SC-002**: All player annotations and rating overrides appear in the exported game log without requiring any extra steps beyond the existing "Download Log" action.
- **SC-003**: The game log export clearly distinguishes AI-generated content from player annotations and overrides using labeled fields; a reader can identify them at a glance.
- **SC-004**: Original AI ratings are preserved in 100% of cases where a player override is applied — the original value is never lost or overwritten.
- **SC-005**: A player can drag and drop a card to a new position in their hand or battlefield in a single gesture without accidentally triggering a card-play action.
- **SC-006**: Card reordering produces no change to legal actions, active player, or any game state visible to the opponent or the engine.

## Assumptions

- Annotations and rating overrides are stored server-side (attached to the debug entry record) so they survive page refreshes and appear in the panel on reload.
- Card visual ordering is stored client-side (browser memory only) for v1 — it resets on page refresh. Server-side persistence of card order is out of scope.
- The "download game log" action refers to the existing `GET /export/{game_id}/game-log` endpoint; no new export format or file type is introduced.
- Only the human player in a human-vs-AI game can add annotations and override ratings; this UI is not exposed for AI-only spectator games.
- Rating override options are the same three values the observer uses: Good, Acceptable, Suboptimal.
- Annotation input is plain text only (no markdown or rich text) for v1.
- The drag-to-reorder for the battlefield applies only to the human player's own permanents, not the opponent's.
- Drag-to-play (existing feature) and drag-to-reorder are distinct interactions; the system must not confuse them. Dropping onto the battlefield zone plays a card; dropping within a zone reorders it.

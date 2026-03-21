# Research: Play-by-Play Game Log

**Feature**: 007-play-by-play-log
**Date**: 2026-03-21

## Findings

### 1. Existing Event Infrastructure

**Decision**: Build on top of `TranscriptRecorder` in `mtg_engine/export/transcript.py`.

**Rationale**: `TranscriptRecorder` already records every engine event in a structured `TranscriptEntry` format: `cast`, `resolve`, `trigger`, `sba`, `zone_change`, `damage`, `phase_change`, `priority_grant`, `choice_made`. All the raw data needed for a play-by-play log exists — the feature is primarily about (a) streaming those events to output in real time and (b) filling three gaps.

**Alternatives considered**: Adding a separate event bus; rejected as over-engineering since the transcript recorder is already the canonical event store.

---

### 2. Missing Events in TranscriptRecorder

**Decision**: Add three new recording methods to `TranscriptRecorder`:
- `record_life_change(player, delta, source, new_total, turn, phase, step)`
- `record_draw(player, turn, phase, step)` — card identity not recorded (private information per spec FR-006)
- `record_game_end(winner, reason, turn, phase, step)`

**Rationale**: Life total changes are currently tracked in player state (`PlayerState.life`) but not emitted as transcript events. Draw events are implicit in zone changes but not explicitly surfaced. Game-end is recorded as `is_game_over` / `winner` on `GameState` but not as a transcript entry. All three are required by FR-004, FR-006, and FR-009 respectively.

**Alternatives considered**: Deriving life changes by diffing state snapshots; rejected because it is unreliable (multiple changes can happen in one step) and adds complexity.

**Call sites to instrument**:
- Life changes: `mtg_engine/engine/combat.py` (damage application), `mtg_engine/engine/stack.py` (spell effects), `mtg_engine/engine/sba.py` (state-based actions)
- Draw: `mtg_engine/engine/zones.py` → `draw_card()` function
- Game end: `mtg_engine/engine/sba.py` → where `is_game_over` is set

---

### 3. Real-Time Output Strategy

**Decision**: Introduce a `VerboseLogger` class in `mtg_engine/engine/verbose_log.py` that wraps Python's standard `logging` module (at `INFO` level) and formats `TranscriptEntry` objects into human-readable sentences.

**Rationale**: The engine already uses `logging.getLogger(__name__)` throughout. Routing verbose output through the `logging` framework means callers can control destination (stdout, file, null handler) via standard Python logging configuration — no new I/O infrastructure needed. A dedicated `VerboseLogger` class keeps formatting logic isolated from the engine and from `TranscriptRecorder`.

**Alternatives considered**:
- Printing directly to stdout: works but bypasses logging control; makes testing harder.
- Adding a `verbose` flag to every engine function: invasive, high coupling; rejected.
- Observer/event bus pattern: correct but over-engineered for a single consumer.

---

### 4. Toggle Mechanism

**Decision**: Add a `verbose: bool = False` parameter to `GameManager.create_game()`, stored as a per-game flag. Expose `POST /game/{game_id}/verbose` (body: `{"enabled": true/false}`) to toggle mid-game.

**Rationale**: Per-game toggle satisfies FR-007 (toggle without restart) and SC-003 (single configuration change). Per-game (rather than global) scope means batch simulations can run silently while a single debug game streams output, without interference.

**Alternatives considered**: Environment variable toggle: satisfies off-by-default but not per-game control; retained as a future option for batch mode global default.

---

### 5. Output Format

**Decision**: Plain-text line-per-event format with phase/turn headers visually separated.

**Example output**:
```
═══ Turn 1 — player_1 ═══════════════════════════════
  [Beginning / Untap]
  [Beginning / Draw]
    player_1 draws a card.
  [Pre-combat Main]
    player_1 plays Forest.
    player_1 casts Llanowar Elves.
    Llanowar Elves resolves → enters the battlefield under player_1's control.
  [Combat / Declare Attackers]
    player_1 attacks with Llanowar Elves → targeting player_2.
═══ Turn 2 — player_2 ═══════════════════════════════
  ...
  player_2 takes 1 damage from Llanowar Elves. (player_2 life: 19)
  Llanowar Elves moves graveyard ← battlefield (controller: player_1).

══ GAME OVER — player_1 wins (opponent life reached zero) ══
```

**Rationale**: Turn headers are visually distinct (wide separator), phase labels are bracketed, and all entries are indented two spaces. This satisfies SC-002 (readable without knowledge of engine internals).

---

### 6. Zero-Cost Disabled Path

**Decision**: Guard all `VerboseLogger` calls with `if self._verbose_enabled` before any string formatting.

**Rationale**: SC-004 requires no throughput impact when disabled. Python string formatting is not free — even constructing the message string should be skipped. The standard `logging` module's lazy `%s` formatting helps, but the guard at the call site eliminates even the method dispatch overhead.

**Alternatives considered**: Using `logging.NOTSET` / no-op handler: still incurs Python call overhead on every event; the `if` guard is cheaper.

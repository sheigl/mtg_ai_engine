# Tasks: Play-by-Play Game Log

**Input**: Design documents from `/specs/007-play-by-play-log/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Create new file stubs so later tasks have clean targets.

- [x] T001 Create empty module stub `mtg_engine/engine/verbose_log.py` with module docstring only

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story work can proceed.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Extend `TranscriptRecorder` in `mtg_engine/export/transcript.py` with three new recording methods: `record_life_change(player, delta, source, new_total, turn, phase, step)`, `record_draw(player, turn, phase, step)` (no card identity), and `record_game_end(winner, reason, turn, phase, step)` — using `life_change`, `draw`, and `game_end` as `event_type` values matching the data-model
- [x] T003 Add a listener-registration mechanism to `TranscriptRecorder` in `mtg_engine/export/transcript.py`: a `_listeners: list[Callable[[TranscriptEntry], None]]` field, a `register_listener(fn)` method, and a call to `_notify_listeners(entry)` inside `_entry()` after appending to `self._entries`
- [x] T004 Implement `VerboseLogger` class in `mtg_engine/engine/verbose_log.py` with: `__init__(game_id: str, enabled: bool = False)`, `enable()`, `disable()`, `is_enabled` property, `on_event(entry: TranscriptEntry) -> None` (no-op when disabled, guarded by `if not self._enabled`), and `_format(entry: TranscriptEntry) -> str | None` (returns formatted string or None to suppress the entry — suppress `priority_grant` event_type)
- [x] T005 Add per-game verbose state to `GameManager` in `mtg_engine/api/game_manager.py`: add `_recorders: dict[str, TranscriptRecorder]` and `_verbose_loggers: dict[str, VerboseLogger]` fields; update `create_game()` to accept `verbose: bool = False`, create a `TranscriptRecorder` and `VerboseLogger` per game, register the logger as a listener on the recorder, and enable the logger if `verbose=True`; add `get_recorder(game_id)` and `set_verbose(game_id, enabled)` methods

**Checkpoint**: Foundation ready — each user story phase can now proceed.

---

## Phase 3: User Story 1 — View Player Moves in Real Time (Priority: P1) 🎯 MVP

**Goal**: Every substantive player action (cast, activate, attack, block) appears as a human-readable line in the log as it occurs, and verbose mode can be toggled on/off with a single API call.

**Independent Test**: Start a game with `"verbose": true`, play a spell, declare attackers, and verify log lines appear for each action with player name, action type, and card name. Then create a game with `"verbose": false` and confirm no output.

### Implementation for User Story 1

- [x] T006 [US1] Wire `record_cast` into `cast_spell()` in `mtg_engine/engine/stack.py`: after the `StackObject` is appended to `game_state.stack`, retrieve the per-game recorder from `GameManager` and call `recorder.record_cast(player, card_name, targets, turn, phase, step)`
- [x] T007 [US1] Wire `record_cast` (or a dedicated `record_activate`) into the ability activation path in `mtg_engine/api/routers/game.py` (the `POST /game/{game_id}/activate` endpoint handler): after a successful activation, call `recorder.record_cast` with action_type contextualised as "activates ability of"
- [x] T008 [US1] Wire `record_zone_change` into `declare_attackers()` in `mtg_engine/engine/combat.py`: after attacker list is set on `game_state.combat`, call `recorder` for each attacker with a descriptive attack entry (use `event_type="attack"` and a description like `"{player} attacks with {card_name} → {defending_id}"`)
- [x] T009 [US1] Wire `record_zone_change` into `declare_blockers()` in `mtg_engine/engine/combat.py`: after blockers are assigned, call `recorder` for each blocker assignment (use `event_type="block"` and a description like `"{player} blocks {attacker_name} with {blocker_name}"`)
- [x] T010 [US1] Add `VerboseLogger._format` cases in `mtg_engine/engine/verbose_log.py` for `cast`, `attack`, `block`, and `resolve` event types — returning plain-language sentences (e.g., `"  Alice casts Lightning Bolt targeting Bob."`, `"  Alice attacks with Grizzly Bears → Bob."`)
- [x] T011 [US1] Add `verbose: bool = False` field to `CreateGameRequest` in `mtg_engine/api/routers/game.py` and pass it through to `GameManager.create_game(verbose=req.verbose)`
- [x] T012 [US1] Add `POST /game/{game_id}/verbose` endpoint to `mtg_engine/api/routers/game.py` with request body `{"enabled": bool}` and response body `{"data": {"game_id": ..., "verbose_enabled": bool}}` as specified in `contracts/verbose-log-api.md`; call `GameManager.set_verbose(game_id, req.enabled)`

**Checkpoint**: User Story 1 fully functional — verbose cast/attack/block entries print to log, toggle endpoint works, disabled path produces no output.

---

## Phase 4: User Story 2 — Track Turn Structure and Phase Transitions (Priority: P2)

**Goal**: Turn headers and phase labels appear in the log before the actions within each phase, so the reader can follow the game's progression without counting turns manually.

**Independent Test**: Run a multi-turn game with verbose enabled and verify that (a) a turn header appears at the start of each player's turn, (b) phase labels appear before actions in that phase, and (c) a game-end closing entry appears when the game concludes.

### Implementation for User Story 2

- [x] T013 [US2] Wire `record_phase_change` into `advance_step()` in `mtg_engine/engine/turn_manager.py`: after `game_state.phase` and `game_state.step` are updated and before `begin_step` is called, retrieve the recorder and call `recorder.record_phase_change(turn, phase.value, step.value)`; also call it from `_advance_turn()` when the turn number increments
- [x] T014 [US2] Wire `recorder.record_game_end(winner, reason, turn, phase, step)` at the point in `mtg_engine/engine/sba.py` where `game_state.is_game_over` is set to `True` and `game_state.winner` is assigned; derive `reason` from the SBA type (e.g., `"life_total_zero"`, `"poison_counters"`, `"decked"`)
- [x] T015 [US2] Add `VerboseLogger._format` cases in `mtg_engine/engine/verbose_log.py` for `phase_change` and `game_end` event types — `phase_change` should render a wide turn header when `step == "untap"` (new turn) and a bracketed phase label otherwise (e.g., `"═══ Turn 3 — Alice ════..."`, `"  [Combat / Declare Attackers]"`); `game_end` should render a closing banner (e.g., `"══ GAME OVER — Alice wins (life_total_zero) ══"`)

**Checkpoint**: User Stories 1 and 2 both work — log has turn/phase structure wrapping action lines.

---

## Phase 5: User Story 3 — Life Totals and Zone Changes (Priority: P3)

**Goal**: Life total changes (with new total) and significant permanent zone transitions (entering/leaving battlefield, going to graveyard) are captured in the log so decisive moments are visible.

**Independent Test**: Run a game with combat damage and confirm the log contains (a) a life-change entry with amount and new total for the damaged player, (b) a zone-change entry for any creature that dies, and (c) a draw entry (player name only) whenever a card is drawn.

### Implementation for User Story 3

- [x] T016 [P] [US3] Wire `recorder.record_life_change(player, delta, source, new_total, ...)` at every point where `PlayerState.life` is decremented in `mtg_engine/engine/combat.py` (combat damage application) and `mtg_engine/engine/sba.py` (state-based life-loss); `delta` is negative for damage (e.g., `-3`), positive for life gain
- [x] T017 [P] [US3] Wire `recorder.record_draw(player, turn, phase, step)` inside `draw_card()` in `mtg_engine/engine/zones.py`, called after the card is successfully moved from library to hand — no card name is recorded
- [x] T018 [P] [US3] Wire `recorder.record_zone_change(card_name, from_zone, to_zone, player, ...)` inside `move_permanent_to_zone()` in `mtg_engine/engine/zones.py` for permanent transitions that involve the battlefield (i.e., `from_zone == "battlefield"` or `to_zone == "battlefield"`) — other zone moves (e.g., hand→graveyard for non-permanents) are already handled by the existing `_emit_zone_change` path for triggers
- [x] T019 [US3] Add `VerboseLogger._format` cases in `mtg_engine/engine/verbose_log.py` for `life_change`, `draw`, and `zone_change` event types — e.g., `"  Bob takes 3 damage from Grizzly Bears. (Bob life: 17)"`, `"  Alice draws a card."`, `"  Grizzly Bears moves battlefield → graveyard (Alice)."`

**Checkpoint**: All three user stories functional — log captures moves, phases, life totals, and zone changes end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, zero-cost disabled path validation, and documentation.

- [x] T020 [P] Write unit tests for `VerboseLogger` in `tests/rules/test_verbose_log.py`: (a) verify `on_event` produces no output when `is_enabled == False` even when called with a valid entry; (b) verify `_format` returns expected strings for each event type; (c) verify `priority_grant` entries return `None` from `_format`
- [x] T021 Write integration test in `tests/rules/test_verbose_log.py` that creates a game with `verbose=False`, runs several turns, and asserts that no lines were emitted to the `mtg_engine.verbose` logger (use `logging.handlers.MemoryHandler` or `caplog` pytest fixture)
- [x] T022 [P] Validate zero-cost disabled path: review every `recorder.record_X()` call site added in T006–T019 and confirm each is reached only after a successful action (not on the dry-run path); add `if req.dry_run: return ...` guards where missing
- [x] T023 [P] Update `CLAUDE.md` with the `mtg_engine.verbose` logger name and the per-game verbose toggle pattern so future contributors know how to enable play-by-play output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Phase 2 completion; stories can proceed in priority order or in parallel
- **Polish (Phase 6)**: Depends on all user story phases complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational only — no inter-story dependencies
- **User Story 2 (P2)**: Depends on Foundational only — independent of US1 (different engine call sites)
- **User Story 3 (P3)**: Depends on Foundational only — independent of US1/US2 (different engine call sites)

### Within Each User Story

- T004 (VerboseLogger) must complete before any `_format` case tasks (T010, T015, T019)
- T005 (GameManager update) must complete before API endpoint tasks (T011, T012)
- T003 (listener mechanism) must complete before T006–T009, T013, T014, T016–T018 (recorder call sites)
- Within US1: T006–T009 can run in parallel (different files); T010 depends on T004

### Parallel Opportunities

- T006, T007, T008, T009 — different engine files, all parallelizable once T003 and T005 complete
- T013, T014 — different engine files, parallelizable
- T016, T017, T018 — different engine files, parallelizable
- T020, T021, T022, T023 — independent polish tasks, all parallelizable

---

## Parallel Example: User Story 3

```bash
# Once T003 is done, launch these together:
Task T016: Instrument life_change in mtg_engine/engine/combat.py and sba.py
Task T017: Instrument draw in mtg_engine/engine/zones.py
Task T018: Instrument zone transitions in mtg_engine/engine/zones.py (move_permanent_to_zone)
# Then run T019 (formatter) after T016–T018 complete
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T005)
3. Complete Phase 3: User Story 1 (T006–T012)
4. **STOP and VALIDATE**: Create a game with `verbose=true`, cast a spell, declare attackers — verify log lines appear
5. Demo/review with user

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. Add US1 (T006–T012) → move log working, toggle endpoint live → **MVP**
3. Add US2 (T013–T015) → add turn/phase headers around the move log
4. Add US3 (T016–T019) → add life totals and zone changes
5. Polish (T020–T023) → tests, validation, docs

### Parallel Team Strategy

With two developers after Foundational is complete:
- Dev A: US1 (T006–T012) — engine call sites for cast/attack/block
- Dev B: US2 (T013–T015) — phase transition wiring in turn_manager and sba
- Merge and proceed to US3 together

---

## Notes

- All `recorder.record_X()` calls must be skipped on `dry_run=True` requests to avoid polluting the transcript with speculative actions
- `VerboseLogger.on_event` must never raise — wrap in try/except to prevent verbose logging bugs from crashing the game
- The `mtg_engine.verbose` logger name should be documented so operators can configure it separately from application logs
- Total tasks: **23** (T001–T023)

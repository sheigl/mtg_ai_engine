# Tasks: Skip Empty Phases

**Input**: Design documents from `/specs/029-skip-empty-phases/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal setup since this is an existing project. Understand current test structure.

- [x] T001 Review existing test structure in `tests/api/test_api.py` and `tests/api/test_bot_games.py`
- [x] T002 [P] Verify `pytest` runs successfully on current codebase

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract a reusable legal actions helper that can evaluate any player (not just priority holder). This MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 [P] Extract `get_legal_actions_for_player(gs: GameState, player_name: str)` helper from `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`
- [x] T004 [P] Update `_compute_legal_actions()` in `mtg_engine/api/routers/game.py` to call the new helper with `gs.priority_holder`
- [x] T005 Verify the extracted helper produces identical results to the original `_compute_legal_actions()` for all existing tests
- [x] T006 Create `can_skip_phase(gs: GameState)` helper in `mtg_engine/engine/turn_manager.py` that checks skip prevention conditions (stack, triggers, pending choices) and calls `get_legal_actions_for_player()` for both players

**Checkpoint**: Foundation ready — `can_skip_phase()` works correctly, all existing tests pass.

---

## Phase 3: User Story 1 - Auto-Skip Phases With No Actions (Priority: P1) 🎯 MVP

**Goal**: When a game enters a phase where every player has no legal actions except to pass priority, the system skips presenting that phase entirely and advances directly to the next phase.

**Independent Test**: Create a game state where both players have empty hands, no activated abilities, and no triggers — verify that Main Phase is skipped entirely without player interaction.

### Implementation for User Story 1

- [x] T007 [US1] Integrate `can_skip_phase()` into `advance_step()` in `mtg_engine/engine/turn_manager.py` after `begin_step()` but before priority grant
- [x] T008 [US1] Implement recursion safety with max 10 consecutive skips in `advance_step()`
- [x] T009 [US1] Add logging for skipped phases (info level: "Phase X skipped — no actions available")
- [x] T010 [US1] Verify Untap step is never skipped (no priority granted anyway)
- [x] T011 [US1] Verify existing `phase_skip_flags` logic (US7) still works alongside new skip logic

**Checkpoint**: At this point, User Story 1 should be fully functional. Empty phases are skipped, phases with actions are presented normally.

---

## Phase 4: User Story 2 - Transcript Records Skipped Phases (Priority: P1)

**Goal**: Even when phases are skipped, the game transcript contains a record with "skipped" status and reason.

**Independent Test**: Create a game with skipped phases and retrieve the transcript — verify skipped phases appear with `event_type="phase_skipped"` and complete metadata.

### Implementation for User Story 2

- [x] T012 [P] [US2] Add `record_phase_skipped()` method to `TranscriptRecorder` in `mtg_engine/export/transcript.py`
- [x] T013 [US2] Call `record_phase_skipped()` from the skip logic in `mtg_engine/engine/turn_manager.py`
- [x] T014 [P] [US2] Ensure consecutive skipped phases each get their own transcript entry (no collapsing)
- [x] T015 [US2] Verify transcript entries include turn, phase, step, active_player, and reason fields
- [x] T016 [US3] Verify playing a land prevents Main Phase skip in `mtg_engine/engine/turn_manager.py`
- [x] T017 [US3] Verify activated abilities prevent skip in all applicable phases
- [x] T018 [US3] Verify pending triggers (from `gs.pending_triggers`) prevent skip
- [x] T019 [US3] Verify pending choices (scry, surveil, tutor, discard, ward, echo, cascade, dredge, proliferate) prevent skip
- [x] T020 [US3] Verify non-empty stack prevents skip
- [x] T021 [US3] Verify cards in hand that cannot be legally played (wrong phase, insufficient mana) do NOT prevent skip
- [x] T022 [P] Add module-level docstring to new helper functions in `mtg_engine/engine/turn_manager.py`
- [x] T023 [P] Add module-level docstring to `record_phase_skipped()` in `mtg_engine/export/transcript.py`
- [x] T024 [P] Verify skip logic performance is <50ms per evaluation
- [x] T025 [P] Handle edge case: what happens if skip evaluation raises an exception (fail-safe: do not skip, log error)
- [x] T026 Verify quickstart.md examples work against a running local server

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001-T002). BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User stories can proceed in parallel (if staffed).
  - Or sequentially in priority order (P1 → P2).
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories.
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) and ideally after US1 (needs skip logic to exist for transcript recording).
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) and US1 (needs skip logic to validate against).

### Within Each User Story

- Helper before integration.
- Core implementation before edge cases.
- Story complete before moving to next priority.

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel.
- All Foundational tasks marked [P] can run in parallel (within Phase 2).
- Once Foundational phase completes:
  - US1 and US2 can run in parallel (T012-T014 are independent of T007-T011).
  - US3 validation tasks (T016-T021) can run in parallel.
- All Polish tasks marked [P] can run in parallel.

---

## Parallel Example: User Story 1 + US2

```bash
# Launch transcript recording alongside skip logic integration:
Task: "Integrate can_skip_phase into advance_step in mtg_engine/engine/turn_manager.py"
Task: "Add record_phase_skipped to TranscriptRecorder in mtg_engine/export/transcript.py"
Task: "Call record_phase_skipped from skip logic in mtg_engine/engine/turn_manager.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (core skip logic)
4. **STOP and VALIDATE**: Test US1 independently — create game with empty hands, verify phases skip
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add Polish phase → Final validation
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together.
2. Once Foundational is done:
   - Developer A: User Story 1 (skip logic in turn_manager)
   - Developer B: User Story 2 (transcript recording)
3. Stories complete and integrate independently.
4. Developer A or B: User Story 3 (action detection validation)
5. Team: Polish phase together.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to specific user story for traceability.
- Each user story should be independently completable and testable.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence.

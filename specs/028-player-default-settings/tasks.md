# Tasks: Player Default Settings

**Input**: Design documents from `/specs/028-player-default-settings/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal setup since this is an existing project. Ensure MongoDB collection is ready.

- [ ] T001 Add `get_player_defaults_collection()` getter to `mtg_engine/persistence/mongo_client.py`
- [ ] T002 [P] Create `ensure_player_defaults_indexes()` async function in `mtg_engine/persistence/mongo_client.py` to create unique index on `player_type`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, validation, and persistence layer that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 [P] Create `HumanPlayerSettings`, `AiPlayerSettings`, `HeuristicPlayerSettings` Pydantic models in `mtg_engine/models/player_defaults.py`
- [ ] T004 [P] Create `PlayerTypeDefaults` response model and `SaveDefaultsRequest` request model in `mtg_engine/models/player_defaults.py`
- [ ] T005 [P] Create `validate_settings_for_type()` and `merge_with_defaults()` helpers in `mtg_engine/models/player_defaults.py` (request values take precedence over defaults)
- [ ] T006 Implement async CRUD operations (`get_defaults`, `save_defaults`, `delete_defaults`, `list_defaults`) in `mtg_engine/persistence/player_defaults.py`
- [ ] T007 Wire `ensure_player_defaults_indexes()` into the application lifespan in `mtg_engine/api/main.py`

**Checkpoint**: Foundation ready - Pydantic models validate correctly, MongoDB collection is accessible, and CRUD functions work against the database.

---

## Phase 3: User Story 1 - Configure Default Settings for a Player Type (Priority: P1) 🎯 MVP

**Goal**: Administrators can save, retrieve, update, and delete default settings per player type via REST API.

**Independent Test**: Call `PUT /player-defaults/heuristic` with valid settings, then `GET /player-defaults/heuristic` and verify the saved values are returned. Call `DELETE /player-defaults/heuristic` and verify 404 on subsequent GET.

### Implementation for User Story 1

- [ ] T008 [P] [US1] Implement GET `/player-defaults` endpoint in `mtg_engine/api/routers/player_defaults.py`
- [ ] T009 [P] [US1] Implement GET `/player-defaults/{player_type}` endpoint in `mtg_engine/api/routers/player_defaults.py`
- [ ] T010 [US1] Implement PUT `/player-defaults/{player_type}` endpoint in `mtg_engine/api/routers/player_defaults.py`
- [ ] T011 [P] [US1] Implement DELETE `/player-defaults/{player_type}` endpoint in `mtg_engine/api/routers/player_defaults.py`
- [ ] T012 [US1] Register `player_defaults` router with `/player-defaults` prefix in `mtg_engine/api/main.py`

**Checkpoint**: At this point, User Story 1 should be fully functional. The admin CRUD API works independently and can be tested via curl or HTTP client without any game creation logic.

---

## Phase 4: User Story 2 - Apply Default Settings to New Players (Priority: P1)

**Goal**: When a new game is created, default settings for each player's type are automatically fetched from MongoDB and applied. If no defaults exist, the game creation proceeds with request values or hardcoded fallbacks.

**Independent Test**: Save defaults for `heuristic` player type, then call `POST /human-game` with `player2_type=heuristic` and omit `ai_model`/`ai_base_url`. Verify the game is created using the saved default values.

### Implementation for User Story 2

- [ ] T013 [US2] Create `get_merged_player_settings(player_type, request_values)` async helper in `mtg_engine/persistence/player_defaults.py` (fetches defaults and merges with request values)
- [ ] T014 [US2] Modify `POST /game` in `mtg_engine/api/routers/game.py` to call the merge helper for both `player1_type` and `player2_type` before `GameManager.create_game`
- [ ] T015 [US2] Modify `POST /human-game` in `mtg_engine/api/routers/human_game.py` to call the merge helper for the AI player and apply merged `ai_model`, `ai_base_url`, `ai_enable_thinking` values
- [ ] T016 [US2] Modify `POST /ai-game` in `mtg_engine/api/routers/ai_game.py` to call the merge helper for both AI players before game creation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Creating games with defaults configured uses those defaults; creating games without defaults uses existing behavior.

---

## Phase 5: User Story 3 - Override Defaults with Individual Player Settings (Priority: P2)

**Goal**: Request values provided at game creation time always take precedence over saved defaults. Updating defaults never affects already-created games.

**Independent Test**: Save defaults with `ai_model="gpt-4"`, then call `POST /human-game` with `ai_model="gpt-3.5"` and `player2_type="ai"`. Verify the game uses `gpt-3.5`, not the default `gpt-4`.

### Implementation for User Story 3

- [ ] T017 [US3] Verify `merge_with_defaults()` helper in `mtg_engine/models/player_defaults.py` correctly gives precedence to non-empty request values over defaults
- [ ] T018 [US3] Ensure `POST /human-game` in `mtg_engine/api/routers/human_game.py` respects explicit request values (`ai_model`, `ai_base_url`, `ai_enable_thinking`) over fetched defaults
- [ ] T019 [US3] Ensure `POST /game` in `mtg_engine/api/routers/game.py` and `POST /ai-game` in `mtg_engine/api/routers/ai_game.py` respect explicit request values over fetched defaults
- [ ] T020 [US3] Verify that updating defaults via PUT `/player-defaults/{player_type}` does not affect existing in-memory games (defaults are read at creation time only)

**Checkpoint**: All user stories should now be independently functional. Request values override defaults, and defaults updates are non-retroactive.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, documentation, and validation across all user stories.

- [ ] T021 [P] Add 422 validation for unsupported `player_type` values across all `/player-defaults` endpoints in `mtg_engine/api/routers/player_defaults.py`
- [ ] T022 [P] Add 503 `MONGODB_NOT_CONFIGURED` responses to all new endpoints when MongoDB is not configured
- [ ] T023 [P] Add module-level docstrings and type annotations to `mtg_engine/models/player_defaults.py`
- [ ] T024 [P] Add module-level docstrings and type annotations to `mtg_engine/persistence/player_defaults.py`
- [ ] T025 [P] Add module-level docstrings and type annotations to `mtg_engine/api/routers/player_defaults.py`
- [ ] T026 Validate quickstart.md examples (PUT, GET, DELETE, game creation with defaults) against a running local server

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001, T002). BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User stories can proceed in parallel (if staffed).
  - Or sequentially in priority order (P1 → P2).
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories.
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) and ideally after US1 (needs the CRUD endpoints to exist for end-to-end testing, but the merge helper can be developed in parallel).
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) and US2 (needs the game creation integration to exist). The override behavior is a refinement of the merge logic.

### Within Each User Story

- Models before services/endpoints.
- Core implementation before integration.
- Story complete before moving to next priority.

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel.
- All Foundational tasks marked [P] can run in parallel (within Phase 2).
- Once Foundational phase completes:
  - US1 endpoint tasks (T008, T009, T011) can run in parallel.
  - US2 game router modifications (T014, T015, T016) can run in parallel.
- All Polish tasks marked [P] can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all GET/DELETE endpoints together:
Task: "Implement GET /player-defaults endpoint in mtg_engine/api/routers/player_defaults.py"
Task: "Implement GET /player-defaults/{player_type} endpoint in mtg_engine/api/routers/player_defaults.py"
Task: "Implement DELETE /player-defaults/{player_type} endpoint in mtg_engine/api/routers/player_defaults.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all game router modifications together:
Task: "Modify POST /game in mtg_engine/api/routers/game.py to apply defaults"
Task: "Modify POST /human-game in mtg_engine/api/routers/human_game.py to apply defaults"
Task: "Modify POST /ai-game in mtg_engine/api/routers/ai_game.py to apply defaults"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (admin CRUD API)
4. **STOP and VALIDATE**: Test User Story 1 independently via curl/API client
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
   - Developer A: User Story 1 (CRUD endpoints)
   - Developer B: User Story 2 (game creation integration)
3. Stories complete and integrate independently.
4. Developer A or B: User Story 3 (override behavior refinement)
5. Team: Polish phase together.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to specific user story for traceability.
- Each user story should be independently completable and testable.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence.

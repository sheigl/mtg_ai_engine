# Tasks: AI CLI Client for MTG Games

**Input**: Design documents from `/specs/008-ai-cli-client/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `ai_client` package skeleton and register dependencies

- [X] T001 Create `ai_client/` package directory with `ai_client/__init__.py` (empty)
- [X] T002 Create `tests/cli/__init__.py` to register the test sub-package
- [X] T003 [P] Add `httpx` and `openai` to project dependencies (add to `requirements.txt` or `pyproject.toml`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures and HTTP wrapper that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement `PlayerConfig` and `GameConfig` dataclasses in `ai_client/models.py` — fields per `data-model.md` (`name`, `base_url`, `model`; `players`, `engine_url`, `deck1`, `deck2`, `verbose`, `max_turns`)
- [X] T005 Implement `TurnRecord` and `GameSummary` dataclasses in `ai_client/models.py` — fields per `data-model.md`
- [X] T006 Implement `EngineClient` in `ai_client/client.py` with methods: `create_game(config: GameConfig) -> str`, `get_legal_actions(game_id: str) -> dict`, `get_game_state(game_id: str) -> dict`, `submit_action(game_id: str, action_type: str, payload: dict) -> dict`, `set_verbose(game_id: str, enabled: bool) -> None`
- [X] T007 Define built-in 40-card default test deck constant in `ai_client/prompts.py` (20× Plains, 4× Lightning Bolt, 4× Grizzly Bears, 4× Llanowar Elves, 4× Giant Growth, 4× Counterspell)

**Checkpoint**: Foundation ready — `PlayerConfig`, `GameConfig`, `TurnRecord`, `GameSummary`, and `EngineClient` are importable and unit-testable

---

## Phase 3: User Story 1 — Launch AI vs AI Game (Priority: P1) 🎯 MVP

**Goal**: Two AI players run a complete game automatically via the engine API

**Independent Test**: `python -m ai_client --player "A,http://localhost:11434/v1,llama3" --player "B,http://localhost:11434/v1,llama3"` runs a full game to completion with winner printed

### Implementation for User Story 1

- [X] T008 [US1] Implement `build_game_state_prompt(state: dict, legal_actions: list[dict]) -> str` in `ai_client/prompts.py` — serialises current phase/step, active player, hand, battlefield, stack, and numbered legal action list into a plain-text LLM prompt
- [X] T009 [US1] Implement `AIPlayer` class in `ai_client/ai_player.py` — constructor takes `PlayerConfig`; `decide(prompt: str) -> tuple[int, str]` calls the OpenAI-compatible endpoint, parses JSON response `{"action_index": N, "reasoning": "..."}`, returns `(chosen_index, reasoning)`
- [X] T010 [US1] Implement `_map_action_to_request(action: dict) -> tuple[str, dict]` helper in `ai_client/game_loop.py` — maps `action_type` from legal-actions response to `(endpoint_path, request_payload)` (e.g. `"pass"` → `("/pass", {})`, `"cast"` → `("/cast", {"card_id": ..., "mana_payment": ...})`)
- [X] T011 [US1] Implement `GameLoop` class in `ai_client/game_loop.py` — constructor takes `GameConfig`, `EngineClient`, `list[AIPlayer]`; `run() -> GameSummary` creates game, loops on `legal-actions` until `is_game_over`, routes each turn to the right `AIPlayer`, submits action via `EngineClient`, returns `GameSummary`
- [X] T012 [US1] Implement `ai_client/__main__.py` entry point: parse `--player` flags into `PlayerConfig` objects (minimal validation), build `GameConfig`, construct `EngineClient` + `AIPlayer` instances, instantiate `GameLoop`, call `run()`, print `GameSummary` to console

**Checkpoint**: Running `python -m ai_client --player "..." --player "..."` completes a full game and prints winner, game ID, and turn count

---

## Phase 4: User Story 2 — Console Turn & Thought Logging (Priority: P2)

**Goal**: Every AI decision prints the player name, reasoning, and chosen action to the console before submission

**Independent Test**: Running any game with the CLI produces a clearly labelled log block per turn (separator, player name, reasoning, action); no turn is silent

### Implementation for User Story 2

- [X] T013 [US2] Implement `format_turn_header(record: TurnRecord) -> str` in `ai_client/game_loop.py` — formats the separator block per the console output contract in `contracts/cli-arguments.md` (dashes, `Turn N | PHASE / STEP`, `Player: ...`, `Reasoning: ...`, `Action: ...`)
- [X] T014 [US2] Update `GameLoop.run()` in `ai_client/game_loop.py` to build a `TurnRecord` for each decision and call `format_turn_header()` before submitting the action — including `fallback_used=True` if AI response parsing failed
- [X] T015 [US2] Update `AIPlayer.decide()` in `ai_client/ai_player.py` to return `"(no reasoning provided)"` when the LLM response contains no `reasoning` field, ensuring no output is silently dropped
- [X] T016 [US2] Implement `print_game_summary(summary: GameSummary) -> None` in `ai_client/game_loop.py` using the double-border format from `contracts/cli-arguments.md` (winner, game ID, turns, decisions, reason)
- [X] T017 [P] [US2] Add verbose board-state printing in `ai_client/game_loop.py`: when `GameConfig.verbose` is `True`, print `get_game_state()` response after each turn block (players' life totals, hand sizes, battlefield permanents)

**Checkpoint**: Every turn in the console output has a clearly labelled block with player name, reasoning text, and action; game summary prints at end

---

## Phase 5: User Story 3 — Flexible Per-Player CLI Configuration (Priority: P3)

**Goal**: All player and game parameters are fully configurable from the command line; malformed input produces descriptive errors

**Independent Test**: Running with `--player "A,http://host1/v1,model-a" --player "B,http://host2/v1,model-b"` routes Player A's turns exclusively to `host1` and Player B's to `host2`; running with no `--player` flags prints a usage error and exits non-zero

### Implementation for User Story 3

- [X] T018 [US3] Expand `ai_client/__main__.py` argparse setup to add `--engine URL`, `--deck1 CARDS`, `--deck2 CARDS`, `--verbose`, `--max-turns N`, and `--help` per `contracts/cli-arguments.md`; wire each into `GameConfig`
- [X] T019 [US3] Implement `parse_player_flag(value: str) -> PlayerConfig` in `ai_client/__main__.py` — splits on first two commas, validates all three parts non-empty and URL starts with `http://` or `https://`, raises `argparse.ArgumentTypeError` with descriptive message on failure
- [X] T020 [US3] Add minimum-player-count validation in `ai_client/__main__.py` — if fewer than two `--player` flags are supplied, print a descriptive error and exit with code 1
- [X] T021 [P] [US3] Add `--deck1` / `--deck2` comma-split parsing in `ai_client/__main__.py` — split on commas, strip whitespace, fall back to default deck constant from `ai_client/prompts.py` when flag is absent

**Checkpoint**: All CLI flags work, each player routes to its own configured endpoint, malformed `--player` values print clear errors, `--help` documents all flags

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, safety limits, and end-to-end validation

- [X] T022 Add single-retry logic on LLM failure in `ai_client/ai_player.py` — catch `openai.OpenAIError` or `httpx.HTTPError`, log `[WARNING]` line, retry once after 2 s, then set `fallback_used=True` and return `(0, "(AI endpoint unreachable)")` on second failure
- [X] T023 Add engine API error handling in `ai_client/client.py` — if any `httpx` call returns a non-2xx status, log the error with response body and raise a custom `EngineError`; catch `EngineError` in `GameLoop.run()`, print error, exit with code 1
- [X] T024 Add `max_turns` safety limit in `ai_client/game_loop.py` — if `turn_count >= GameConfig.max_turns`, set `termination_reason="max_turns_reached"`, print `GameSummary`, and exit cleanly with code 0
- [X] T025 [P] Add startup banner to `ai_client/__main__.py` — print engine URL, each player's name/model/endpoint, and game ID once the engine confirms game creation
- [ ] T026 Validate end-to-end with `quickstart.md` minimal invocation against a live engine and Ollama; confirm turn logs appear for every turn and final summary prints correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user story phases**
- **US1 (Phase 3)**: Depends on Phase 2 — no dependency on US2 or US3
- **US2 (Phase 4)**: Depends on Phase 3 (extends `GameLoop` and `AIPlayer`) — no dependency on US3
- **US3 (Phase 5)**: Depends on Phase 2 (uses `PlayerConfig`/`GameConfig`) — extends `__main__.py` independently of US2
- **Polish (Phase 6)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: Requires Foundational complete — no story dependencies
- **US2 (P2)**: Requires US1 complete — extends game loop with logging
- **US3 (P3)**: Requires Foundational complete — extends CLI entry point; can proceed in parallel with US1/US2

### Parallel Opportunities

Within Phase 2:
- T004 (`models.py`) and T006 (`client.py`) and T007 (`prompts.py`) can run in parallel

Within Phase 3 (once T007 done):
- T008 (`prompts.py`) and T009 (`ai_player.py`) can run in parallel

Within Phase 5:
- T021 (deck parsing) is independent of T018/T019/T020 on non-overlapping lines

---

## Parallel Example: User Story 1

```bash
# After Foundational phase, launch in parallel:
Task T008: "build_game_state_prompt in ai_client/prompts.py"
Task T009: "AIPlayer class in ai_client/ai_player.py"
# Then sequentially:
Task T010: "_map_action_to_request in ai_client/game_loop.py"
Task T011: "GameLoop class in ai_client/game_loop.py" (depends on T008, T009, T010)
Task T012: "__main__.py entry point" (depends on T011)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — `EngineClient`, `PlayerConfig`, `GameConfig`, default deck
3. Complete Phase 3: US1 — AI players run a full game automatically
4. **STOP and VALIDATE**: `python -m ai_client --player "..." --player "..."` completes a game and prints a winner
5. Demo if ready

### Incremental Delivery

1. Phase 1 + 2 → Infrastructure ready
2. Phase 3 → US1 game loop works (minimal hardcoded args acceptable)
3. Phase 4 → US2 turn logging visible in console
4. Phase 5 → US3 full CLI flexibility
5. Phase 6 → Production-ready with error handling and safety limits

### Parallel Team Strategy

With two developers after Foundational:
- **Developer A**: US1 (Phase 3) + US2 (Phase 4) — game loop and logging
- **Developer B**: US3 (Phase 5) — CLI argument parsing and validation
- Merge and integrate after both complete; US3 replaces the minimal `__main__.py` stub from US1

---

## Notes

- [P] tasks = different files or non-overlapping sections, no inter-task dependencies
- [Story] label maps each task to its user story for traceability
- No test tasks generated (none requested in spec)
- Stop at each **Checkpoint** to validate the story independently before proceeding
- Commit after each logical group (e.g., after T007, after T012, after T017)

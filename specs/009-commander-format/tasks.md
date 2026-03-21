# Tasks: Commander Format Support

**Input**: Design documents from `/specs/009-commander-format/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new directories or packages required — all changes are additive to existing modules. This phase confirms the branch and existing test suite are green before any changes.

- [X] T001 Verify all existing tests pass on branch `009-commander-format` by running `pytest tests/ -q` — must be 0 failures before any changes are made
- [X] T002 [P] Add `color_identity: list[str] = []` field to the `Card` model in `mtg_engine/models/game.py` — import `Field` is already available; this is a non-breaking additive change

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All model extensions and deck-validation logic that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `command_zone: list[Card] = Field(default_factory=list)`, `commander_name: Optional[str] = None`, and `commander_cast_count: int = 0` to `PlayerState` in `mtg_engine/models/game.py`
- [X] T004 Add `format: str = "standard"` and `commander_damage: dict[str, dict[str, int]] = Field(default_factory=dict)` to `GameState` in `mtg_engine/models/game.py`
- [X] T005 [P] Add `from_command_zone: bool = False` to `CastRequest` in `mtg_engine/models/actions.py`
- [X] T006 [P] Update `ScryfallClient._build_card()` in `mtg_engine/card_data/scryfall.py` to populate `color_identity=raw.get("color_identity", [])` on the returned `Card` object
- [X] T007 Add `format: str = "standard"`, `commander1: Optional[str] = None`, `commander2: Optional[str] = None` fields to `CreateGameRequest` in `mtg_engine/api/routers/game.py`
- [X] T008 Implement `load_commander_deck(card_names: list[str], commander_name: str, db_path=None) -> tuple[list[Card], Card]` in `mtg_engine/card_data/deck_loader.py` — resolves all cards via `ScryfallClient`, finds and removes the commander card, validates: (1) commander is legendary creature, (2) remaining deck is exactly 99 cards, (3) no duplicate non-basic-land cards (basic land names: Plains, Island, Swamp, Mountain, Forest, Wastes), (4) every card's `color_identity` is a subset of the commander's `color_identity`; raises `ValueError` with specific message on each violation
- [X] T009 Add `"command_zone"` to `_get_player_zone()` zone map in `mtg_engine/engine/zones.py` returning `player.command_zone`, and add helper `move_card_to_command_zone(game_state: GameState, card: Card, player_name: str) -> GameState` that appends the card to the player's `command_zone` and emits a zone-change event with `to_zone="command_zone"`

**Checkpoint**: All model fields are importable; `load_commander_deck()` raises correct errors for each validation rule; all existing tests still pass.

---

## Phase 3: User Story 1 — Start a Commander Game (Priority: P1) 🎯 MVP

**Goal**: A Commander game can be created via `POST /game` with two valid 100-card singleton decks, 40 starting life, commanders in command zones, and commander tax applied on re-cast.

**Independent Test**: `POST /game` with `format=commander`, two 99-card singleton decks, two legendary commander names → 200 response with `players[N].life == 40`, `players[N].command_zone[0].name == commander_name`, commander absent from library. Then submit legal actions → `cast_commander` appears when player has mana. Submit `POST /cast` with `from_command_zone=true` → commander moves to stack, `commander_cast_count` increments to 1, second legal-actions call shows tax in description.

### Implementation for User Story 1

- [X] T010 [US1] Extend `GameManager.create_game()` in `mtg_engine/api/game_manager.py` to accept `format: str = "standard"`, `commander1_card: Optional[Card] = None`, `commander2_card: Optional[Card] = None` parameters; when `format == "commander"`: set `p1.life = 40`, `p2.life = 40`, set `p1.commander_name`, `p2.commander_name`, `p1.commander_cast_count = 0`, `p2.commander_cast_count = 0`, place commander cards into `p1.command_zone` / `p2.command_zone`, set `gs.format = "commander"`
- [X] T011 [US1] Update the `create_game` endpoint in `mtg_engine/api/routers/game.py` to: when `req.format == "commander"` and `commander1`/`commander2` are provided, call `load_commander_deck(req.deck1, req.commander1)` and `load_commander_deck(req.deck2, req.commander2)` instead of `load_deck()`; pass the returned commander cards to `mgr.create_game()`; surface all `ValueError` messages as `DECK_LOAD_ERROR` / `SINGLETON_VIOLATION` / `COLOR_IDENTITY_VIOLATION` / `INVALID_COMMANDER` HTTP 422 errors with the appropriate `error_code`
- [X] T012 [US1] Add commander redirect logic in `mtg_engine/engine/zones.py` `move_card_to_zone()`: when `to_zone` is `"graveyard"` or `"exile"` and the card's name matches `player.commander_name`, redirect the move to `command_zone` instead (call `move_card_to_command_zone()`) and emit a zone-change event with `to_zone="command_zone"`; skip if `format != "commander"` on the game state
- [X] T013 [US1] Extend `_compute_legal_actions()` in `mtg_engine/api/routers/game.py` to: when `gs.format == "commander"`, check if the priority player's `command_zone` is non-empty; compute `tax = 2 × player.commander_cast_count`; check if player can pay `commander_base_mana_cost` plus `tax` generic mana using existing `can_pay_cost()`; if yes, append `LegalAction(action_type="cast_commander", card_id=commander_card.id, card_name=commander_card.name, description=f"Cast {name} from command zone (cost: {base_cost} + {tax} tax)", mana_options=[{"mana_cost": base_cost, "commander_tax": tax}])`
- [X] T014 [US1] Extend the `cast()` endpoint in `mtg_engine/api/routers/game.py` to handle `req.from_command_zone == True`: find the card in `player.command_zone` instead of `player.hand` (raise `INVALID_ACTION` if not found); validate that `req.mana_payment` covers base cost plus tax; call `cast_spell()` with the found card; on success, remove the card from `command_zone` and increment `player.commander_cast_count`

**Checkpoint**: `POST /game` (Commander) starts with 40 life and commanders in command zones. `GET /game/{id}/legal-actions` includes `cast_commander` when mana is available. `POST /game/{id}/cast` with `from_command_zone=true` succeeds, increments cast count, second cast shows tax in legal actions.

---

## Phase 4: User Story 2 — Commander Damage Tracking (Priority: P2)

**Goal**: The engine tracks cumulative combat damage dealt by each commander permanent, and applies the 21-damage loss SBA.

**Independent Test**: Create a Commander game, advance to combat, submit `assign-combat-damage` with a commander as attacker. Verify `GET /game/{id}` shows `commander_damage` updated. Repeat until total reaches 21; verify `is_game_over=True` and correct `winner`.

### Implementation for User Story 2

- [X] T015 [US2] In `mtg_engine/engine/combat.py` `assign_combat_damage()`, after applying player life damage: check if each attacking permanent's card name matches `perm.controller`'s `commander_name` (i.e., the attacker is a commander); if so, record damage in `gs.commander_damage[perm.id][defender_player_name] += damage_amount` — create nested dict entries as needed; this runs for every combat damage assignment where the target is a player (not a blocker)
- [X] T016 [US2] In `mtg_engine/engine/sba.py` `_check_once()`, add a commander damage SBA check after the poison check: iterate `gs.commander_damage.items()`; for each `(perm_id, damage_by_player)`, for each `(defender_name, total)`, find the defender in `gs.players`; if `total >= 21` and `not player.has_lost`, set `player.has_lost = True` and append `SBAEvent("commander_damage", f"{defender_name} has taken 21+ commander damage from {perm_id} and loses", [defender_name])`; only apply when `gs.format == "commander"`

**Checkpoint**: After enough combat damage from a commander, `is_game_over=True` with the correct winner. `commander_damage` dict in game state shows per-commander, per-player accumulated totals. Two different commanders each dealing 10 damage does NOT trigger the SBA.

---

## Phase 5: User Story 3 — AI Client Commander Mode (Priority: P3)

**Goal**: The AI CLI client supports `--format commander` and `--commander NAME` flags, runs a complete Commander game loop, and correctly handles command-zone casting.

**Independent Test**: `python -m ai_client --format commander --player "A,..." --player "B,..." --commander "Multani, Maro-Sorcerer" --commander "Ghalta, Primal Hunger"` starts a Commander game; startup banner shows `[Commander]` and commander names; turn prompts include command zone info; `cast_commander` action is mapped correctly; game ends with summary.

### Implementation for User Story 3

- [X] T017 [US3] Add `format: str = "standard"`, `commander1: Optional[str] = None`, `commander2: Optional[str] = None` fields to `GameConfig` dataclass in `ai_client/models.py`
- [X] T018 [US3] Update `EngineClient.create_game()` in `ai_client/client.py` to include `"format"`, `"commander1"`, `"commander2"` in the request body when `config.format == "commander"` and the fields are set
- [X] T019 [US3] Add `--format standard|commander` flag and `--commander NAME` flag (repeatable, `action="append"`) to the argparse setup in `ai_client/__main__.py`; validate that exactly 2 `--commander` values are supplied when `--format commander`; populate `GameConfig.format`, `GameConfig.commander1`, `GameConfig.commander2`; exit 1 with descriptive error if `--format commander` is used without exactly 2 `--commander` flags
- [X] T020 [US3] Add `DEFAULT_COMMANDER_DECK: list[str]` constant to `ai_client/prompts.py` — a 99-card mono-green singleton list (37× Forest plus 62 unique green cards: 4× Llanowar Elves, 4× Elvish Mystic, 4× Grizzly Bears, 4× Giant Growth, 4× Elvish Warrior, 4× Troll Ascetic, 4× Leatherback Baloth, 4× Garruk's Companion, 4× Rancor, 4× Giant Spider, 4× Kalonian Tusker, 4× Prey Upon, 4× Titanic Growth, 3× Woodfall Primus); also update `build_game_state_prompt()` to include command zone contents (`command_zone` from player state), current commander tax, and accumulated commander damage totals when present in the game state
- [X] T021 [US3] Update `_map_action_to_request()` in `ai_client/game_loop.py` to handle `action_type == "cast_commander"` by returning `("cast", {"card_id": action["card_id"], "targets": [], "mana_payment": {}, "from_command_zone": True})`; update `GameLoop.run()` startup banner to show `[Commander]` suffix in title and include each player's commander name when `config.format == "commander"`; update `print_game_summary()` to show commander damage totals from the final game state when in Commander mode
- [X] T022 [P] [US3] Update `ai_client/__main__.py` `main()` to use `DEFAULT_COMMANDER_DECK` (from `ai_client/prompts.py`) as the default for `--deck1`/`--deck2` when `--format commander` is specified and no deck flags are provided (instead of `DEFAULT_DECK`)

**Checkpoint**: `python -m ai_client --format commander ...` runs a game. Startup shows `[Commander]`. Turns include command zone state in reasoning prompt. `cast_commander` legal action triggers a cast with `from_command_zone=true`. Game summary shows commander damage totals.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression validation and end-to-end confirmation.

- [X] T023 Run full test suite (`pytest tests/ -v`) and confirm 0 regressions — all pre-existing standard game tests must pass; fix any breakage before marking complete
- [X] T024 [P] Validate end-to-end with `quickstart.md` Commander curl examples against a live engine: create a Commander game, confirm 40 life + command zones, submit a `cast_commander` action, confirm `commander_cast_count` increments and tax appears in next legal-actions response

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user story phases**
- **US1 (Phase 3)**: Depends on Phase 2 — no dependency on US2 or US3
- **US2 (Phase 4)**: Depends on Phase 2 — no dependency on US1 or US3 (but benefits from Phase 3 for end-to-end testing)
- **US3 (Phase 5)**: Depends on Phase 2 — extends AI client independently; full end-to-end requires US1 + US2
- **Polish (Phase 6)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: Requires Foundational — no story dependencies
- **US2 (P2)**: Requires Foundational — no story dependencies; runs independently of US1
- **US3 (P3)**: Requires Foundational + at minimum US1 (engine must create Commander games); benefits from US2 for full game-over testing

### Parallel Opportunities

Within Phase 2 (Foundational):
- T002 (`game.py` Card field), T005 (`actions.py`), T006 (`scryfall.py`) can run in parallel
- T003 and T004 (both in `game.py`) must run sequentially
- T007 (`game.py` router) and T008 (`deck_loader.py`) and T009 (`zones.py`) can run in parallel after T003/T004

Within Phase 5 (US3):
- T017 (`models.py`) and T020 (`prompts.py`) can run in parallel
- T022 (`__main__.py` deck default) is independent of T021 (`game_loop.py`)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase, these can run in parallel:
Task T010: "Extend GameManager.create_game() in game_manager.py"
Task T013: "Extend _compute_legal_actions() for cast_commander in game.py"

# Then sequentially:
Task T011: "Update create_game endpoint in game.py" (needs T010)
Task T012: "Add commander redirect in zones.py" (independent of T010/T011)
Task T014: "Extend cast() endpoint for from_command_zone" (needs T013)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify green baseline)
2. Complete Phase 2: Foundational (models + deck validation + zones)
3. Complete Phase 3: US1 (game creation + casting)
4. **STOP and VALIDATE**: `POST /game` creates Commander game; `cast_commander` works with tax
5. Demo if ready

### Incremental Delivery

1. Phase 1 + 2 → Infrastructure ready
2. Phase 3 → Commander games start and commanders can be cast (MVP)
3. Phase 4 → Commander damage win condition enforced
4. Phase 5 → AI client can play Commander games autonomously
5. Phase 6 → Regression confirmed, quickstart validated

### Parallel Team Strategy

With two developers after Foundational:
- **Developer A**: US1 (Phase 3) + US2 (Phase 4) — engine Commander rules
- **Developer B**: US3 (Phase 5) — AI client Commander mode (can stub engine if needed)
- Merge and validate after both complete

---

## Notes

- [P] tasks = different files or non-overlapping sections, no inter-task dependencies
- [Story] label maps each task to its user story for traceability
- No test tasks generated (none requested in spec)
- Stop at each **Checkpoint** to validate the story independently before proceeding
- Commit after each logical group (e.g., after T009, after T014, after T016, after T022)
- The `color_identity` field added to `Card` (T002/T006) is used by deck validation (T008) but has no effect on standard game play — zero regression risk

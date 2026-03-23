# Tasks: Rules Engine Completeness

**Input**: Design documents from `/specs/014-rules-engine-completeness/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story; each story is independently implementable and testable.
**Tests**: Not explicitly requested — no test tasks generated. Existing test files will be extended inline where noted.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Existing Structure)

**Purpose**: Confirm existing codebase baseline before making additive changes.

- [X] T001 Verify existing test suite passes with `python -m pytest tests/ -v` and record baseline pass/fail counts in tests/rules/ directory
- [X] T002 [P] Read and understand mtg_engine/engine/sba.py to confirm existing SBA checks and identify the missing CR 704.5b deck-out check
- [X] T003 [P] Read and understand mtg_engine/engine/mana.py to confirm _can_pay_simple and _validate_payment do not handle hybrid/Phyrexian symbols

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add new model fields and classes that multiple user stories depend on. Must be complete before US3–US7 can be implemented.

**⚠️ CRITICAL**: US3–US7 require `GameState` to have the new fields defined here.

- [X] T004 Add `DamagePreventionEffect` Pydantic model to mtg_engine/models/game.py with fields: `effect_id: str`, `source_permanent_id: str | None`, `target_id: str | None`, `remaining: int | None`, `combat_only: bool = False`, `color_restriction: str | None = None`
- [X] T005 Add `AttackConstraint` Pydantic model to mtg_engine/models/game.py with fields: `source_id: str`, `affected_id: str`, `constraint_type: str` (values: `"must_attack"`, `"cannot_attack"`, `"cost_to_attack"`, `"goad"`), `cost: str | None = None`, `goad_controller: str | None = None`
- [X] T006 Add `BlockConstraint` Pydantic model to mtg_engine/models/game.py with fields: `source_id: str`, `affected_id: str`, `constraint_type: str` (values: `"cannot_block"`, `"can_only_block_flyers"`, `"min_power_to_block"`), `restriction: str | None = None`
- [X] T007 Add new optional fields to `GameState` in mtg_engine/models/game.py: `prevention_effects: list[DamagePreventionEffect] = Field(default_factory=list)`, `attack_constraints: list[AttackConstraint] = Field(default_factory=list)`, `block_constraints: list[BlockConstraint] = Field(default_factory=list)`, `prevent_all_combat_damage: bool = False`, `phase_skip_flags: dict[str, bool] = Field(default_factory=dict)`
- [X] T008 Add optional field `copy_of_permanent_id: str | None = None` to `Permanent` model in mtg_engine/models/game.py (used by layer 1 copy effects in US5)

**Checkpoint**: Model changes committed — all existing tests must still pass.

---

## Phase 3: User Story 1 — State-Based Actions Correctness (Priority: P1) 🎯 MVP

**Goal**: Engine correctly applies deck-out loss (CR 704.5b) and planeswalker 0-loyalty destruction (CR 704.5i). PW destruction is already implemented; this phase adds deck-out.

**Independent Test**: Create a game where a player has an empty library, call draw_card, call check_and_apply_sbas, and assert `gs.is_game_over == True` and `gs.winner` is the other player.

- [X] T009 [US1] In mtg_engine/engine/zones.py `draw_card()`, when `player.library` is empty, set `player.has_lost = True` and log at WARNING level `"[SBA 704.5b] {player_name} attempted to draw from empty library — player loses"` before returning `(game_state, None)`
- [X] T010 [US1] Add a test case to tests/rules/test_sba.py: create minimal GameState with player1 having an empty library, call `draw_card(gs, "player_1")`, then `check_and_apply_sbas(gs)`, and assert `gs.is_game_over` and `gs.winner == "player_2"`
- [X] T011 [US1] Add a test case to tests/rules/test_sba.py verifying the existing planeswalker 0-loyalty SBA: create a Permanent with `type_line="Planeswalker"` and `counters={"loyalty": 0}`, call `check_and_apply_sbas`, and assert the permanent is removed from battlefield

**Checkpoint**: `python -m pytest tests/rules/test_sba.py -v` passes; deck-out scenario correctly ends the game.

---

## Phase 4: User Story 2 — Triggered Ability Coverage (Priority: P2)

**Goal**: Combat damage triggers ("whenever this deals combat damage to a player") are detected and queued after `assign_combat_damage`. Phase triggers (upkeep, end step) already work — this phase adds damage triggers.

**Independent Test**: Create a creature with oracle text containing `"whenever this creature deals combat damage to a player"`, run `assign_combat_damage` with that creature as an unblocked attacker, and assert a `PendingTrigger` with `trigger_type == "combat_damage"` is in `game_state.pending_triggers`.

- [X] T012 [US2] In mtg_engine/engine/triggers.py, add `check_damage_triggers(game_state: GameState, assignments: list) -> GameState` that iterates `assignments`, for each attacker dealing damage to a player: scans all permanents for `"whenever this.*deals.*combat damage"` or `"whenever ~ deals combat damage to a player"` oracle patterns (case-insensitive), and queues a `PendingTrigger` with `trigger_type="combat_damage"` for the matching source permanent's controller
- [X] T013 [US2] In mtg_engine/engine/combat.py `assign_combat_damage()`, after damage is applied and before returning, call `from mtg_engine.engine.triggers import check_damage_triggers` and `game_state = check_damage_triggers(game_state, all_assignments)` (using the `all_assignments` list that includes both attacker and blocker damage)
- [X] T014 [US2] Add test cases to tests/rules/test_triggers.py: (a) creature with "whenever this creature deals combat damage to a player" trigger fires after unblocked combat damage; (b) trigger does NOT fire when creature deals 0 damage; (c) `apnap_order_triggers` correctly orders combat_damage triggers

**Checkpoint**: `python -m pytest tests/rules/test_triggers.py -v` passes; damage triggers are queued after combat.

---

## Phase 5: User Story 3 — Mana Cost Enforcement (Priority: P3)

**Goal**: Hybrid mana pips ({G/W}, {2/B}) and Phyrexian mana pips ({B/P}) are correctly validated. Currently `_can_pay_simple` ignores hybrid/Phyrexian symbols parsed into the cost dict.

**Independent Test**: `can_pay_cost(ManaPool(G=1), "{G/W}") == True`; `can_pay_cost(ManaPool(U=3), "{G/W}") == False`; `can_pay_cost(ManaPool(), "{B/P}", player_life=4) == True`.

- [X] T015 [US3] In mtg_engine/engine/mana.py, extend `_can_pay_simple(pool, cost)` to handle hybrid symbols: for each key in `cost` that contains `/` and is not Phyrexian (not ending in `/P`): parse the two options (e.g. `"G/W"` → options `"G"` and `"W"`; `"2/B"` → generic-2 or color-B), check if either option is satisfiable from the remaining pool, and deduct the chosen option. Return `False` if neither option is available.
- [X] T016 [US3] In mtg_engine/engine/mana.py, handle Phyrexian mana symbols (symbols ending in `/P`, e.g. `"B/P"`, `"G/P"`) in `_can_pay_simple`: add optional `player_life: int = 999` parameter to `_can_pay_simple`; for each Phyrexian pip, check if the colored option is available in the pool OR if `player_life >= 2`; deduct the colored mana if available (prefer mana over life payment in the simple check); otherwise return `False` if neither option works.
- [X] T017 [US3] Update `can_pay_cost(pool, mana_cost, payment=None, player_life=999)` signature in mtg_engine/engine/mana.py to pass `player_life` through to `_can_pay_simple` so callers providing player life totals can get correct Phyrexian validation
- [X] T018 [US3] Add Phyrexian life deduction to `pay_cost()` in mtg_engine/engine/mana.py: when a Phyrexian pip is in the cost and the player chose to pay life (i.e., the colored mana was not deducted for that pip), include the life cost in the return value as a `life_cost: int` field — OR return a tuple `(new_pool, life_cost)` and update callers in stack.py accordingly
- [X] T019 [US3] Add test cases to tests/rules/test_mana.py covering: (a) hybrid `{G/W}` castable with green only; (b) hybrid `{G/W}` castable with white only; (c) hybrid `{G/W}` not castable with only blue; (d) `{2/B}` castable with 2 generic or 1 black; (e) Phyrexian `{B/P}` castable with 1 black mana; (f) Phyrexian `{B/P}` castable with 2 life (player_life=4); (g) Phyrexian `{B/P}` not castable with 0 life and no black mana

**Checkpoint**: `python -m pytest tests/rules/test_mana.py -v` passes; hybrid and Phyrexian validation is correct.

---

## Phase 6: User Story 4 — Damage Prevention Replacement Effects (Priority: P4)

**Goal**: Active `DamagePreventionEffect` entries in `GameState.prevention_effects` reduce or eliminate damage before it is marked. `prevent_all_combat_damage` flag blocks all combat damage (Fog). Protection from color prevents damage from that color source.

**Independent Test**: Set `gs.prevent_all_combat_damage = True`, run `assign_combat_damage`, and assert no player life changed.

- [X] T020 [US4] In mtg_engine/engine/replacement.py, update `_get_replacement_effects()` to also check `game_state.prevention_effects` list: for each `DamagePreventionEffect` with `remaining > 0` (or `remaining is None`), create a `ReplacementEffect` with `event_types=["damage"]` and bind the prevention logic
- [X] T021 [US4] In mtg_engine/engine/replacement.py `apply_replacement()`, add handling for prevention effect IDs: reduce `event.modified_amount` by up to `remaining` of the prevention effect, decrement `remaining`, remove the effect from `game_state.prevention_effects` when `remaining` reaches 0, and set `event.cancelled = True` if all damage is prevented
- [X] T022 [US4] In mtg_engine/engine/combat.py `assign_combat_damage()`, at the top of the function (before any damage is applied), check `game_state.prevent_all_combat_damage`: if `True`, skip all damage application (return early after setting `game_state.combat.damage_assigned = True`) and reset `game_state.prevent_all_combat_damage = False`
- [X] T023 [US4] In mtg_engine/engine/replacement.py `apply_damage_event()`, add a protection-from-color check: before processing replacement effects, check if the target permanent has any `"protection from {color}"` keywords (e.g. `"protection from red"`) and if the source card's colors list contains that color; if so, set `event.cancelled = True` and return immediately (damage fully prevented by protection)
- [X] T024 [US4] In mtg_engine/engine/turn_manager.py `begin_step()` cleanup section (Step.CLEANUP), add `game_state.prevention_effects.clear()` and `game_state.prevent_all_combat_damage = False` to ensure all prevention effects are cleared at the end of each turn
- [X] T025 [US4] Add test cases to tests/rules/test_replacement.py: (a) `prevent_all_combat_damage=True` results in 0 damage from `assign_combat_damage`; (b) `DamagePreventionEffect(remaining=3)` reduces 5 damage to 2 and is decremented; (c) protection from red prevents damage from a red source; (d) protection does not prevent damage from a non-matching color

**Checkpoint**: `python -m pytest tests/rules/test_replacement.py -v` passes; Fog and protection effects work correctly.

---

## Phase 7: User Story 5 — Full Layer System (Priority: P5)

**Goal**: `collect_continuous_effects` in `layers.py` generates effects for layers 1 (copy), 2 (control change), 4 (type change), and 5 (color change) in addition to existing layers 6 and 7. Layer 3 (text) is scaffolded but not matched.

**Independent Test**: A permanent with `copy_of_permanent_id` set to another permanent should have the source's card data applied via layer 1. A permanent with a control-change aura should have its controller updated after `apply_continuous_effects`.

- [X] T026 [US5] In mtg_engine/engine/layers.py `collect_continuous_effects()`, add Layer 1 (COPY) effect generation: for each permanent on the battlefield where `perm.copy_of_permanent_id` is not `None`, find the source permanent with that ID and create a `ContinuousEffect` (layer=COPY, sublayer=None, is_cda=False) with an `apply_fn` that copies the source permanent's `card` copiable values (`name`, `mana_cost`, `type_line`, `oracle_text`, `power`, `toughness`, `colors`, `keywords`) onto the target permanent using `model_copy(update={...})`
- [X] T027 [US5] In mtg_engine/engine/layers.py `collect_continuous_effects()`, add Layer 2 (CONTROL) effect generation: scan oracle text for `"you control enchanted"` or `"gain control of enchanted creature"` patterns on aura permanents that have `perm.attached_to` set; create a `ContinuousEffect` (layer=CONTROL, sublayer=None) with `apply_fn` that sets `target.controller = perm.controller` where target is the `perm.attached_to` permanent ID
- [X] T028 [US5] [P] In mtg_engine/engine/layers.py `collect_continuous_effects()`, add Layer 4 (TYPE) effect generation: scan oracle text for `"is [a/an] artifact in addition to"`, `"becomes a [type]"`, and `"is all types"` patterns; create a `ContinuousEffect` (layer=TYPE, sublayer=None) with `apply_fn` that appends the new type to `target.card.type_line` using `model_copy`
- [X] T029 [US5] [P] In mtg_engine/engine/layers.py `collect_continuous_effects()`, add Layer 5 (COLOR) effect generation: scan oracle text for `"is [color]"`, `"is all colors"`, and `"is colorless"` patterns; create a `ContinuousEffect` (layer=COLOR, sublayer=None) with `apply_fn` that sets `target.card.colors` to the appropriate list (`[]` for colorless, `["W","U","B","R","G"]` for all colors, or a specific color list) using `model_copy`
- [X] T030 [US5] In mtg_engine/engine/layers.py `collect_continuous_effects()`, add a stub comment block for Layer 3 (TEXT) at the correct position in the function, noting that text-change effects (e.g. Magical Hack changing "Forest" to "Island") are not pattern-matched in this implementation but the layer is applied in `apply_continuous_effects` layer order
- [X] T031 [US5] Add test cases to tests/rules/test_layers.py: (a) permanent with `copy_of_permanent_id` acquires source card's P/T and keywords after `apply_continuous_effects`; (b) control-change aura changes `perm.controller` to the enchanting player after `apply_continuous_effects`; (c) type-addition effect adds "Artifact" to a creature's type_line; (d) color-setting effect changes permanent's colors list

**Checkpoint**: `python -m pytest tests/rules/test_layers.py -v` passes; layers 1, 2, 4, 5 generate and apply effects correctly.

---

## Phase 8: User Story 6 — Attack and Block Constraints (Priority: P6)

**Goal**: Engine enforces Propaganda-style attack costs, must-attack requirements, goad, and cannot-block restrictions during legal action computation. New `AttackConstraint` and `BlockConstraint` models (added in Phase 2) are populated from oracle text scanning and enforced in `game.py`.

**Independent Test**: With a Propaganda-like permanent on the battlefield (oracle text `"creatures can't attack unless their controller pays {2}"`), the legal actions list should contain no `declare_attackers` actions if the player has 0 mana.

- [X] T032 [US6] In mtg_engine/api/routers/game.py (or a new helper module `mtg_engine/engine/constraints.py`), add `derive_combat_constraints(game_state: GameState) -> tuple[list[AttackConstraint], list[BlockConstraint]]` that scans oracle text of all battlefield permanents and returns: (a) `AttackConstraint(type="cost_to_attack", cost="{N}", affected_id="all")` for patterns like `"creatures can't attack unless.*pays? \{[^}]+\}"` or `"creatures attack each combat if able"`; (b) `BlockConstraint(type="cannot_block", affected_id=perm.id)` for permanents with oracle text `"can't block"`; (c) `AttackConstraint(type="goad", affected_id=perm.id, goad_controller=...)` for permanents with `"goad"` counter key matching pattern `"goad_by_"` on their counters dict
- [X] T033 [US6] In mtg_engine/api/routers/game.py legal actions computation (the section that adds `declare_attackers` actions), call `derive_combat_constraints(gs)` to get active constraints and filter the attackers list: for each potential attacker, check `AttackConstraint` entries — if `constraint_type == "cost_to_attack"` and the controller cannot pay the cost (use `can_pay_cost`), exclude that creature from legal attackers; if `constraint_type == "must_attack"` and the creature can attack, it should always be included even if other heuristics would skip it
- [X] T034 [US6] In mtg_engine/api/routers/game.py legal actions computation (the section that adds `declare_blockers` actions), apply `BlockConstraint` filtering: exclude any blocker whose permanent ID matches a `BlockConstraint(type="cannot_block")` entry; check goad constraints to exclude any blocker that is goaded (goaded creatures cannot block, CR 702.117b)
- [X] T035 [US6] In mtg_engine/engine/combat.py `declare_blockers()`, add a check: before recording a blocker, verify no `BlockConstraint(type="cannot_block")` in `game_state.block_constraints` matches `blocker.id`; raise `ValueError(f"{blocker.card.name} cannot block due to an active restriction")` if a match is found
- [X] T036 [US6] Add test cases to tests/rules/test_legal_actions.py: (a) permanent with Propaganda oracle text results in no attacker legal actions when player has 0 mana; (b) permanent with Propaganda oracle text allows attacker legal action when player has {2} available; (c) permanent with "can't block" in oracle text is excluded from blocker legal actions; (d) goaded creature (goad counter present) cannot be declared as a blocker

**Checkpoint**: `python -m pytest tests/rules/test_legal_actions.py -v` passes; Propaganda and can't-block constraints are enforced.

---

## Phase 9: User Story 7 — Copy Effects on the Stack (Priority: P7)

**Goal**: A copy spell action creates a new `StackObject` with `is_copy=True`. Copying resolves via the existing `resolve_top` path but skips the graveyard-placement step. Phase-skip flags prevent entire phases from executing.

**Independent Test**: Call `copy_spell_on_stack(gs, original_spell_id, new_targets)`, assert stack length increased by 1, the new object has `is_copy=True`, and resolving it applies effects without placing any card in a graveyard.

- [X] T037 [US7] In mtg_engine/engine/stack.py, add `copy_spell_on_stack(game_state: GameState, source_stack_id: str, new_targets: list[str] | None = None) -> GameState` that: finds the StackObject with matching ID, creates a copy using `model_copy(update={"id": str(uuid.uuid4()), "is_copy": True, "targets": new_targets or source_obj.targets})`, appends the copy to `game_state.stack`, and returns the updated game state
- [X] T038 [US7] In mtg_engine/engine/stack.py `resolve_top()`, after resolving the spell effect, in the section that moves the source card to graveyard, add a check: `if not stack_obj.is_copy:` before executing the graveyard move (copies of spells cease to exist, CR 706.10, so they are simply discarded without zone change)
- [X] T039 [US7] In mtg_engine/engine/turn_manager.py `advance_step()`, after computing `next_phase`, check `game_state.phase_skip_flags.get(next_phase.value, False)`: if `True`, advance one more step (call recursively or loop) to skip the entire phase; ensure skipping is limited to one phase at a time (no infinite loop) and clear the consumed skip flag
- [X] T040 [US7] In mtg_engine/engine/turn_manager.py `_advance_turn()`, add `game_state.phase_skip_flags.clear()` to reset phase skip flags at the end of each turn
- [X] T041 [US7] In mtg_engine/models/actions.py, add `CopySpellRequest` Pydantic model with fields: `game_id: str`, `player_name: str`, `target_stack_id: str` (the stack object to copy), `new_targets: list[str] = []`
- [X] T042 [US7] In mtg_engine/api/routers/game.py, add `POST /game/{game_id}/copy-spell` endpoint that accepts `CopySpellRequest`, validates the target stack object exists and the requesting player has priority, calls `copy_spell_on_stack()`, saves the updated game state, and returns the standard `_ok(gs)` response
- [X] T043 [US7] Add test cases to tests/rules/test_stack.py: (a) `copy_spell_on_stack` creates a new stack object with `is_copy=True` and the correct targets; (b) resolving a copy does not place any card in the graveyard; (c) original spell resolves and goes to graveyard normally; (d) phase skip flag for "combat" causes `advance_step` to skip the entire COMBAT phase

**Checkpoint**: `python -m pytest tests/rules/test_stack.py -v` passes; copy spells work correctly and phase skipping functions.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Verify integration, clean up any inconsistencies introduced across phases, confirm no regressions.

- [X] T044 Run full test suite `python -m pytest tests/ -v` and fix any regressions introduced by Phase 2–9 changes (model field additions, combat.py changes, mana.py signature changes)
- [X] T045 [P] Update CLAUDE.md via `.specify/scripts/bash/update-agent-context.sh claude` to reflect any new modules or patterns added by this feature
- [X] T046 [P] In mtg_engine/engine/turn_manager.py `begin_step()` cleanup section, verify `game_state.attack_constraints.clear()` and `game_state.block_constraints.clear()` are called to remove per-turn constraints (Propaganda constraints persist but goad constraints are per-turn)
- [X] T047 Validate quickstart.md integration scenarios manually by running the Python snippets against the updated engine and confirming each assertion passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US3–US7 (US1/US2 can start without Phase 2)
- **US1 (Phase 3)**: Depends on Setup only (zones.py change is independent)
- **US2 (Phase 4)**: Depends on Setup only (triggers.py + combat.py changes are independent)
- **US3 (Phase 5)**: Depends on Foundational (Phase 2) — needs player_life param wired through
- **US4 (Phase 6)**: Depends on Foundational (Phase 2) — uses `prevention_effects` list on GameState
- **US5 (Phase 7)**: Depends on Foundational (Phase 2) — uses `copy_of_permanent_id` on Permanent
- **US6 (Phase 8)**: Depends on Foundational (Phase 2) — uses AttackConstraint/BlockConstraint models
- **US7 (Phase 9)**: Depends on Foundational (Phase 2) — uses `phase_skip_flags` on GameState
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependencies

- **US1**: Fully independent — only modifies `zones.py`
- **US2**: Fully independent — only modifies `triggers.py` and `combat.py`
- **US3**: Depends on Foundational only
- **US4**: Depends on Foundational; US4 integration with Fog also touches `combat.py` — coordinate with US2 if implementing in parallel
- **US5**: Depends on Foundational only
- **US6**: Depends on Foundational; touches `game.py` legal actions — coordinate with US4 if parallel
- **US7**: Depends on Foundational; touches `stack.py` and `turn_manager.py`

### Within Each User Story

- Model/field additions before service logic
- Service logic (engine functions) before API wiring
- API wiring before test verification

### Parallel Opportunities

- T002 and T003 (Phase 1 reads) can run in parallel
- T004, T005, T006 (new model classes in Phase 2) can run in parallel — all in same file but independent class definitions
- T026, T027, T028, T029 (layer generators in US5) — T028 and T029 are marked [P] as they touch different oracle pattern branches
- US1 and US2 can be implemented fully in parallel (different files)
- US5 and US6 can be implemented in parallel after Phase 2

---

## Parallel Example: User Story 5 (Layer System)

```bash
# T028 and T029 can run in parallel (different oracle pattern branches in same function):
Task T028: "Add Layer 4 type-change effect generator in layers.py"
Task T029: "Add Layer 5 color-change effect generator in layers.py"

# T026 and T027 must be sequential (layer 1 copy depends on copy_of_permanent_id from T008):
Task T026: "Add Layer 1 copy effect generator" (after T008)
Task T027: "Add Layer 2 control-change effect generator" (can start independently)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup verification
2. Complete US1 (Phase 3): Fix deck-out SBA — only `zones.py` change needed
3. **STOP and VALIDATE**: `python -m pytest tests/rules/test_sba.py -v`
4. Deck-out games now end correctly

### Incremental Delivery

1. Phase 1 (Setup) + US1 → Deck-out works ✓
2. Phase 2 (Foundational) → Models ready for US3–US7
3. US2 → Damage triggers work ✓
4. US3 → Hybrid/Phyrexian mana valid ✓
5. US4 → Fog/prevention works ✓
6. US5 → Full layer system ✓
7. US6 → Propaganda/goad constraints ✓
8. US7 → Copy spells + phase skip ✓
9. Phase 10 (Polish) → Full suite green ✓

---

## Notes

- [P] tasks = different files or independent branches in the same function, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 can be implemented immediately (no model changes required)
- US3–US7 require Phase 2 (Foundational) to complete first
- All changes are **additive** — no existing function signatures broken except mana.py `can_pay_cost` gaining an optional `player_life` parameter (backward-compatible)
- The `combat.py` file is touched by US2 (damage triggers), US4 (fog check), and US6 (block constraint check) — implement in that order to avoid merge conflicts

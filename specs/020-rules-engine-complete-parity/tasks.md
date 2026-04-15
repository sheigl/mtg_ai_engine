# Tasks: Rules Engine Complete Parity (020)

**Input**: Design documents from `/specs/020-rules-engine-complete-parity/`
**Prerequisites**: plan.md ✓, spec.md ✓, data-model.md ✓, contracts/api-changes.md ✓
**Tests**: Included — plan.md defines a full `tests/test_020/` suite mirroring the `tests/test_019/` pattern.

**Organization**: Tasks grouped by phase per plan.md, then by user story within each phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable — different files, no dependencies on incomplete tasks
- **[Story]**: User story label (US1–US30)
- All paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Create test directory scaffolding so all test files have a home.

- [x] T001 Create `tests/test_020/__init__.py` (empty, following tests/test_019/ pattern)

**Checkpoint**: Test directory exists; `python -m pytest tests/test_020/ -v` reports "no tests collected" (not an error)

---

## Phase 2: Foundational — Data Model Extensions

**Purpose**: Add all new Pydantic fields and models required by US1–US30. All new fields carry defaults so existing tests are unaffected.

**⚠️ CRITICAL**: All user story phases depend on these model changes. Complete before any implementation phase.

- [ ] T002 Add `DamageModifier` model and `ManaPoolPersistence` model to `mtg_engine/models/game.py` (new top-level Pydantic classes per data-model.md)
- [ ] T003 [P] Add new fields to `Card`, `StackObject`, `Permanent`, `ManaPool`, `PlayerState`, and `GameState` in `mtg_engine/models/game.py` — all fields listed in data-model.md with their specified defaults
- [ ] T004 [P] Add `face_index`, `fuse`, `as_face_down`, `foretell`, `cast_foretold`, `mutate_target_id`, `mutate_on_top` fields to `CastRequest` in `mtg_engine/models/actions.py`; add new `LegalAction` `action_type` string literals (`"crew"`, `"turn_face_up"`, `"foretell"`, `"cast_foretold"`, `"cast_adventure"`, `"activate_mana_ability"`, `"mutate"`, `"cast_split_left"`, `"cast_split_right"`, `"cast_fuse"`, `"play_mdfc_land"`)
- [ ] T005 [P] Add `CrewRequest` and `TurnFaceUpRequest` request models to `mtg_engine/models/actions.py` per contracts/api-changes.md
- [ ] T006 [P] Add `type_operation`, `remove_abilities`, `grant_abilities`, `switch_pt` fields to `ContinuousEffect` in `mtg_engine/engine/layers.py`

**Checkpoint**: `python -m pytest tests/ -v` — all 447 existing tests pass with no regressions

---

## Phase 3: User Story 1 — Cleanup Step (P1-CRITICAL) 🎯

**Goal**: Implement CR 514 cleanup step: discard to hand size, remove damage, expire "until end of turn" effects, grant priority if SBAs/triggers fire.

**Independent Test**: End a turn where the active player has 9 cards (max 7). Verify `pending_discard_choice` is set for 2 cards. After resolving, verify `damage_marked=0` on all permanents and `power_bonus=0` on all pumped permanents.

- [ ] T007 [US1] Implement `process_cleanup_step(game_state: GameState) -> GameState` in `mtg_engine/engine/turn_manager.py`: set `pending_discard_choice` when hand > `max_hand_size`; iterate battlefield resetting `damage_marked=0`; reset `power_bonus`, `toughness_bonus` for effects where `power_bonus_expires == "end_of_turn"`; clear `crewed_until_end_of_turn`; call `check_sba()` and `check_triggers()` and loop if anything fired; wire after end-step transition
- [ ] T008 [P] [US1] Write `tests/test_020/test_020_cleanup_step.py`: test discard-to-hand-size (scenarios 1, 4); test damage removal (scenario 2); test "until end of turn" expiry (scenario 3); test SBA-during-cleanup loop (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_cleanup_step.py -v` passes

---

## Phase 4: User Stories 2 & 20 — Targeting Enforcement + Full Protection (P1-CRITICAL / P1-HIGH)

**Goal**: Enforce hexproof, shroud, protection (DEBT) on all targeting endpoints; handle protection SBAs for Auras/Equipment.

**Independent Test**: Put a hexproof creature controlled by Player B on the battlefield. Have Player A cast Murder targeting it — verify `400 ILLEGAL_TARGET_HEXPROOF`. Have Player B self-target — verify legal.

- [ ] T009 [US2] Implement `_validate_targets(game_state, targets, source_card, controller) -> list[str]` in `mtg_engine/api/routers/game.py`: hexproof check (opponent-controlled source only); shroud check (any controller); protection check (color, type, CMC matching per CR 702.16); return error strings for illegal targets
- [ ] T010 [US2] Wire `_validate_targets()` into `/cast`, `/activate`, and `/put_trigger` endpoint handlers in `mtg_engine/api/routers/game.py`; raise `400` with error codes from contracts/api-changes.md (`ILLEGAL_TARGET_HEXPROOF`, `ILLEGAL_TARGET_SHROUD`, `ILLEGAL_TARGET_PROTECTION`)
- [ ] T011 [US20] Add protection SBA checks to `mtg_engine/engine/sba.py`: if an Aura is attached to a permanent with protection from a matching quality → put Aura to graveyard; if an Equipment is attached → unattach (equipment stays on battlefield); handle "protection from everything"
- [ ] T012 [P] [US2] Write `tests/test_020/test_020_targeting_enforcement.py`: test hexproof (scenarios 1–2); test shroud (scenario 3); test protection from red (scenarios 4–5); test protection from creatures (scenario 6)
- [ ] T013 [P] [US20] Write `tests/test_020/test_020_protection_full.py`: test Aura falling off on SBA (scenario 1); test Equipment unattaching on SBA (scenario 2); test protection-from-creatures targeting (scenario 3); test protection-from-everything damage prevention (scenario 4); test Aura falling off when protection gained after attachment (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_targeting_enforcement.py tests/test_020/test_020_protection_full.py -v` passes

---

## Phase 5: User Stories 3 & 21 — Mana Abilities Bypass Stack + Split Second (P1-CRITICAL / P1-HIGH)

**Goal**: Mana abilities resolve immediately; non-mana abilities blocked while split second is on the stack.

**Independent Test**: With a split second spell on the stack, tap a Forest for {G} — mana added immediately. Attempt to activate a non-mana ability — rejected.

- [ ] T014 [US3] Implement `is_mana_ability(oracle_text: str, is_loyalty: bool = False) -> bool` and `resolve_mana_ability(game_state, permanent_id, ability_index) -> GameState` in `mtg_engine/engine/mana.py`; pattern: produces mana AND no "target" in text AND not loyalty ability
- [ ] T015 [US3] In `/activate` endpoint in `mtg_engine/api/routers/game.py`: check `is_mana_ability()` before `stack.activate_ability()`; if True call `resolve_mana_ability()` directly; update `_compute_legal_actions()` to tag mana ability actions as `action_type="activate_mana_ability"`
- [ ] T016 [US21] In `mtg_engine/engine/stack.py` split-second enforcement: block non-mana activated abilities when `_has_split_second()` is True; exempt `action_type="activate_mana_ability"`; raise `400 SPLIT_SECOND_BLOCKS_ABILITY` for blocked activations; confirm triggered abilities still queue normally
- [ ] T017 [P] [US3] Write `tests/test_020/test_020_mana_abilities.py`: test immediate resolution (scenario 1); test mana ability during split second (scenario 2); test non-mana ability blocked during split second (scenario 3); test mana ability with target uses stack (scenario 5)
- [ ] T018 [P] [US21] Write `tests/test_020/test_020_split_second_abilities.py`: test non-mana ability blocked (scenario 1); test mana ability still legal (scenario 2); test spell cast blocked (scenario 3); test triggers unaffected (scenario 4); test abilities legal after split second resolves (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_mana_abilities.py tests/test_020/test_020_split_second_abilities.py -v` passes

---

## Phase 6: User Story 4 — Split Cards, MDFCs, and Aftermath (P1-CRITICAL)

**Goal**: Enable face selection when casting multi-face cards; support fuse; support aftermath graveyard cast; support MDFC land play.

**Independent Test**: Cast "Fire // Ice" split card with `face_index=0` — stack object uses Fire's cost/effect. Cast with `face_index=1` — uses Ice's.

- [ ] T019 [US4] In `cast_spell()` in `mtg_engine/engine/stack.py`: when `card.faces` is set and `len(card.faces) > 1`, read `face_index` from request and populate stack object fields from selected `CardFace` (name, mana_cost, type_line, oracle_text, power, toughness); for `fuse=True` merge both faces; for aftermath `face_index=1` validate card is in graveyard and mark `StackObject` for exile on resolution; raise error codes from contracts/api-changes.md
- [ ] T020 [US4] In `_compute_legal_actions()` in `mtg_engine/engine/stack.py` (or turn_manager): for split cards emit `cast_split_left` and `cast_split_right` actions; emit `cast_fuse` if card has fuse; for MDFCs with land back face emit `play_mdfc_land`; in play-land handler in `mtg_engine/api/routers/game.py` handle `face_index=1` for MDFC land play
- [ ] T021 [P] [US4] Write `tests/test_020/test_020_split_cards.py`: test face_index=0 (scenario 1); test face_index=1 (scenario 2); test fuse (scenario 3); test MDFC land play (scenario 4); test aftermath graveyard cast with exile on resolution (scenario 5); test legal actions include both faces (scenario 6)

**Checkpoint**: `python -m pytest tests/test_020/test_020_split_cards.py -v` passes

---

## Phase 7: User Story 5 — ETB Replacement Effects (P1-CRITICAL)

**Goal**: Apply battlefield replacement effects to permanents entering the battlefield (enters tapped, counter doubling).

**Independent Test**: Thalia, Heretic Cathar on battlefield. Play nonbasic land → enters tapped. Play basic land → enters untapped.

- [ ] T022 [US5] Implement `apply_etb_replacements(game_state, permanent, controller) -> Permanent` in `mtg_engine/engine/replacement.py`: scan battlefield for "enters tapped" patterns (nonbasic lands, opponent creatures, all permanents); scan for counter-multiply patterns (Doubling Season); use `ETBReplacementEffect` dataclass internally; handle multiple replacement effect ordering (CR 616.1)
- [ ] T023 [US5] Call `apply_etb_replacements()` from `put_permanent_onto_battlefield()` in `mtg_engine/engine/zones.py` before adding permanent to battlefield list
- [ ] T024 [P] [US5] Write `tests/test_020/test_020_etb_replacements.py`: test nonbasic land enters tapped (scenario 1); test opponent creature enters tapped (scenario 2); test counter doubling (scenario 3); test no effects → default state (scenario 4); test multiple replacement effect ordering (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_etb_replacements.py -v` passes

---

## Phase 8: User Story 6 — Extended Trigger Pattern Recognition (P1-CRITICAL)

**Goal**: Add event-based trigger dispatch covering lifegain, landfall, death, draw, sacrifice, counter-spell, enchantment-enter, and end-step triggers.

**Independent Test**: Permanent with "Whenever you gain life, put a +1/+1 counter" on battlefield. Gain 3 life. Verify 3 triggers on stack.

- [ ] T025 [US6] Implement `check_event_triggers(game_state, event_type, event_data) -> GameState` in `mtg_engine/engine/triggers.py`: define event types `"gain_life"`, `"land_enter"`, `"creature_dies"`, `"draw_card"`, `"sacrifice"`, `"counter_spell"`, `"enchantment_enter"`, `"end_step"`; add regex patterns matching each oracle_text condition; preserve all existing patterns (additive only)
- [ ] T026 [US6] Wire event calls into: `gain_life()`, `move_permanent_to_zone()` (death/sacrifice/enchant-enter/land-enter), `draw_card()`, and end-step phase transition hook in `mtg_engine/engine/turn_manager.py` and `mtg_engine/engine/zones.py`
- [ ] T027 [P] [US6] Write `tests/test_020/test_020_trigger_patterns.py`: test lifegain trigger (scenario 1); test landfall trigger (scenario 2); test creature-dies trigger (scenario 3); test draw trigger (scenario 4); test sacrifice trigger (scenario 5); test at-end-step trigger (scenario 6)

**Checkpoint**: `python -m pytest tests/test_020/test_020_trigger_patterns.py -v` passes

---

## Phase 9: User Stories 7 & 8 — SBA Corrections (P1-HIGH)

**Goal**: Legend rule prompts player choice; toughness-0 bypasses destruction pipeline (no regeneration, no indestructible).

**Independent Test (US7)**: Control two legends with same name → `pending_legend_choice` set. Submit choice → unchosen goes to graveyard.
**Independent Test (US8)**: Indestructible creature reduced to 0 toughness → goes to graveyard (indestructible does not prevent).

- [ ] T028 [US7] In `mtg_engine/engine/sba.py`: replace auto-keep-newest legend logic with `pending_legend_choice` dict on `GameState`; format `{"player": str, "permanent_ids": [str], "legend_name": str}`; add `/choice` handler for `"legend_choice"` in `mtg_engine/api/routers/game.py` that keeps chosen permanent and graveards the rest
- [ ] T029 [US8] In `mtg_engine/engine/sba.py`: add `_put_to_graveyard_sba(permanent, game_state)` function that moves permanent to graveyard without invoking `_destroy_permanent()`; route toughness-0 SBA checks through this non-destruction path; confirm regeneration shields and indestructible are NOT consulted
- [ ] T030 [P] [US7] Write `tests/test_020/test_020_legend_rule_choice.py`: test pending_legend_choice set on duplicate legend (scenario 1); test choice resolves correctly (scenario 2); test three legends → keep one (scenario 3); test two players, one each → no rule (scenario 4); test choosing older legend keeps it (scenario 5)
- [ ] T031 [P] [US8] Write `tests/test_020/test_020_toughness_zero.py`: test non-destruction path (scenario 1); test indestructible still dies (scenario 2); test regeneration shield NOT consumed (scenario 3); test protection from source color still dies (scenario 4); test layer 7c reduction triggers SBA (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_legend_rule_choice.py tests/test_020/test_020_toughness_zero.py -v` passes

---

## Phase 10: User Stories 9 & 10 — Combat Improvements (P1-HIGH)

**Goal**: Correct blocker damage assignment order; support additional combat phases.

**Independent Test (US9)**: 5/5 vs [2/2, 3/3] in order — 2 damage to 2/2 then 3 to 3/3. Both die.
**Independent Test (US10)**: Effect grants `additional_combat_phases += 1`. Verify new combat phase begins after postcombat main.

- [ ] T032 [US9] In `assign_combat_damage()` in `mtg_engine/engine/combat.py`: when attacker has multiple blockers, assign damage to blockers in `blocker_order` sequence, requiring lethal damage to each before moving to next; handle deathtouch (1 = lethal); handle trample — excess after all blockers assigned lethal goes through; add `/choice` handler `"blocker_damage_order"` for manual assignment validation
- [ ] T033 [US10] In `mtg_engine/engine/turn_manager.py`: after combat-to-postcombat-main transition, check `game_state.additional_combat_phases > 0`; if so, decrement and schedule full combat phase (beginning of combat → end of combat steps) followed by another postcombat main phase; ensure "beginning of combat" triggers fire for each additional combat
- [ ] T034 [P] [US9] Write `tests/test_020/test_020_blocker_damage_order.py`: test lethal-first order (scenario 1); test specific 5/5 vs 2/2+3/3 (scenario 2); test insufficient power to reach second blocker (scenario 3); test deathtouch + multiple blockers (scenario 4); test trample through after lethal (scenario 5)
- [ ] T035 [P] [US10] Write `tests/test_020/test_020_additional_combat.py`: test additional combat phase inserted (scenario 1); test creatures can attack again (scenario 2); test two additional combats (scenario 3); test steps proceed even with no attackers (scenario 4); test beginning-of-combat triggers fire again (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_blocker_damage_order.py tests/test_020/test_020_additional_combat.py -v` passes

---

## Phase 11: User Stories 11 & 19 — Step Skipping + Mana Persistence (P1-HIGH)

**Goal**: Skip individual steps (not whole phases) via `step_skip_flags`; preserve mana across phase transitions per `mana_persistence`.

**Independent Test (US11)**: `step_skip_flags["draw"] = True` → untap and upkeep occur, draw step skipped.
**Independent Test (US19)**: Player has "green mana doesn't empty" — add 5 {G}. Advance phase. {G} remains.

- [ ] T036 [US11] In `mtg_engine/engine/turn_manager.py`: before entering each step, check `game_state.step_skip_flags.get(step_name)`; if True skip the step (no priority granted, no triggers); for one-time skips clear the flag after skipping; ensure `phase_skip_flags` (phase-level) takes priority over step-level skips
- [ ] T037 [US19] In the mana-emptying function in `mtg_engine/engine/mana.py` and/or `turn_manager.py`: check `player.mana_persistence.colors`; skip emptying those colors; if `convert_to_colorless=True` convert colored mana to colorless instead of emptying; rebuild `mana_persistence` from battlefield permanents with "mana doesn't empty" patterns at each transition
- [ ] T038 [P] [US11] Write `tests/test_020/test_020_step_skip.py`: test draw step skipped, untap/upkeep occur (scenario 1); test untap skip (scenario 2); test phase-level skip overrides step skip (scenario 3); test no priority granted during skipped step (scenario 4); test one-time skip clears after use (scenario 5)
- [ ] T039 [P] [US19] Write `tests/test_020/test_020_mana_persistence.py`: test green mana preserved, others empty (scenario 1); test all mana preserved (scenario 2); test colorless conversion (scenario 3); test normal empty when no persistence (scenario 4); test persistence removed mid-turn (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_step_skip.py tests/test_020/test_020_mana_persistence.py -v` passes

---

## Phase 12: User Stories 12 & 13 — Ward Enforcement + Kicker Resolution (P1-HIGH)

**Goal**: Ward triggers when opponent targets ward permanent; kicker effects applied at resolution.

**Independent Test (US12)**: Ward {2} creature targeted by opponent → `pending_ward_payment`. Pay → spell continues. Decline → spell countered.
**Independent Test (US13)**: Kicked spell with `kicker_paid=True` → kicked effect applied, not base effect.

- [ ] T040 [US12] In `mtg_engine/engine/stack.py`: replace `_ward()` stub with full ward trigger flow — when `_validate_targets()` finds a ward permanent targeted by an opponent, queue ward trigger on stack; on ward trigger resolution set `pending_ward_payment` on `GameState`; add `/choice` handler `"ward_payment"` in `mtg_engine/api/routers/game.py` — if paid, continue stack; if declined, counter the targeting spell/ability; parse ward cost from oracle_text pattern `r"Ward (\{[^}]+\})"`
- [ ] T041 [US13] In `resolve_top()` in `mtg_engine/engine/stack.py`: when `stack_obj.kicker_paid=True`, parse kicked effect from oracle_text (look for "If this spell was kicked" or "If [it] was kicked" clause); apply kicked effect instead of or in addition to base effect; for multikicker (`kicker_count > 0`), apply N times; if a kicked copy retains `kicker_paid=True`, apply kicked effect on copy resolution too
- [ ] T042 [P] [US12] Write `tests/test_020/test_020_ward.py`: test pending_ward_payment set (scenario 1); test payment allows spell (scenario 2); test decline counters spell (scenario 3); test ward doesn't trigger for controller's own spells (scenario 4); test non-mana ward cost (scenario 5)
- [ ] T043 [P] [US13] Write `tests/test_020/test_020_kicker_resolution.py`: test kicked effect applied (scenario 1); test unkicked base effect (scenario 2); test multikicker N applications (scenario 3); test kicked token count (scenario 4); test kicked copy retains kicked status (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_ward.py tests/test_020/test_020_kicker_resolution.py -v` passes

---

## Phase 13: User Stories 14, 22 & 28 — Damage Doublers + Type Layers + P/T Switching (P1-HIGH)

**Goal**: Damage modifier pipeline; type overwrite layer (Blood Moon); P/T switching in layer 7d.

**Independent Test (US14)**: Dictate of the Twin Gods on battlefield. Deal 3 damage → 6 dealt. Two doublers → 12.
**Independent Test (US22)**: Blood Moon on battlefield → nonbasic lands become Mountains with only {T}: {R}.
**Independent Test (US28)**: 2/5 creature with P/T switch effect → becomes 5/2. +2/+0 then switch → 5/4.

- [ ] T044 [US14] Implement `apply_damage_modifiers(game_state, source, target, amount, is_combat) -> int` in `mtg_engine/engine/replacement.py`: iterate `game_state.damage_modifiers` in timestamp order applying multipliers; filter by `applies_to` field; call before damage prevention in all damage paths (combat, spell, ability) in `combat.py` and `stack.py`; register/unregister `DamageModifier` entries when permanents with doubling/tripling static abilities ETB/leave
- [ ] T045 [US22] In `apply_continuous_effects()` in `mtg_engine/engine/layers.py`: extend layer 4 to handle `type_operation="overwrite"` — replace all subtypes with the overwrite type; in layer 6, process `remove_abilities=True` by clearing non-intrinsic abilities; then apply `grant_abilities` list (e.g. `"{T}: Add {R}"`); apply effects in timestamp order within layer 4
- [ ] T046 [US28] In layer 7d processing in `mtg_engine/engine/layers.py`: when a `ContinuousEffect` has `switch_pt=True`, swap the effective power and toughness after all other layer 7 modifications (7a–7c applied first); multiple switch effects cancel out (even number = no swap)
- [ ] T047 [P] [US14] Write `tests/test_020/test_020_damage_doublers.py`: test single doubler (scenario 1); test controller-only tripler (scenario 2); test two doublers = 4x (scenario 3); test doubler + prevention shield interaction (scenario 4); test combat-only doubler doesn't apply to non-combat damage (scenario 5)
- [ ] T048 [P] [US22] Write `tests/test_020/test_020_type_layers.py`: test Blood Moon overwrites nonbasic subtypes (scenario 1); test nonbasic loses original ability gains {T}:{R} (scenario 2); test additive type change (scenario 3); test Blood Moon removal restores original (scenario 4); test timestamp ordering (scenario 5)
- [ ] T049 [P] [US28] Write `tests/test_020/test_020_pt_switching.py`: test 2/5 becomes 5/2 (scenario 1); test +2/+0 then switch → 5/4 (scenario 2); test two switches cancel (scenario 3); test switched toughness used for SBA check (scenario 4)

**Checkpoint**: `python -m pytest tests/test_020/test_020_damage_doublers.py tests/test_020/test_020_type_layers.py tests/test_020/test_020_pt_switching.py -v` passes

---

## Phase 14: User Stories 15, 16 & 17 — Phasing, Vehicles, and Morph (P1-HIGH)

**Goal**: Phase permanents in/out during untap step; crew vehicles; cast morph face-down and turn face-up.

**Independent Test (US15)**: Phase out creature + Aura. Both excluded from battlefield queries. Next untap → both phase in, Aura still attached.
**Independent Test (US16)**: Vehicle (crew 3) + two creatures with power 4 total → vehicle becomes artifact creature until cleanup.
**Independent Test (US17)**: Cast morph face-down for {3} → 2/2 colorless. Pay morph cost → full creature restored.

- [ ] T050 [US15] In untap step handler in `mtg_engine/engine/turn_manager.py`: before untapping, iterate battlefield — phase in all `phased_out=True` permanents (non-tokens; tokens cease to exist); phase out all `has_phasing=True` permanents and their attached Auras/Equipment (indirect phasing via `attached_to` relationship); implement `get_active_battlefield(game_state) -> list[Permanent]` helper that filters `phased_out=True` permanents; use this helper throughout combat, targeting, SBA, and trigger code
- [ ] T051 [US16] Add `POST /game/{game_id}/crew` endpoint to `mtg_engine/api/routers/game.py`: validate vehicle is on battlefield and not already creature; validate creature IDs are untapped, no summoning sickness, total power >= crew cost; tap crew creatures; set `crewed_until_end_of_turn=True` and add "Creature" to vehicle type_line; require main phase with empty stack (sorcery speed); return errors from contracts/api-changes.md; add `"crew"` legal action to `_compute_legal_actions()`
- [ ] T052 [US17] In `cast_spell()` in `mtg_engine/engine/stack.py`: when `as_face_down=True`, validate card has morph/megamorph; set stack object to face-down 2/2 colorless with no name/abilities; `permanent.is_face_down=True` on ETB; add `POST /game/{game_id}/turn_face_up` endpoint in `mtg_engine/api/routers/game.py`: validate face-down, controller, can pay morph cost; pay cost; set `is_face_down=False`; restore printed characteristics; if megamorph add +1/+1 counter; fire "turned face up" triggers; this is a special action (no stack); add `"turn_face_up"` legal action
- [ ] T053 [P] [US15] Write `tests/test_020/test_020_phasing.py`: test phased-out excluded from battlefield (scenario 1); test Aura phases out with creature (scenario 2); test phases back in at untap (scenario 3); test token ceases to exist (scenario 4); test board wipe ignores phased-out (scenario 5); test phasing in is NOT an ETB (scenario 6)
- [ ] T054 [P] [US16] Write `tests/test_020/test_020_vehicles.py`: test crew success (scenario 1); test crewed vehicle can attack (scenario 2); test insufficient power rejected (scenario 3); test cleanup reverts vehicle (scenario 4); test crew legal action visible in main phase (scenario 5)
- [ ] T055 [P] [US17] Write `tests/test_020/test_020_morph.py`: test face-down is 2/2 colorless (scenario 1); test turn-face-up restores characteristics (scenario 2); test megamorph adds +1/+1 counter (scenario 3); test face-down revealed on zone change (scenario 4); test turn_face_up legal action available when payable (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_phasing.py tests/test_020/test_020_vehicles.py tests/test_020/test_020_morph.py -v` passes

---

## Phase 15: User Story 18 — Adventure Cards (P1-HIGH)

**Goal**: Cast adventure half from hand (exile on resolve); cast creature half from adventure-exile.

**Independent Test**: Cast Stomp (adventure) from hand → card exiled. Cast creature half from exile → enters battlefield normally.

- [ ] T056 [US18] In `cast_spell()` in `mtg_engine/engine/stack.py`: when `card.card_layout == "adventure"` and `face_index=1`, set `StackObject.is_adventure=True`; on adventure resolution in `resolve_top()`, exile card to `player.exile` and tag it as adventure-exiled (not graveyard); allow casting creature half (face_index=0) from adventure-exile; if adventure spell is countered, send to graveyard; in `_compute_legal_actions()` emit two separate actions for adventure cards in hand and one cast-from-exile action for adventure-exiled cards; add legal action type `"cast_adventure"`
- [ ] T057 [P] [US18] Write `tests/test_020/test_020_adventure.py`: test two legal actions from hand (scenario 1); test adventure resolves to exile (scenario 2); test creature cast from adventure-exile (scenario 3); test creature goes to graveyard on death (scenario 4); test countered adventure goes to graveyard (scenario 5)

**Checkpoint**: `python -m pytest tests/test_020/test_020_adventure.py -v` passes

---

## Phase 16: User Stories 26 & 27 — Fading and Echo (P3-LOW)

**Goal**: Fading sacrifices permanents when fade counters run out; echo prompts payment on second upkeep.

**Independent Test (US26)**: Permanent with "Fading 3" enters with 3 fade counters. After 3 upkeeps → sacrificed.
**Independent Test (US27)**: Echo creature entered this turn. Next upkeep → `pending_echo_payment`. Decline → sacrificed.

- [ ] T058 [US26] In upkeep processing in `mtg_engine/engine/turn_manager.py`: find permanents with fading keyword on the active player's battlefield; remove one fade counter (`counters["fade"] -= 1`); if `counters["fade"]` reaches 0, sacrifice the permanent via `move_permanent_to_zone()`; fading permanents enter with N fade counters (parse from oracle_text `r"Fading (\d+)"` in `put_permanent_onto_battlefield()` in `mtg_engine/engine/zones.py`)
- [ ] T059 [US27] In upkeep processing in `mtg_engine/engine/turn_manager.py`: find permanents with echo where `echo_paid=False` and `turn_entered_battlefield < current_turn`; set `pending_echo_payment` on `GameState`; add `/choice` handler `"echo_payment"` in `mtg_engine/api/routers/game.py` — if paid, set `echo_paid=True`; if declined or cannot pay, sacrifice the permanent; echo does not trigger again after payment
- [ ] T060 [P] [US26] Write `tests/test_020/test_020_fading.py`: test enters with N counters (scenario 1); test counter removed each upkeep (scenario 2); test sacrifice when counters reach 0 (scenario 3); test proliferate extends lifetime (scenario 4)
- [ ] T061 [P] [US27] Write `tests/test_020/test_020_echo.py`: test pending_echo_payment set (scenario 1); test payment allows survival (scenario 2); test decline sacrifices (scenario 3); test echo doesn't trigger again after payment (scenario 4)

**Checkpoint**: `python -m pytest tests/test_020/test_020_fading.py tests/test_020/test_020_echo.py -v` passes

---

## Phase 17: User Stories 23, 24, 25 — Snow Mana, Trample PW, Flanking (P2/P3)

**Goal**: Track snow mana for {S} costs; trample excess to planeswalker; flanking -1/-1 trigger.

**Independent Test (US23)**: Snow-Covered Forest taps → {G} flagged as snow. Pay {S} with snow mana → succeeds. Pay {S} with non-snow → rejected.
**Independent Test (US24)**: 6/6 trampler attacks planeswalker; blocked by 2/2 → 2 to blocker, 4 to planeswalker.
**Independent Test (US25)**: Flanker blocked by non-flanker → -1/-1 trigger fires on blocker.

- [ ] T062 [US23] In `mtg_engine/engine/mana.py`: when a snow permanent produces mana, increment `mana_pool.snow_by_color[color] += 1` and `mana_pool.snow += 1`; in `can_pay_cost()` validate `{S}` against `snow_by_color` (any color with snow > 0 satisfies it); decrement both color field and `snow_by_color[color]` on payment; write `tests/test_020/test_020_snow_mana.py` covering all 4 acceptance scenarios
- [ ] T063 [US24] In `assign_combat_damage()` in `mtg_engine/engine/combat.py`: when attacker has trample AND the attack is targeting a planeswalker, route excess damage (beyond lethal to all blockers) to the planeswalker (decrement loyalty counters), not the defending player; write `tests/test_020/test_020_trample_planeswalker.py` covering all 4 acceptance scenarios
- [ ] T064 [US25] In `declare_blockers()` processing in `mtg_engine/engine/combat.py`: for each attacking creature with flanking keyword, fire a -1/-1 trigger against each blocking creature that does NOT have flanking; multiple flanking instances trigger separately; in `mtg_engine/engine/triggers.py` add flanking trigger pattern; write `tests/test_020/test_020_flanking.py` covering all 4 acceptance scenarios

**Checkpoint**: `python -m pytest tests/test_020/test_020_snow_mana.py tests/test_020/test_020_trample_planeswalker.py tests/test_020/test_020_flanking.py -v` passes

---

## Phase 18: User Stories 29 & 30 — Foretell and Mutate (P2-MEDIUM)

**Goal**: Foretell exiles card face-down for {2}; foretold card castable at foretell cost on later turns. Mutate merges creatures into pile.

**Independent Test (US29)**: Foretell card for {2} → exiled face-down in `foretold_cards`. Cast from exile on later turn → foretell cost used.
**Independent Test (US30)**: Mutate onto non-Human → permanent gains top card stats + all abilities from pile. "Whenever mutates" trigger fires.

- [ ] T065 [US29] Add `POST /game/{game_id}/foretell` endpoint in `mtg_engine/api/routers/game.py`: validate card in hand, has foretell keyword, is player's turn, can pay {2}; deduct {2}, move card to `player.foretold_cards` as face-down; in `cast_spell()` handler for `cast_foretold=True`: validate card is foretold, not foretold this turn, pay foretell cost; add `"foretell"` and `"cast_foretold"` legal actions to `_compute_legal_actions()`; write `tests/test_020/test_020_foretell.py` covering all 5 acceptance scenarios
- [ ] T066 [US30] In `cast_spell()` in `mtg_engine/engine/stack.py`: when `mutate_target_id` is set, validate target is non-Human creature controlled by caster; on resolution in `resolve_top()`, merge mutating card into `target.mutated_cards` list (top or bottom per `mutate_on_top`); update permanent characteristics from top card; add all abilities from all cards in pile to the permanent; fire "whenever this creature mutates" triggers via `check_event_triggers()`; when merged creature dies, send all cards in `mutated_cards` plus base card to graveyard as separate cards; add `"mutate"` legal action; write `tests/test_020/test_020_mutate.py` covering all 5 acceptance scenarios

**Checkpoint**: `python -m pytest tests/test_020/test_020_foretell.py tests/test_020/test_020_mutate.py -v` passes

---

## Phase 19: Polish & Regression

**Purpose**: Wire cleanup step to vehicles (`crewed_until_end_of_turn` cleared in `process_cleanup_step()`), full regression run, and cross-cutting validation.

- [ ] T067 Confirm `process_cleanup_step()` clears `crewed_until_end_of_turn` and removes "Creature" from vehicle type_line; confirm phased-out permanents excluded in all relevant helper calls (`get_active_battlefield()` wired throughout) in `mtg_engine/engine/turn_manager.py`, `mtg_engine/engine/sba.py`, `mtg_engine/engine/triggers.py`, and `mtg_engine/engine/combat.py`
- [ ] T068 Run full regression suite (`python -m pytest tests/ -v`) and confirm all 447 pre-existing tests still pass alongside all new test_020 tests

**Checkpoint**: Zero regressions. All test_020 tests green.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → no deps
Phase 2 (Data Models) → depends on Phase 1; BLOCKS all implementation phases
Phase 3 (US1) → depends on Phase 2
Phase 4 (US2+US20) → depends on Phase 2
Phase 5 (US3+US21) → depends on Phase 2
Phase 6 (US4) → depends on Phase 2
Phase 7 (US5) → depends on Phase 2
Phase 8 (US6) → depends on Phase 2
Phase 9 (US7+US8) → depends on Phase 2; US20 SBA work may complement
Phase 10 (US9+US10) → depends on Phase 2; Phase 8 trigger patterns recommended first
Phase 11 (US11+US19) → depends on Phase 2; US19 depends on mana infra from Phase 5
Phase 12 (US12+US13) → depends on Phase 2; ward depends on targeting from Phase 4
Phase 13 (US14+US22+US28) → depends on Phase 2
Phase 14 (US15+US16+US17) → depends on Phase 8 (upkeep trigger infrastructure for phasing)
Phase 15 (US18) → depends on Phase 6 (split card face-index infrastructure)
Phase 16 (US26+US27) → depends on Phase 8 (upkeep trigger infrastructure)
Phase 17 (US23+US24+US25) → depends on Phase 2
Phase 18 (US29+US30) → depends on Phase 5 (mana ability/cast infra)
Phase 19 (Polish) → depends on all phases
```

### User Story Priority Groups (recommended order)

| Priority | Stories | After Phase 2 is complete |
|----------|---------|--------------------------|
| P1-CRITICAL | US1–US6 | Start immediately, can parallelize |
| P1-HIGH | US7–US22 | Start after P1-CRITICAL or in parallel |
| P2-MEDIUM | US23, US24, US29, US30 | After P1 work |
| P3-LOW | US25, US26, US27, US28 | Last |

### Parallel Opportunities per Phase

```bash
# Phase 2 — all 5 tasks touch different files/sections:
Task T002 (new model classes in game.py)
Task T003 (new fields on existing models in game.py) — coordinate with T002 ordering
Task T004 (actions.py new fields + action types)
Task T005 (actions.py new request models)
Task T006 (layers.py ContinuousEffect fields)

# Phase 4 — implementation and tests:
Task T009+T010 (targeting implementation)   ← sequential within phase
Task T011 (protection SBA)                  ← parallel with T009/T010
Task T012 (targeting tests)                 ← parallel after T009
Task T013 (protection tests)                ← parallel after T011

# Phases 3–18: each phase's [P]-marked test tasks can run with their [P]-marked impl tasks
```

---

## Implementation Strategy

### MVP Scope (P1-CRITICAL — US1–US6)

1. Complete Phase 1: Setup
2. Complete Phase 2: Data Models (CRITICAL)
3. Complete Phase 3: US1 (Cleanup Step)
4. Complete Phase 4: US2+US20 (Targeting)
5. Complete Phase 5: US3+US21 (Mana Abilities)
6. Complete Phase 6: US4 (Split Cards)
7. Complete Phase 7: US5 (ETB)
8. Complete Phase 8: US6 (Triggers)
9. **STOP and VALIDATE**: Run full suite, confirm zero regressions

### Incremental Delivery

- Each phase is independently testable via its dedicated test file(s)
- Commit after each phase passes its tests
- Run full regression suite (`python -m pytest tests/ -v`) before marking a phase complete
- Target: zero regressions against 447 pre-existing tests throughout

---
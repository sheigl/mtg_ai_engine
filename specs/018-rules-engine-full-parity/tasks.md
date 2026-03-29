---

description: "Task list for Full Rules Engine Parity (Feature 018)"
---

# Tasks: Full Rules Engine Parity

**Input**: Design documents from `/specs/018-rules-engine-full-parity/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md, contracts/

**Tests**: OPTIONAL - Only include test tasks if explicitly requested in the feature specification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below are absolute based on repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per implementation plan
- [X] T002 Initialize Python 3.11 project with existing dependencies (FastAPI, Pydantic v2, httpx, openai)
- [X] T003 [P] Configure linting and formatting tools (ruff, pytest)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Setup test framework and run existing test suite
- [X] T005 [P] Verify all 376 existing tests pass
- [X] T006 [P] Configure error handling and logging infrastructure
- [X] T007 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Spell Effects Actually Resolve (Priority: P1) 🎯 MVP

**Goal**: Implement 9 new spell effect patterns in `_apply_spell_effect()` to handle common spell effects beyond damage/pump/counter

**Independent Test**: Play a game where Player 1 casts Divination (draw 2 cards) — player's hand size should increase by 2. Cast Murder on a creature — creature should leave the battlefield. Cast Raise the Alarm (create tokens) — tokens should appear on the battlefield.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Test draw effect in tests/test_018_spell_effects.py
- [X] T011 [P] [US1] Test destroy effect in tests/test_018_spell_effects.py
- [X] T012 [P] [US1] Test exile effect in tests/test_018_spell_effects.py
- [X] T013 [P] [US1] Test bounce effect in tests/test_018_spell_effects.py
- [X] T014 [P] [US1] Test token creation effect in tests/test_018_spell_effects.py
- [X] T015 [P] [US1] Test gain life effect in tests/test_018_spell_effects.py
- [X] T016 [P] [US1] Test discard effect in tests/test_018_spell_effects.py
- [X] T017 [P] [US1] Test tutor effect in tests/test_018_spell_effects.py
- [X] T018 [P] [US1] Test counters effect in tests/test_018_spell_effects.py
- [X] T019 [P] [US1] Test scry effect in tests/test_018_spell_effects.py
- [X] T020 [P] [US1] Test surveil effect in tests/test_018_spell_effects.py

### Implementation for User Story 1

- [X] T021 [P] [US1] Add new fields to GameState in mtg_engine/models/game.py (pending_scry_choice, pending_surveil_choice, pending_tutor_choice, pending_discard_choice, pending_ward_payment, spells_cast_this_turn, spells_cast_last_turn)
- [X] T022 [P] [US1] Add new fields to StackObject in mtg_engine/models/game.py (x_value, kicker_paid, jump_start_discard_id)
- [X] T023 [P] [US1] Add new fields to Permanent in mtg_engine/models/game.py (unearthed, time_counters, foretold)
- [X] T024 [P] [US1] Add new fields to PlayerState in mtg_engine/models/game.py (suspended_cards, foretold_cards)
- [X] T025 [P] [US1] Add new fields to CastRequest in mtg_engine/models/actions.py (x_value, kicker_paid, jump_start_discard_id)
- [X] T026 [P] [US1] Add new fields to LegalAction in mtg_engine/models/actions.py (x_value, kicker_paid)
- [X] T027 [US1] Implement helper function `_draw_cards()` in mtg_engine/engine/stack.py
- [X] T028 [US1] Implement helper function `_destroy_permanent()` in mtg_engine/engine/stack.py
- [X] T029 [US1] Implement helper function `_exile_permanent()` in mtg_engine/engine/stack.py
- [X] T030 [US1] Implement helper function `_bounce_permanent()` in mtg_engine/engine/stack.py
- [X] T031 [US1] Implement helper function `_create_tokens()` in mtg_engine/engine/stack.py
- [X] T032 [US1] Implement helper function `_gain_life()` in mtg_engine/engine/stack.py
- [X] T033 [US1] Implement helper function `_discard_cards()` in mtg_engine/engine/stack.py
- [X] T034 [US1] Implement helper function `_tutor()` in mtg_engine/engine/stack.py
- [X] T035 [US1] Implement helper function `_add_counters()` in mtg_engine/engine/stack.py
- [X] T036 [US1] Implement helper function `_scry()` in mtg_engine/engine/stack.py
- [X] T037 [US1] Implement helper function `_surveil()` in mtg_engine/engine/stack.py
- [X] T038 [US1] Refactor `_apply_spell_effect()` in mtg_engine/engine/stack.py to use priority-ordered pattern list
- [X] T039 [US1] Add X value substitution logic to `_apply_spell_effect()`
- [X] T040 [US1] Update `_compute_legal_actions()` in mtg_engine/api/routers/game.py to handle new spell effects
- [X] T041 [US1] Add logging for unrecognized oracle text at DEBUG level
- [X] T042 [US1] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Targeting Rules Enforced (Priority: P2)

**Goal**: Implement hexproof, shroud, menace, ward, and protection targeting rules

**Independent Test**: Start a game with a Hexproof creature on the battlefield. Verify that no opponent spell actions list that creature as a valid target. Add a Shroud creature — verify neither player can target it. Send a Menace attacker — verify the declare_blockers validation rejects a single-blocker assignment.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [X] T043 [P] [US2] Test hexproof targeting in tests/test_018_targeting.py
- [X] T044 [P] [US2] Test shroud targeting in tests/test_018_targeting.py
- [X] T045 [P] [US2] Test menace blocking in tests/test_018_targeting.py
- [X] T046 [P] [US2] Test ward payment in tests/test_018_targeting.py
- [X] T047 [P] [US2] Test protection targeting in tests/test_018_targeting.py

### Implementation for User Story 2

- [X] T048 [P] [US2] Implement hexproof check in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T049 [P] [US2] Implement shroud check in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T050 [US2] Implement menace blocking validation in `declare_blockers()` in mtg_engine/engine/combat.py
- [X] T051 [US2] Implement ward cost payment logic in mtg_engine/engine/stack.py
- [X] T052 [US2] Implement protection targeting check in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T053 [US2] Update spell resolution to check protection before applying effects
- [X] T054 [US2] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 2 should be fully functional and testable independently

---

## Phase 5: User Story 3 - X Spells Cast for Variable Amounts (Priority: P3)

**Goal**: Allow X spells to be cast with different X values based on available mana

**Independent Test**: Load a game with Fireball in hand and 5 available mana. Verify that `_compute_legal_actions` returns multiple cast actions for Fireball with different X values. Cast Fireball with X=3 targeting a creature with 3 toughness — creature should die.

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [X] T055 [P] [US3] Test X spell variants in tests/test_018_x_spells.py
- [X] T056 [P] [US3] Test X value substitution in tests/test_018_x_spells.py

### Implementation for User Story 3

- [X] T057 [P] [US3] Implement X value calculation in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T058 [US3] Generate multiple cast actions for X spells with different X values
- [X] T059 [US3] Update CastRequest model to accept x_value
- [X] T060 [US3] Update spell resolution to use x_value from StackObject
- [X] T061 [US3] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 3 should be fully functional and testable independently

---

## Phase 6: User Story 4 - Modal Spells Apply Only Chosen Mode (Priority: P4)

**Goal**: Ensure modal spells only apply the chosen mode(s), not all modes simultaneously

**Independent Test**: Cast a charm spell choosing one mode. Verify only that mode's effect resolves, not all modes.

### Tests for User Story 4 (OPTIONAL - only if tests requested) ⚠️

- [X] T062 [P] [US4] Test single mode selection in tests/test_018_modal.py
- [X] T063 [P] [US4] Test multiple mode selection in tests/test_018_modal.py

### Implementation for User Story 4

- [X] T064 [P] [US4] Update `_apply_spell_effect()` to respect `modes_chosen` in mtg_engine/engine/stack.py
- [X] T065 [US4] Implement mode filtering logic for oracle text parsing
- [X] T066 [US4] Update `_compute_legal_actions()` to include mode choices in LegalAction
- [X] T067 [US4] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 4 should be fully functional and testable independently

---

## Phase 7: User Story 5 - Cascade Trigger Works (Priority: P5)

**Goal**: Implement cascade mechanic for spells like Shardless Agent

**Independent Test**: Cast a cascade spell and observe that `cascade_choice` legal action appears with a revealed card; choose to cast or exile it.

### Tests for User Story 5 (OPTIONAL - only if tests requested) ⚠️

- [X] T068 [P] [US5] Test cascade card selection in tests/test_018_cascade.py
- [X] T069 [P] [US5] Test cascade choice action in tests/test_018_cascade.py
- [X] T070 [P] [US5] Test cascade library placement in tests/test_018_cascade.py

### Implementation for User Story 5

- [X] T071 [P] [US5] Implement cascade card selection logic in mtg_engine/engine/stack.py
- [X] T072 [US5] Implement cascade_choice legal action generation in mtg_engine/api/routers/game.py
- [X] T073 [US5] Implement cascade resolution (cast or exile) in mtg_engine/engine/stack.py
- [X] T074 [US5] Implement library placement logic for non-chosen cards
- [X] T075 [US5] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 5 should be fully functional and testable independently

---

## Phase 8: User Story 6 - Scry/Surveil Create Blocking Choice (Priority: P6)

**Goal**: Implement scry and surveil mechanics with blocking choice prompts

**Independent Test**: Cast a card with "scry 2". Verify that `pending_scry_choice` appears in game state with the revealed cards, and that `choice` legal actions are emitted.

### Tests for User Story 6 (OPTIONAL - only if tests requested) ⚠️

- [X] T076 [P] [US6] Test scry choice in tests/test_018_scry_surveil.py
- [X] T077 [P] [US6] Test surveil choice in tests/test_018_scry_surveil.py

### Implementation for User Story 6

- [X] T078 [P] [US6] Implement scry choice generation in mtg_engine/engine/stack.py
- [X] T079 [US6] Implement surveil choice generation in mtg_engine/engine/stack.py
- [X] T080 [US6] Implement choice action handling in mtg_engine/api/routers/game.py
- [X] T081 [US6] Update game state to include pending_scry_choice and pending_surveil_choice
- [X] T082 [US6] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 6 should be fully functional and testable independently

---

## Phase 9: User Story 7 - Keyword Mechanics Implemented (Priority: P7)

**Goal**: Implement kicker, jump-start, suspend, foretell, and unearth keyword mechanics

**Independent Test**: For each keyword: put a card with that keyword in hand, verify the alternate-cost legal action appears; take the action; verify the effect.

### Tests for User Story 7 (OPTIONAL - only if tests requested) ⚠️

- [X] T083 [P] [US7] Test kicker variants in tests/test_018_keywords.py
- [X] T084 [P] [US7] Test jump-start in tests/test_018_keywords.py
- [X] T085 [P] [US7] Test suspend in tests/test_018_keywords.py
- [X] T086 [P] [US7] Test foretell in tests/test_018_keywords.py
- [X] T087 [P] [US7] Test unearth in tests/test_018_keywords.py

### Implementation for User Story 7

- [X] T088 [P] [US7] Implement kicker cost variants in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T089 [P] [US7] Implement jump-start cast action in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T090 [P] [US7] Implement suspend action in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T091 [P] [US7] Implement foretell action in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T092 [P] [US7] Implement unearth cast action in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T093 [P] [US7] Update PlayerState to track suspended_cards and foretold_cards
- [X] T094 [P] [US7] Update Permanent to track unearthed and time_counters
- [X] T095 [P] [US7] Implement suspend resolution in mtg_engine/engine/stack.py
- [X] T096 [P] [US7] Implement foretell resolution in mtg_engine/engine/stack.py
- [X] T097 [P] [US7] Implement unearth resolution in mtg_engine/engine/stack.py
- [X] T098 [US7] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 7 should be fully functional and testable independently

---

## Phase 10: User Story 8 - Protection from Color Targeting Enforced (Priority: P8)

**Goal**: Implement protection from color targeting enforcement

**Independent Test**: Cast a "protection from red" creature. Verify no red spells list it as a valid target.

### Tests for User Story 8 (OPTIONAL - only if tests requested) ⚠️

- [X] T099 [P] [US8] Test protection targeting in tests/test_018_protection.py
- [X] T100 [P] [US8] Test protection damage prevention in tests/test_018_protection.py

### Implementation for User Story 8

- [X] T101 [P] [US8] Implement protection targeting check in `_compute_legal_actions()` in mtg_engine/api/routers/game.py
- [X] T102 [US8] Implement protection damage prevention in mtg_engine/engine/stack.py
- [X] T103 [US8] Update spell resolution to check protection before applying damage
- [X] T104 [US8] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 8 should be fully functional and testable independently

---

## Phase 11: User Story 9 - AI Responds During Opponent's Priority Window (Priority: P9)

**Goal**: Enable AI to respond during opponent's priority window

**Independent Test**: Opponent casts a high-value creature. AI has a Counterspell. Verify that AI evaluates the counterspell action rather than auto-passing.

### Tests for User Story 9 (OPTIONAL - only if tests requested) ⚠️

- [X] T105 [P] [US9] Test AI non-active priority in tests/test_018_ai.py
- [X] T106 [P] [US9] Test AI counterspell evaluation in tests/test_018_ai.py

### Implementation for User Story 9

- [X] T107 [P] [US9] Update heuristic_player.py to evaluate actions during opponent's priority
- [X] T108 [US9] Implement non-active priority scoring in heuristic_player.py
- [X] T109 [US9] Update game_loop.py to check for AI responses during opponent's turn
- [X] T110 [US9] Run all existing tests to ensure backwards compatibility

**Checkpoint**: At this point, User Story 9 should be fully functional and testable independently

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, testing, and cleanup

- [X] T111 Run full test suite (all 376 existing tests + new tests)
- [X] T112 Fix any linting issues
- [X] T113 Update documentation (README, CLAUDE.md)
- [X] T114 Add integration tests for multi-story scenarios
- [X] T115 Performance testing (<=15ms per `_compute_legal_actions`, <=5ms spell resolution)
- [X] T116 Code review and cleanup
- [X] T117 Final validation against spec.md requirements

---

## Phase 13: User Story 10 - Planeswalker Combat & Uniqueness (Priority: P10)

**Goal**: Allow creatures to attack planeswalkers; enforce the planeswalker uniqueness SBA (CR 704.5l)

**Source**: Forge gap analysis — `Combat.java` supports planeswalker as defender; `GameAction.java` enforces CR 704.5l

**Independent Test**: Play a planeswalker onto the battlefield. Declare an attacker — verify the planeswalker appears as a valid attack target alongside the defending player. Have two copies of the same planeswalker enter — verify one is put into the graveyard by SBA.

### Implementation for User Story 10

- [X] T118 [P] [US10] Add planeswalker as valid attack target in `declare_attackers()` in mtg_engine/engine/combat.py (store target_id on AttackAssignment alongside defending player)
- [X] T119 [P] [US10] Update `_resolve_combat_damage()` in mtg_engine/engine/combat.py to reduce planeswalker loyalty when attacked, triggering SBA if loyalty reaches 0
- [X] T120 [P] [US10] Update `_compute_legal_actions()` in mtg_engine/api/routers/game.py to include planeswalker IDs as valid attack targets in declare_attackers legal actions
- [X] T121 [US10] Add CR 704.5l planeswalker uniqueness check to `check_state_based_actions()` in mtg_engine/engine/sba.py (keep highest-timestamp copy, send others to graveyard)
- [X] T122 [US10] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Creatures can attack planeswalkers; duplicate planeswalkers trigger SBA

---

## Phase 14: User Story 11 - Fizzle Detection & Mana Abilities Off-Stack (Priority: P11)

**Goal**: Spells whose all targets are illegal at resolution do nothing (fizzle, CR 608.2b); mana abilities never use the stack (CR 602.2)

**Source**: Forge gap analysis — `SpellAbilityStackInstance.java` re-validates targets at resolution; mana abilities bypass stack in Forge's `MagicStack.java`

**Independent Test (fizzle)**: Cast Lightning Bolt targeting a creature. In response, exile that creature. Verify that when Bolt resolves it does nothing rather than erroring or dealing damage to an invalid target. **Independent Test (mana)**: Tap a mana-producing land — verify no stack object is created and mana is added instantly without priority passing.

### Implementation for User Story 11

- [X] T123 [P] [US11] Add target re-validation at resolution start in `resolve_top_of_stack()` in mtg_engine/engine/stack.py — if all targets illegal, pop spell and emit fizzle event without applying effects
- [X] T124 [P] [US11] Add `is_mana_ability` flag to `ActivatedAbility` / `LegalAction` in mtg_engine/models/actions.py
- [X] T125 [US11] In `activate_ability()` in mtg_engine/api/routers/game.py, detect mana abilities (tap to add mana) and resolve them immediately without pushing to stack or passing priority
- [X] T126 [US11] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Fizzled spells resolve cleanly; mana abilities resolve immediately off-stack

---

## Phase 15: User Story 12 - Regeneration (Priority: P12)

**Goal**: Implement regeneration shields — when a creature with a regen shield would be destroyed, instead tap it, remove all damage, and remove the shield (CR 701.15)

**Source**: Forge gap analysis — `shieldCount` / `regeneratedThisTurn` fields in `Card.java`; regen is a replacement effect for "would be destroyed"

**Independent Test**: Give a creature a regeneration shield (e.g., activate a regen ability). Deal lethal damage. Verify the creature survives tapped with damage cleared rather than going to the graveyard.

### Implementation for User Story 12

- [X] T127 [P] [US12] Add `regen_shields` integer field to `Permanent` in mtg_engine/models/game.py
- [X] T128 [P] [US12] Add regeneration activated ability parsing in mtg_engine/engine/ability_parser.py (`"regenerate"` / `"regenerates"` patterns)
- [X] T129 [US12] In `_destroy_permanent()` in mtg_engine/engine/stack.py, check `regen_shields > 0` before moving to graveyard — if shields present, tap creature, clear damage, decrement shield, skip destruction
- [X] T130 [US12] Apply the same regen check in `check_state_based_actions()` in mtg_engine/engine/sba.py for lethal-damage SBA
- [X] T131 [US12] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Regeneration shields prevent destruction and correctly consume on use

---

## Phase 16: User Story 13 - Extra Turns (Priority: P13)

**Goal**: Implement a queue for extra turns so effects like Time Walk and Temporal Manipulation work correctly (CR 500.7)

**Source**: Forge gap analysis — `Stack<ExtraTurn>` in `PhaseHandler.java`

**Independent Test**: Cast Time Walk (target player takes an extra turn). Verify that after the current turn ends, the targeted player takes a full extra turn before normal turn order resumes.

### Implementation for User Story 13

- [X] T132 [P] [US13] Add `extra_turns` list field to `GameState` in mtg_engine/models/game.py (ordered list of player IDs who get extra turns, consumed LIFO per CR 500.7)
- [X] T133 [US13] Update `advance_turn()` in mtg_engine/engine/turn_manager.py to check `extra_turns` queue before switching active player — pop extra turn recipient as next active player if queue non-empty
- [X] T134 [US13] Add `_grant_extra_turn(player_id)` helper in mtg_engine/engine/stack.py and wire into `_apply_spell_effect()` for "take an extra turn" oracle text pattern
- [X] T135 [US13] Run all existing tests to ensure backwards compatibility

**Checkpoint**: "Take an extra turn" spells correctly queue and consume extra turns before normal rotation

---

## Phase 17: User Story 14 - Attack & Block Constraints (Goad, Must-Attack) (Priority: P14)

**Goal**: Enforce "must attack" / "cannot block" / goad constraints during declare attackers and blockers steps (CR 702.117, CR 508.1d)

**Source**: Forge gap analysis — `AttackConstraints` class in `Combat.java` with must/cannot flags; `Goad` keyword class

**Independent Test**: Give a creature the goad counter. Verify that on its controller's next turn, the legal actions for declare_attackers do not include passing without attacking with that creature (if able). Mark a creature "cannot block" — verify it does not appear as a valid blocker.

### Implementation for User Story 14

- [X] T136 [P] [US14] Add `goaded_by` list field (attacker IDs) and `must_attack` / `cannot_block` booleans to `Permanent` in mtg_engine/models/game.py
- [X] T137 [P] [US14] Add goad counter detection in `check_state_based_actions()` / trigger system — set `goaded_by` when goad ability resolves
- [X] T138 [US14] In `_validate_attack_declaration()` in mtg_engine/engine/combat.py, enforce that goaded/must-attack creatures are included in any non-empty attack if able
- [X] T139 [US14] In `_validate_block_declaration()` in mtg_engine/engine/combat.py, exclude `cannot_block` creatures from valid blockers
- [X] T140 [US14] Update `_compute_legal_actions()` in mtg_engine/api/routers/game.py to filter blocker options for cannot_block creatures
- [X] T141 [US14] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Goaded creatures must attack; cannot-block creatures are excluded from valid blocker assignments

---

## Phase 18: User Story 15 - Priority Windows in Combat (Priority: P15)

**Goal**: Grant priority after each combat step declaration so players can cast instants during combat (CR 508.3, 509.3, 510.2)

**Source**: Forge gap analysis — `PhaseHandler.java` grants priority after declare attackers and declare blockers; players currently cannot cast instants or activate abilities during combat in our engine

**Independent Test**: Declare attackers. Verify the non-active player receives priority before blockers are declared, allowing them to cast a removal spell on an attacker. Declare blockers. Verify the active player receives priority before damage is assigned.

### Implementation for User Story 15

- [X] T142 [P] [US15] After `declare_attackers()` succeeds in mtg_engine/api/routers/game.py, set `gs.priority_holder` to the non-active player (CR 508.3) before advancing to DECLARE_BLOCKERS
- [X] T143 [P] [US15] After `declare_blockers()` succeeds, set `gs.priority_holder` to the active player (CR 509.3) before advancing to FIRST_STRIKE_DAMAGE/COMBAT_DAMAGE
- [X] T144 [US15] Update `pass_priority()` in mtg_engine/engine/turn_manager.py to advance combat steps correctly when both players pass on an empty stack during combat
- [X] T145 [US15] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Players can cast instants and activate abilities between combat steps

---

## Phase 19: User Story 16 - Dies Triggers from SBAs (Priority: P16)

**Goal**: Fire "when ~ dies" / "whenever a creature dies" triggers when a creature is destroyed by state-based actions (CR 603.2)

**Source**: Forge gap analysis — `GameAction.java` fires zone-change triggers during SBA application; our SBA code moves permanents to graveyard without emitting trigger events

**Independent Test**: Put a creature with "when this creature dies, draw a card" on the battlefield. Deal lethal damage. Verify the ETB/death trigger fires and the card draw occurs, not just the creature entering the graveyard silently.

### Implementation for User Story 16

- [X] T146 [P] [US16] In `_destroy_permanent()` and `_move_to_graveyard()` in mtg_engine/engine/sba.py, emit a zone-change event (`from_zone="battlefield"`, `to_zone="graveyard"`) that the trigger system can intercept
- [X] T147 [P] [US16] Extend `check_damage_triggers()` or add `check_zone_change_triggers()` in mtg_engine/engine/triggers.py to handle "when X dies" / "whenever a creature dies" patterns from zone-change events
- [X] T148 [US16] Wire zone-change events from `move_permanent_to_zone()` in mtg_engine/engine/zones.py to the trigger system for battlefield→graveyard transitions
- [X] T149 [US16] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Death triggers fire when creatures are destroyed by SBAs or removal spells

---

## Phase 20: User Story 17 - Triggered Ability Choices ("May" Triggers) (Priority: P17)

**Goal**: When triggered abilities include "you may", present a choice to the player rather than auto-resolving; queue multiple simultaneous triggers correctly (CR 603.3)

**Source**: Forge gap analysis — Forge queues all triggered abilities and presents them as ordered choices; our triggers.py auto-applies effects without player input on "may" abilities

**Independent Test**: Put a creature with "whenever this creature attacks, you may draw a card" on the battlefield and attack. Verify a `choice` legal action is presented asking whether to draw, and that choosing "no" skips the draw.

### Implementation for User Story 17

- [X] T150 [P] [US17] Add `is_optional: bool` field to `PendingTrigger` in mtg_engine/models/game.py to mark "you may" triggers
- [X] T151 [P] [US17] Update trigger pattern matching in mtg_engine/engine/triggers.py to detect "you may" prefix and set `is_optional=True` on the resulting `PendingTrigger`
- [X] T152 [US17] In `_compute_legal_actions()` in mtg_engine/api/routers/game.py, when offering `put_trigger` actions for optional triggers, also offer a `decline_trigger` action so the player can skip the effect
- [X] T153 [US17] Add `decline_trigger` handler in the put-trigger endpoint (mtg_engine/api/routers/game.py) that discards the trigger without applying its effect
- [X] T154 [US17] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Optional triggers offer a yes/no choice; mandatory triggers still auto-queue

---

## Phase 21: User Story 18 - Delayed Triggered Abilities (Priority: P18)

**Goal**: Implement a deferred trigger queue for "at the beginning of your next upkeep" / "at the beginning of the next end step" effects (CR 603.7)

**Source**: Forge gap analysis — Forge has a `DelayedTrigger` class with a target phase/event; effects like Suspend and many enchantments rely on this

**Independent Test**: Create an effect that says "at the beginning of your next upkeep, draw a card." Advance through end step, cleanup, and the start of the next turn. Verify the draw fires at upkeep, not immediately.

### Implementation for User Story 18

- [X] T155 [P] [US18] Add `delayed_triggers: list[dict]` field to `GameState` in mtg_engine/models/game.py — each entry stores `{trigger_phase, trigger_step, controller, effect, once}`
- [X] T156 [P] [US18] In `begin_step()` in mtg_engine/engine/turn_manager.py, check `gs.delayed_triggers` at each step entry and move matching triggers into `gs.pending_triggers` for normal resolution
- [X] T157 [US18] Add `_schedule_delayed_trigger()` helper in mtg_engine/engine/stack.py and wire into `_apply_spell_effect()` for oracle text patterns like "at the beginning of your next upkeep"
- [X] T158 [US18] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Effects that fire at a future phase/step correctly defer and fire at the right time

---

## Phase 22: User Story 19 - Protection Blocks Blocking (Priority: P19)

**Goal**: Enforce the "Blocking" component of protection (DEBT) — a creature with protection from X cannot be blocked by X creatures (CR 702.16c)

**Source**: Forge gap analysis — Forge's `CombatUtil.canBlock()` checks all four DEBT components; our `declare_blockers()` only checks flying/reach and cannot-block constraints, not protection

**Independent Test**: Give an attacking creature "protection from red." Declare a red creature as its blocker. Verify the block is rejected.

### Implementation for User Story 19

- [X] T159 [P] [US19] In `declare_blockers()` in mtg_engine/engine/combat.py, add a check: if the blocker's color matches a "protection from [color]" on the attacker, raise `ValueError` rejecting the block
- [X] T160 [P] [US19] In `_compute_legal_actions()` in mtg_engine/api/routers/game.py, filter potential blockers to exclude creatures whose color matches the attacker's protection
- [X] T161 [US19] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Protection from X prevents X creatures from blocking the protected creature

---

## Phase 23: User Story 20 - Activated Ability Timing Restrictions (Priority: P20)

**Goal**: Enforce `timing_restriction` on activated abilities — abilities with "activate only as a sorcery" or "activate only during your turn" are correctly gated (CR 602.1)

**Source**: Forge gap analysis — `ability_parser.py` already extracts `timing_restriction` but the `activate` endpoint never checks it

**Independent Test**: Create a permanent with an activated ability that has "activate only as a sorcery." Attempt to activate it during the opponent's turn. Verify the activation is rejected. Verify it succeeds during your own main phase with an empty stack.

### Implementation for User Story 20

- [X] T162 [P] [US20] In `activate()` in mtg_engine/api/routers/game.py, after parsing the ability, read `ability.timing_restriction` and validate it against current `gs.phase`, `gs.step`, `gs.active_player`, and `gs.stack` — raise `ValueError` if violated
- [X] T163 [P] [US20] In `_compute_legal_actions()` in mtg_engine/api/routers/game.py, filter activated ability actions by `timing_restriction` so illegal-timing abilities are not offered
- [X] T164 [US20] Run all existing tests to ensure backwards compatibility

**Checkpoint**: "Activate only as a sorcery" and "activate only during your turn" abilities are correctly gated

---

## Phase 24: User Story 21 - Evasion Keyword Blocking Restrictions (Priority: P21)

**Goal**: Enforce shadow, horsemanship, and landwalk blocking restrictions in `declare_blockers()` (CR 702.27, CR 702.54, CR 702.11)

**Source**: Forge gap analysis — Forge's `CombatUtil` checks all evasion keywords; our engine only checks flying/reach

**Independent Test**: Give an attacking creature shadow. Declare a blocker without shadow. Verify the block is rejected. Give a creature landwalk (e.g., islandwalk) and attack when the opponent controls an Island — verify it cannot be blocked.

### Implementation for User Story 21

- [X] T165 [P] [US21] In `declare_blockers()` in mtg_engine/engine/combat.py, add shadow check: attacker with shadow can only be blocked by shadow; blocker with shadow can only block shadow
- [X] T166 [P] [US21] In `declare_blockers()`, add horsemanship check: same as flying but for horsemanship keyword
- [X] T167 [P] [US21] In `declare_blockers()`, add landwalk check: if attacker has "[type]walk" and defending player controls a land of that type, attacker cannot be blocked
- [X] T168 [P] [US21] Filter these restrictions in `_compute_legal_actions()` so invalid blockers are excluded from valid_targets
- [X] T169 [US21] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Shadow, horsemanship, and landwalk correctly restrict blocking

---

## Phase 25: User Story 22 - "Cannot Be Countered" Spell Flag (Priority: P22)

**Goal**: Track `uncounterable` on stack objects so Counterspell cannot target them (CR 702.102)

**Source**: Forge gap analysis — Forge marks spells as uncounterable via a flag on `SpellAbilityStackInstance`; our stack has no such field

**Independent Test**: Cast a spell with "this spell can't be countered." Cast Counterspell targeting it. Verify Counterspell fizzles (its target is illegal) or the counter effect is ignored.

### Implementation for User Story 22

- [X] T170 [P] [US22] Add `uncounterable: bool = False` field to `StackObject` in mtg_engine/models/game.py
- [X] T171 [P] [US22] In `cast_spell()` in mtg_engine/engine/stack.py, detect "this spell can't be countered" / "can't be countered" in oracle text and set `stack_obj.uncounterable = True`
- [X] T172 [US22] In `_counter_spell()` in mtg_engine/engine/stack.py, check `target_obj.uncounterable` and skip the countering effect if True (log at INFO level)
- [X] T173 [US22] In `_compute_legal_actions()`, filter counter-target valid_targets to exclude uncounterable stack objects
- [X] T174 [US22] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Spells marked uncounterable cannot be targeted by Counterspell or similar effects

---

## Phase 26: User Story 23 - "Until Your Next Turn" Effect Scoping (Priority: P23)

**Goal**: Differentiate "until end of turn" (clears at active player's cleanup) from "until your next turn" (clears at that player's next cleanup) so opponent's cleanup doesn't incorrectly remove your effects (CR 110.3)

**Source**: Forge gap analysis — Forge tracks effect expiry scope per controller; our cleanup clears all P/T bonuses and prevention effects unconditionally

**Independent Test**: Apply a "until your next turn" pump to a creature during your turn. Advance to opponent's turn through cleanup. Verify the bonus persists. Advance to your next cleanup. Verify the bonus is removed.

### Implementation for User Story 23

- [X] T175 [P] [US23] Add `power_bonus_expires: str | None` and `toughness_bonus_expires: str | None` fields to `Permanent` in mtg_engine/models/game.py — value is either `"end_of_turn"` (current active player's cleanup) or `"player:<name>"` (that player's next cleanup)
- [X] T176 [P] [US23] Update the pump pattern in `_apply_spell_effect()` / `_pump_creature()` in mtg_engine/engine/stack.py to default to `"end_of_turn"` scope; add detection for "until your next turn" oracle text to set `"player:<controller>"` scope
- [X] T177 [US23] In `begin_step()` cleanup in mtg_engine/engine/turn_manager.py, only clear `power_bonus`/`toughness_bonus` on permanents where `expires == "end_of_turn"` or `expires == f"player:{active_player}"`
- [X] T178 [US23] Run all existing tests to ensure backwards compatibility

**Checkpoint**: "Until your next turn" effects survive the opponent's cleanup step

---

## Phase 27: User Story 24 - Sacrifice Cost Validation (Priority: P24)

**Goal**: Validate that sacrifice-cost activated abilities have a valid sacrifice target before being offered as legal actions (CR 602.2a)

**Source**: Forge gap analysis — Forge validates all ability costs including sacrifice targets before listing them as legal; our engine offers sacrifice-cost abilities even with no valid targets

**Independent Test**: Create a permanent with "{1}, sacrifice a creature: draw a card." Verify this action appears only when the controller has at least one creature to sacrifice. Sacrifice the last creature. Verify the action disappears.

### Implementation for User Story 24

- [X] T179 [P] [US24] In `_compute_legal_actions()` in mtg_engine/api/routers/game.py, detect sacrifice-cost abilities (regex `r"sacrifice (a|an) [\w ]+"` in ability cost text) and count available sacrifice targets on the battlefield
- [X] T180 [US24] Only include sacrifice-cost ability actions in legal actions if at least one valid sacrifice target (of the correct type) exists for the controller
- [X] T181 [US24] Run all existing tests to ensure backwards compatibility

**Checkpoint**: Sacrifice-cost abilities only appear as legal actions when a valid sacrifice target exists

---

## Dependencies

### User Story Completion Order

1. **US1** (Spell Effects) - MUST complete first (foundation for all other stories)
2. **US2** (Targeting Rules) - Can start after US1 Phase 1 (model changes)
3. **US3** (X Spells) - Can start after US1 Phase 1 (model changes)
4. **US4** (Modal Spells) - Can start after US1 Phase 1 (model changes)
5. **US5** (Cascade) - Can start after US1 Phase 1 (model changes)
6. **US6** (Scry/Surveil) - Can start after US1 Phase 1 (model changes)
7. **US7** (Keyword Mechanics) - Can start after US1 Phase 1 (model changes)
8. **US8** (Protection) - Can start after US1 Phase 1 (model changes)
9. **US9** (AI Priority) - Can start after US1 Phase 1 (model changes)
10. **US10** (Planeswalker Combat) - Can start after US1 Phase 1 (model changes)
11. **US11** (Fizzle & Mana Abilities) - Can start after US1; fizzle depends on target tracking from US2
12. **US12** (Regeneration) - Can start after US1 (model changes)
13. **US13** (Extra Turns) - Can start after US1 (model changes)
14. **US14** (Attack/Block Constraints) - Can start after US1 (model changes)
15. **US15** (Priority in Combat) - Can start independently; touches turn_manager + game.py router
16. **US16** (Dies Triggers from SBAs) - Can start after US1; depends on trigger system
17. **US17** (May Triggers) - Can start after US1; depends on trigger system
18. **US18** (Delayed Triggers) - Can start after US17 (depends on trigger queue infrastructure)
19. **US19** (Protection Blocks Blocking) - Can start after US2 (uses same protection helpers)
20. **US20** (Ability Timing Restrictions) - Can start independently
21. **US21** (Evasion Blocking Restrictions) - Can start independently
22. **US22** (Cannot Be Countered) - Can start after US1 (stack model change)
23. **US23** (Until Your Next Turn) - Can start after US1 (model changes)
24. **US24** (Sacrifice Cost Validation) - Can start independently

### Parallel Execution Opportunities

After Phase 1 (model changes) is complete, the following can be implemented in parallel:
- **US2** Targeting Rules (mtg_engine/api/routers/game.py, mtg_engine/engine/combat.py)
- **US3** X Spells (mtg_engine/api/routers/game.py)
- **US4** Modal Spells (mtg_engine/engine/stack.py)
- **US5** Cascade (mtg_engine/engine/stack.py, mtg_engine/api/routers/game.py)
- **US6** Scry/Surveil (mtg_engine/engine/stack.py)
- **US7** Keyword Mechanics (mtg_engine/api/routers/game.py, mtg_engine/engine/stack.py)
- **US8** Protection (mtg_engine/api/routers/game.py, mtg_engine/engine/stack.py)
- **US9** AI Priority (ai_client/heuristic_player.py, ai_client/game_loop.py)
- **US10** Planeswalker Combat (mtg_engine/engine/combat.py, mtg_engine/engine/sba.py)
- **US11** Fizzle & Mana Abilities (mtg_engine/engine/stack.py, mtg_engine/api/routers/game.py)
- **US12** Regeneration (mtg_engine/models/game.py, mtg_engine/engine/stack.py, mtg_engine/engine/sba.py)
- **US13** Extra Turns (mtg_engine/models/game.py, mtg_engine/engine/turn_manager.py, mtg_engine/engine/stack.py)
- **US14** Attack/Block Constraints (mtg_engine/models/game.py, mtg_engine/engine/combat.py)
- **US15** Priority in Combat (mtg_engine/api/routers/game.py, mtg_engine/engine/turn_manager.py)
- **US16** Dies Triggers (mtg_engine/engine/sba.py, mtg_engine/engine/triggers.py, mtg_engine/engine/zones.py)
- **US17** May Triggers (mtg_engine/models/game.py, mtg_engine/engine/triggers.py, mtg_engine/api/routers/game.py)
- **US19** Protection Blocks Blocking (mtg_engine/engine/combat.py, mtg_engine/api/routers/game.py)
- **US20** Ability Timing Restrictions (mtg_engine/api/routers/game.py)
- **US21** Evasion Blocking Restrictions (mtg_engine/engine/combat.py, mtg_engine/api/routers/game.py)
- **US22** Cannot Be Countered (mtg_engine/models/game.py, mtg_engine/engine/stack.py)
- **US23** Until Your Next Turn (mtg_engine/models/game.py, mtg_engine/engine/stack.py, mtg_engine/engine/turn_manager.py)
- **US24** Sacrifice Cost Validation (mtg_engine/api/routers/game.py)

### Independent Test Criteria

Each user story can be tested independently:
- **US1**: Cast various spells and verify effects apply correctly
- **US2**: Create creatures with hexproof/shroud/menace and verify targeting rules
- **US3**: Cast X spells with different X values and verify damage
- **US4**: Cast modal spells and verify only chosen modes apply
- **US5**: Cast cascade spells and verify cascade choice works
- **US6**: Cast scry/surveil spells and verify blocking choices
- **US7**: Cast cards with keyword mechanics and verify alternate costs
- **US8**: Create creatures with protection and verify targeting/damage prevention
- **US9**: Opponent casts creature, AI counters with Counterspell
- **US10**: Attack a planeswalker; verify duplicate planeswalker SBA triggers
- **US11**: Fizzle a spell by removing its target in response; tap land and verify no stack object
- **US12**: Give creature a regen shield; deal lethal damage; verify it survives tapped
- **US13**: Cast Time Walk; verify targeted player takes an extra turn before normal rotation
- **US14**: Goad a creature; verify it must attack on owner's next turn
- **US15**: Declare attackers; verify non-active player receives priority before blockers
- **US16**: Kill a creature with a death trigger; verify the trigger fires
- **US17**: Attack with a creature that has "you may draw"; verify yes/no choice is offered
- **US18**: Apply "at beginning of your next upkeep" effect; verify it fires next upkeep only
- **US19**: Attack with protection from red creature; verify red blocker is rejected
- **US20**: Activate "only as a sorcery" ability at instant speed; verify rejection
- **US21**: Attack with shadow creature; verify non-shadow blocker is rejected
- **US22**: Cast uncounterable spell; cast Counterspell targeting it; verify it resolves
- **US23**: Pump with "until your next turn"; verify it persists through opponent's cleanup
- **US24**: Remove all creatures; verify sacrifice-cost ability disappears from legal actions

---

## Implementation Strategy

### MVP Scope

The Minimum Viable Product (MVP) should include:
- **Phase 1**: Setup
- **Phase 2**: Foundational
- **Phase 3**: User Story 1 (Spell Effects) - This is the critical foundation

With just US1 complete, the engine can resolve 80% of common spells, making the game playable with a broad card pool.

### Incremental Delivery

After MVP, deliver user stories in priority order (P1 → P14):
1. US1 (P1) - Spell Effects
2. US2 (P2) - Targeting Rules
3. US3 (P3) - X Spells
4. US4 (P4) - Modal Spells
5. US5 (P5) - Cascade
6. US6 (P6) - Scry/Surveil
7. US7 (P7) - Keyword Mechanics
8. US8 (P8) - Protection
9. US9 (P9) - AI Priority
10. US10 (P10) - Planeswalker Combat & Uniqueness
11. US11 (P11) - Fizzle & Mana Abilities Off-Stack
12. US12 (P12) - Regeneration
13. US13 (P13) - Extra Turns
14. US14 (P14) - Attack/Block Constraints

Each story delivers independent, testable functionality.

---

## Summary

**Total Tasks**: 141
**Setup Tasks**: 3
**Foundational Tasks**: 4
**User Story Tasks**:
- US1: 22 tasks
- US2: 7 tasks
- US3: 5 tasks
- US4: 4 tasks
- US5: 5 tasks
- US6: 4 tasks
- US7: 12 tasks
- US8: 4 tasks
- US9: 4 tasks
- US10: 5 tasks (Planeswalker Combat & Uniqueness)
- US11: 4 tasks (Fizzle & Mana Abilities Off-Stack)
- US12: 5 tasks (Regeneration)
- US13: 4 tasks (Extra Turns)
- US14: 6 tasks (Attack/Block Constraints)
**Polish Tasks**: 7 tasks

**Parallel Opportunities**: 13 stories can be implemented in parallel after Phase 1
**Independent Test Criteria**: Each story has clear test scenarios
**MVP Scope**: Phases 1-3 (10 tasks) for basic playability

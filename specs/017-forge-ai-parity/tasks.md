# Tasks: Forge AI Parity

**Input**: Design documents from `/specs/017-forge-ai-parity/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Organization**: Tasks grouped by user story. 36 user stories across 38 phases.
**Tests**: Not explicitly requested — no test tasks generated.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm project structure matches plan. No new files created — project already exists.

- [X] T001 Confirm `ai_client/` and `mtg_engine/` directory layout matches plan.md Source Code structure; note any discrepancies before proceeding

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and wiring that ALL user stories depend on. Must complete before any US phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `AIMemory` dataclass to `ai_client/models.py` with all 9 named category fields: `revealed_cards: dict[str, list]`, `bounced_this_turn: set[str]`, `attached_this_turn: set[str]`, `animated_this_turn: set[str]`, `chosen_fog_effect: str | None`, `trick_attackers: set[str]`, `mandatory_attackers: set[str]`, `held_mana_for_main2: set[str]`, `held_mana_for_declblk: set[str]`; add `new_turn()` method that clears all per-turn fields except `revealed_cards` and `mandatory_attackers`
- [X] T003 [P] Add `AiPersonalityProfile` dataclass to `ai_client/models.py` with all boolean flags (ATTACK_INTO_TRADE_WHEN_TAPPED_OUT, TRY_TO_AVOID_ATTACKING_INTO_CERTAIN_BLOCK, ENABLE_RANDOM_FAVORABLE_TRADES_ON_BLOCK, RANDOMLY_TRADE_EVEN_WHEN_HAVE_LESS_CREATURES, ALWAYS_COUNTER_OTHER_COUNTERSPELLS, ALWAYS_COUNTER_DAMAGE_SPELLS, ALWAYS_COUNTER_REMOVAL_SPELLS, ALWAYS_COUNTER_PUMP_SPELLS, ALWAYS_COUNTER_AURAS, ACTIVELY_DESTROY_ARTIFACTS_AND_ENCHANTMENTS, ACTIVELY_DESTROY_IMMEDIATELY_UNBLOCKABLE, HOLD_LAND_DROP_FOR_MAIN2_IF_UNUSED, RE_EQUIP_ON_CREATURE_DEATH) and all probability floats (chance_to_attack_into_trade=0.40, chance_to_atktrade_when_opp_has_mana=0.30, chance_decrease_to_trade_vs_embalm=0.50, chance_to_trade_to_save_planeswalker=0.70, chance_to_hold_combat_tricks=0.30, token_generation_chance=0.80, chance_to_counter_cmc_1=0.50, chance_to_counter_cmc_2=0.75, chance_to_counter_cmc_3_plus=1.00, phyrexian_life_threshold=5); add `DEFAULT` and `AGGRO` class-level constants
- [X] T004 [P] Add `BlockClassification` enum to `ai_client/models.py` with values `SAFE`, `TRADE`, `CHUMP`
- [X] T005 [P] Extend `LegalAction` in `mtg_engine/models/actions.py` with three optional fields: `loyalty_ability_index: Optional[int] = None`, `cascade_card_id: Optional[str] = None`, `from_graveyard: bool = False`; add new request models `MulliganRequest(player_name: str, keep: bool)`, `ActivateLoyaltyRequest(permanent_id: str, ability_index: int, targets: list[str])`, `CascadeChoiceRequest(player_name: str, card_id: str, cast: bool)`
- [X] T006 Add `personality: AiPersonalityProfile` field (default `AiPersonalityProfile.DEFAULT`) to `PlayerConfig` in `ai_client/models.py`; extend `HeuristicPlayer.__init__(self, config: PlayerConfig)` in `ai_client/heuristic_player.py` to store `self._profile = config.personality`; extend `choose_action()` signature to accept `memory: AIMemory | None = None` and store as `self._memory`
- [X] T007 Instantiate `AIMemory` per player in `ai_client/game_loop.py` at game start (one instance per AI player, keyed by player name); call `memory.new_turn()` at the start of each AI turn; pass `memory` to every `player.choose_action()` call
- [X] T008 Create `ai_client/lookahead.py` with `LookaheadSimulator` class: `__init__(self, heuristic_player, max_depth=1)`; `evaluate_bonus(current_action, game_state, memory) -> float` returning 0.0 stub (full implementation in US14); `_apply_action_to_state(action, state) -> dict` skeleton handling play_land (increment lands_played), cast (remove card from hand), and pass (advance step) actions on a deep-copied state dict

**Checkpoint**: Foundation ready — all user story phases can now proceed.

---

## Phase 3: US1 — AI Target Selection (Priority: P1) 🎯 MVP

**Goal**: AI selects the best target for removal, burn, and buff spells rather than using the engine's auto-pick.

**Independent Test**: Board with opponent 1/1 and 5/5; AI has destroy-target-creature spell. Verify AI targets 5/5.

- [X] T009 [US1] Expand `valid_targets` population in `_compute_legal_actions()` in `mtg_engine/api/routers/game.py` to return ALL valid targets (not just the first auto-picked one) for removal spells (destroy/exile patterns), burn spells (damage to any target), and Aura attach spells — iterate all legal targets and include every permanent/player ID that satisfies the spell's targeting restriction
- [X] T010 [US1] Add `_select_best_target(valid_targets: list[str], game_state: dict, effect_type: str) -> str | None` to `ai_client/heuristic_player.py`: for `effect_type="removal"` return highest-CMC opponent creature; for `effect_type="burn"` check lethal against opponent player first, else highest-power creature; for `effect_type="aura"` return highest-power friendly creature; for `effect_type="control"` return highest-CMC opponent permanent
- [X] T011 [US1] Integrate `_select_best_target()` into `_score_cast()` in `ai_client/heuristic_player.py`: detect effect type from oracle text using existing `_DESTROY_RE` and `_DAMAGE_TO_TARGET_RE` patterns; set `action["chosen_target"]` to selected target ID before scoring; ensure `_map_action_to_request()` in `game_loop.py` passes `chosen_target` as `targets[0]` in `CastRequest`
- [X] T012 [US1] Add `_CONTROL_RE = re.compile(r'gain control of target', re.IGNORECASE)` and `_LIFE_LOSS_RE = re.compile(r'target player loses \d+ life|target opponent loses \d+ life', re.IGNORECASE)` to top of `ai_client/heuristic_player.py`; wire both into `_select_best_target()` effect detection

**Checkpoint**: AI now picks optimal targets for all targeted spells.

---

## Phase 4: US2 — AI Combat Tricks and Instant-Speed Holding (Priority: P1)

**Goal**: AI holds pump instants for declare-blockers timing and holds mana open on its own turn when it has counterspells.

**Independent Test**: AI holds +3/+3 instant when 2/2 attacks; opponent blocks with 4/4; AI casts pump at blockers step.

- [X] T013 [US2] Add instant-speed combat trick detection to `ai_client/heuristic_player.py`: add `_PUMP_RE` already exists — create `_is_combat_trick(card) -> bool` that returns True if card has flash or is an instant that contains a pump pattern; add `_should_hold_for_combat(game_state, my_name) -> bool` that returns True if current step is MAIN and a combat window exists this turn (is active player)
- [X] T014 [US2] Modify `_score_cast()` in `ai_client/heuristic_player.py` so that instant pump spells score `-50.0` during main phase when no combat is in progress AND `self._memory` has no `trick_attackers` designated — preventing main-phase sorcery casting; score them at full value (+pump_power × 8) during declare_blockers step when a friendly creature is in combat
- [X] T015 [US2] Add "hold up mana" logic to `ai_client/game_loop.py`: when the AI has a counterspell in hand and no sorcery-speed plays scoring above a configurable threshold (default: 30.0), pass priority in main phase and store the counterspell's mana requirement in `memory.held_mana_for_declblk`; on the opponent's turn, when priority is granted mid-stack, evaluate counterspell actions before auto-passing
- [X] T016 [US2] Add `TRICK_ATTACKERS` designation logic in `_score_action()` for declare_attackers step in `ai_client/heuristic_player.py`: when AI designates attackers and holds a combat trick instant, add those attacker IDs to `self._memory.trick_attackers` per FR-083 so declare-blockers evaluation knows to expect opponent blocks

**Checkpoint**: AI correctly holds instants and mana for instant-speed windows.

---

## Phase 5: US3 — Card Draw and Ramp Scoring (Priority: P2)

**Goal**: Draw spells and ramp spells score meaningfully (≥15 per card drawn; ramp ≥ vanilla 2/2 of same CMC).

**Independent Test**: Draw-two spell scores > 0; Rampant Growth scores ≥ vanilla 2/2.

- [X] T017 [P] [US3] Add `_DRAW_RE = re.compile(r'draw (\d+) card|draw a card', re.IGNORECASE)` and `_RAMP_RE = re.compile(r'search your library for.*land|put.*land.*onto the battlefield|add.*mana', re.IGNORECASE)` to top of `ai_client/heuristic_player.py`
- [X] T018 [US3] Add `_score_draw_spell(oracle_text) -> float` to `ai_client/heuristic_player.py`: extract card count N from `_DRAW_RE` match; return `N * 15.0`; if the spell has another effect (removal + draw, burn + draw), this value is added as a bonus on top of the primary effect score
- [X] T019 [US3] Add `_score_ramp_spell(card, game_state, my_name) -> float` to `ai_client/heuristic_player.py`: detect land-fetch ramp (Cultivate pattern) → `turns_ahead * 20.0`; detect mana-dork creatures (creature with `{T}: Add`) → add `15.0 * mana_produced` bonus on top of creature score per FR-026; wire both into `_score_noncreature_spell()` and `_score_creature()` dispatch

**Checkpoint**: AI correctly values draw and ramp spells.

---

## Phase 6: US4 — Planeswalker Loyalty Ability Activation (Priority: P2)

**Goal**: AI activates a loyalty ability every turn it controls a planeswalker.

**Independent Test**: AI with planeswalker activates + ability each turn; no turn skipped.

- [X] T020 [US4] Add loyalty ability parsing to `mtg_engine/card_data/ability_parser.py`: detect `[+N]`, `[-N]`, `[0]` patterns in oracle text of permanents with "planeswalker" type line; create `LoyaltyAbility(index: int, loyalty_change: int, effect: str, raw_text: str)` dataclass; expose `parse_loyalty_abilities(oracle_text) -> list[LoyaltyAbility]`
- [X] T021 [US4] Add `activate_loyalty` legal action generation to `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`: for each planeswalker on battlefield controlled by priority player, call `parse_loyalty_abilities()`; emit `action_type="activate_loyalty"` with `permanent_id`, `loyalty_ability_index`, `description`; filter out − abilities where `perm.loyalty + loyalty_change < 0`; only offer if planeswalker has not activated this turn (track via `perm.loyalty_activated_this_turn` flag)
- [X] T022 [US4] Add `POST /game/{game_id}/activate-loyalty` endpoint to `mtg_engine/api/routers/game.py`: validate planeswalker exists, adjust `perm.loyalty` by `loyalty_change`, set `perm.loyalty_activated_this_turn = True`, queue the ability effect for resolution; return new loyalty and effect status
- [X] T023 [US4] Add `_score_loyalty_ability(action, game_state, my_name) -> float` to `ai_client/heuristic_player.py`: + abilities score `loyalty_change * 8.0`; 0 abilities score `25.0`; − abilities score based on effect (removal → target CMC × 10, draw → 15 per card, damage → burn formula); never activate − if it would reduce loyalty ≤ 0; wire into `_score_action()` dispatcher; wire `activate_loyalty` action → `ActivateLoyaltyRequest` in `game_loop.py`'s `_map_action_to_request()`

**Checkpoint**: AI activates planeswalker abilities every eligible turn.

---

## Phase 7: US5 — Board Wipe Evaluation (Priority: P2)

**Goal**: AI only casts board wipes when the net permanent CMC destroyed favors the AI.

**Independent Test**: AI with Wrath and 3 creatures vs opponent's 1 creature → does NOT cast. Opponent at 4 creatures → DOES cast.

- [X] T024 [US5] Add `_WIPE_RE = re.compile(r'destroy all creatures|exile all creatures|all creatures get -\d+/-\d+', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T025 [US5] Add `_score_board_wipe(game_state, my_name) -> float` to `ai_client/heuristic_player.py`: compute `my_cmc_lost` = sum of CMC of friendly non-indestructible creatures on battlefield; compute `opp_cmc_destroyed` = sum of CMC of opponent non-indestructible creatures; if `my_cmc_lost >= opp_cmc_destroyed` return `-20.0` (do not cast); else return `(opp_cmc_destroyed - my_cmc_lost) * 10.0`; detect indestructible via `_card_has_kw(card, "indestructible")`; wire into `_score_noncreature_spell()` when `_WIPE_RE` matches

**Checkpoint**: AI correctly evaluates board wipes based on net CMC delta.

---

## Phase 8: US6 — Mulligan Hand Evaluation (Priority: P2)

**Goal**: AI mulligans 0-land and 7-land hands; keeps 2-4 land hands with on-curve spells; stops at 5 cards.

**Independent Test**: 0-land hand → mulligan; 7-land hand → mulligan; 2 lands + 5 on-curve spells → keep.

- [X] T026 [US6] Add `mulligan_phase_active: bool = False` flag and `hands_mulliganed: dict[str, int]` tracking to `GameState` in `mtg_engine/models/game.py`; set `mulligan_phase_active = True` after initial hands are dealt at game creation in `mtg_engine/api/game_manager.py`
- [X] T027 [US6] Add `POST /game/{game_id}/mulligan` endpoint to `mtg_engine/api/routers/game.py`: validate `mulligan_phase_active` is True and player has not yet committed to keeping; if `keep=False` and hand_size > 5: discard entire hand, draw `hand_size - 1` new cards (London mulligan), increment `hands_mulliganed[player_name]`; if `keep=True` or hand_size == 5: mark player as committed; when all players committed set `mulligan_phase_active = False`; add `declare_mulligan` legal action during mulligan phase
- [X] T028 [US6] Add `evaluate_mulligan(hand: list[dict], hand_size: int) -> bool` to `ai_client/heuristic_player.py` (returns True to mulligan): mulligan if land_count == 0 or land_count == hand_size (all lands); mulligan if no spell castable within first 4 turns given land count; always keep if hand_size <= 5; wire call into `ai_client/game_loop.py` before the game loop starts — poll mulligan actions and call `evaluate_mulligan()` until keep or floor reached
- [X] T029 [US6] Update `_map_action_to_request()` in `ai_client/game_loop.py` to handle `action_type="declare_mulligan"` → `POST /game/{id}/mulligan` with `MulliganRequest(player_name, keep)`

**Checkpoint**: AI makes correct keep/mulligan decisions before game starts.

---

## Phase 9: US7 — Sacrifice Target Selection (Priority: P3)

**Goal**: AI selects lowest-CMC permanent as sacrifice target; tokens preferred over non-tokens.

**Independent Test**: Sacrifice-a-creature cost with 1/1 and 5/5 → AI sacrifices 1/1.

- [X] T030 [P] [US7] Add `_SACRIFICE_COST_RE = re.compile(r'sacrifice a|sacrifice an', re.IGNORECASE)` to `ai_client/heuristic_player.py`; add `_select_sacrifice_target(valid_targets: list[str], game_state: dict, my_name: str) -> str | None`: prefer tokens (check `perm.get("is_token")`) over non-tokens; among non-tokens, pick lowest CMC; among ties pick lowest-index; return None if list empty
- [X] T031 [US7] Wire `_select_sacrifice_target()` into cast and activate scoring in `ai_client/heuristic_player.py`: when oracle text matches `_SACRIFICE_COST_RE` and `valid_targets` contains sacrifice candidates, call `_select_sacrifice_target()` and store result in `action["sacrifice_target"]`; if no valid target exists score the action at -1000.0 (do not cast); update `_map_action_to_request()` in `game_loop.py` to pass `sacrifice_target` as first element of `targets`

**Checkpoint**: AI always sacrifices the lowest-value permanent.

---

## Phase 10: US8 — Scry and Surveil Decisions (Priority: P3)

**Goal**: AI keeps on-curve cards on top during Scry; sends graveyard-synergy cards to GY during Surveil.

**Independent Test**: Scry reveals CMC-7 card on turn 2 → bottom it. Surveil reveals flashback card → GY it.

- [X] T032 [P] [US8] Add `_SCRY_RE = re.compile(r'^scry (\d+)', re.IGNORECASE)` and `_SURVEIL_RE = re.compile(r'^surveil (\d+)', re.IGNORECASE)` to `ai_client/heuristic_player.py`; add `_GRAVEYARD_SYNERGY_KW = {"flashback", "escape", "unearth", "disturb", "jump-start"}` constant
- [X] T033 [US8] Add `_score_scry_choice(revealed_card: dict, current_turn: int) -> str` to `ai_client/heuristic_player.py` returning `"top"` or `"bottom"`: keep on top if `card_cmc <= current_turn + 2`; bottom otherwise; add `_score_surveil_choice(revealed_card: dict) -> str` returning `"top"` or `"graveyard"`: graveyard if card has any keyword in `_GRAVEYARD_SYNERGY_KW` else apply scry logic; wire both into the `ChoiceRequest` handler in `game_loop.py` when `action_type == "choice"` and choice type is scry/surveil

**Checkpoint**: AI makes correct library manipulation decisions.

---

## Phase 11: US9 — Modal Spell Mode Selection (Priority: P3)

**Goal**: AI evaluates each mode independently and selects the highest-scoring valid mode(s).

**Independent Test**: Choose-one with removal mode (opponent has creature) and draw mode → AI picks removal.

- [X] T034 [P] [US9] Add `_select_modes(card: dict, game_state: dict, my_name: str) -> list[int]` to `ai_client/heuristic_player.py`: for each mode in `card.get("card_faces") or []` or parsed from oracle text `(Mode 1: ... Mode 2: ...)`, score the mode text using the same scoring sub-dispatch as `_score_noncreature_spell()`; filter out modes with no valid targets; return list of top-N mode indices for choose-N spells; return `[]` if no valid modes (score action at -1000.0)
- [X] T035 [US9] Wire `_select_modes()` into `_score_cast()` in `ai_client/heuristic_player.py`: detect modal spells via `"choose one" in oracle.lower() or "choose two" in oracle.lower()`; call `_select_modes()` and store indices in `action["modes_chosen"]`; update `_map_action_to_request()` in `game_loop.py` to pass `action["modes_chosen"]` into `CastRequest.modes_chosen`

**Checkpoint**: AI picks best mode(s) for modal spells.

---

## Phase 12: US10 — Equipment Attachment (Priority: P3)

**Goal**: AI equips equipment to its highest-power creature when mana is available.

**Independent Test**: AI with equipment and 1/1 + 4/4 equips the 4/4.

- [X] T036 [P] [US10] Add `_is_equipment(perm: dict) -> bool` helper to `ai_client/heuristic_player.py` checking `"equipment" in (perm.get("card", {}).get("type_line") or "").lower()`; add `_select_equip_target(valid_targets: list[str], game_state: dict, my_name: str) -> str | None`: among valid friendly creature targets, return the ID of the highest-power creature
- [X] T037 [US10] In `_score_action()` in `ai_client/heuristic_player.py` for `action_type="activate"` abilities: detect equip cost pattern (`r'equip'` in ability description); call `_select_equip_target()` and store result in `action["equip_target"]`; score equip activation at `equipment_power_bonus * 8.0 + equipment_toughness_bonus * 4.0` (parse bonuses from equip ability effect text); record equip in `self._memory.attached_this_turn`; check `self._profile.re_equip_on_creature_death` before scoring re-equip actions

**Checkpoint**: AI equips equipment to best creature every turn.

---

## Phase 13: US11 — Graveyard Zone Casting (Priority: P3)

**Goal**: AI generates and scores cast actions for flashback/escape/unearth/disturb cards in graveyard.

**Independent Test**: Flashback spell in graveyard with mana → cast action offered and scored.

- [X] T038 [P] [US11] Add graveyard casting branch to `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`: iterate `player.graveyard`; for each card with keyword in `{"flashback", "escape", "unearth", "disturb"}` (detected via `parse_oracle_text()`): validate alternative cost can be paid; for escape, validate `len(player.graveyard) >= escape_exile_count`; emit `LegalAction(action_type="cast", card_id=card.id, from_graveyard=True, alternative_cost="flashback"|"escape"|"unearth"|"disturb", ...)`
- [X] T039 [US11] Add graveyard cast resolution in `mtg_engine/api/routers/game.py` cast handler: when `req.alternative_cost in {"flashback", "escape", "unearth", "disturb"}`, find the card in `player.graveyard` instead of `player.hand`; for flashback/disturb: exile card on resolution instead of moving to graveyard; for escape: exile the card + N additional graveyard cards specified in `req.targets`; for unearth: exile at end of turn (add to end-of-turn cleanup)
- [X] T040 [US11] In `_score_cast()` in `ai_client/heuristic_player.py`: detect `action.get("from_graveyard")` flag; add +10.0 bonus to any graveyard cast score to represent free-resource advantage per FR-036; detect `alternative_cost="escape"` and validate minimum graveyard size before offering positive score
- [X] T041 [US11] Update `_map_action_to_request()` in `ai_client/game_loop.py` to pass `alternative_cost` and `from_graveyard=True` for graveyard casts into `CastRequest`

**Checkpoint**: AI casts flashback/escape/unearth/disturb spells from graveyard.

---

## Phase 14: US12 — ETB and Dies Trigger Evaluation (Priority: P3)

**Goal**: Creatures with ETB draw/damage/token effects score higher than vanilla creatures of same CMC.

**Independent Test**: 2/2 with "draw a card on ETB" scores ≥15 points higher than vanilla 2/2.

- [X] T042 [P] [US12] Add `_ETB_DRAW_RE = re.compile(r'when.*enters.*draw (\d+) card|when.*enters.*draw a card', re.IGNORECASE)`, `_ETB_DAMAGE_RE = re.compile(r'when.*enters.*deals? (\d+) damage', re.IGNORECASE)`, `_ETB_TOKEN_RE = re.compile(r'when.*enters.*create.*token', re.IGNORECASE)`, `_DIES_VALUE_RE = re.compile(r'when.*dies.*draw|when.*dies.*create.*token', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T043 [US12] Add `_score_etb_bonus(oracle_text: str) -> float` and `_score_dies_bonus(oracle_text: str) -> float` to `ai_client/heuristic_player.py`: ETB draw N → `+N * 15.0`; ETB damage N → `+N * 5.0`; ETB token → `+15.0`; dies with draw/token → `+10.0` trade-willingness bonus; wire both into `_score_creature()` so every creature cast includes ETB/dies bonuses

**Checkpoint**: Creatures with ETB/dies effects score proportionally higher.

---

## Phase 15: US13 — Cross-Turn Memory (Priority: P3)

**Goal**: AI tracks revealed opponent cards and uses that info to deprioritize plays into known countermagic.

**Independent Test**: Opponent reveals Counterspell; AI has open mana window; AI deprioritizes casting its highest-value spell.

- [X] T044 [P] [US13] Extend `AIMemory` in `ai_client/models.py` with `add_revealed_card(player_name: str, card: dict)` and `get_revealed_cards(player_name: str) -> list[dict]` convenience methods; add `add_bounced(perm_id: str)`, `add_mandatory_attacker(perm_id: str)`, `clear_mandatory_attacker(perm_id: str)` methods
- [X] T045 [US13] Wire revealed-card tracking into `ai_client/game_loop.py`: when game log or API response indicates opponent played a card face-up (e.g., looting discard, forced reveal), call `memory.add_revealed_card()`; on game state updates where hand contents are visible, populate revealed cards
- [X] T046 [US13] In `_score_cast()` in `ai_client/heuristic_player.py`: when `self._memory` contains opponent revealed counterspells AND opponent has open mana matching the counter's cost, apply a `-20.0` penalty to the score of the AI's highest-value spell per FR-041; also update `bounced_this_turn` tracking: when a permanent the AI controlled reappears in its hand, add to `self._memory.bounced_this_turn` and exclude it from board position calculation

**Checkpoint**: AI avoids walking into known countermagic.

---

## Phase 16: US14 — Lookahead Simulation (Priority: P3)

**Goal**: AI simulates 1 turn ahead; ramp and sequencing actions get a bonus reflecting the future play they enable.

**Independent Test**: Cast ramp this turn + 5-drop next turn → ramp action gets +bonus vs. not casting ramp.

- [X] T047 [US14] Implement `_apply_action_to_state(action: dict, state: dict) -> dict` fully in `ai_client/lookahead.py`: deep-copy state; for `play_land`: add land to battlefield simulation, increment `lands_played`; for `cast`: remove card from simulated hand, add creature to simulated battlefield (non-creatures just removed from hand); for `pass`: do nothing; return modified state copy
- [X] T048 [US14] Implement `evaluate_bonus(current_action, game_state, memory) -> float` in `ai_client/lookahead.py`: apply `current_action` to a deep-copy of `game_state`; simulate next-turn legal actions by calling `self._heuristic_player._score_action()` on each hypothetical action in the resulting state; compute `best_future_score` from those; return `min(best_future_score * 0.3, 30.0)` as the lookahead bonus (scaled and capped at 30 per FR-044); only run lookahead when `action_type in {"play_land", "cast"}` to avoid spending time on pass/combat
- [X] T049 [US14] Wire `LookaheadSimulator` into `HeuristicPlayer.choose_action()` in `ai_client/heuristic_player.py`: instantiate `LookaheadSimulator(self)` once on first call and cache as `self._lookahead`; for each candidate action, add `self._lookahead.evaluate_bonus(action, game_state, memory)` to that action's score before final ranking

**Checkpoint**: AI considers 1-turn-ahead consequences when ranking actions.

---

## Phase 17: US15 — Control Gain and Life Gain Scoring (Priority: P3)

**Goal**: Control-steal spells score `stolen_CMC × 15`; life gain gets 2× bonus when AI ≤ 5 life.

**Independent Test**: Control spell targeting opponent 5/5 scores ≥75. Life gain at 4 life scores 2× vs 20 life.

- [X] T050 [P] [US15] Add `_score_control_gain(valid_targets, game_state, my_name) -> float` to `ai_client/heuristic_player.py`: find highest-CMC opponent permanent in `valid_targets`; return `target_cmc * 15.0`; if no valid targets return `-10.0`
- [X] T051 [US15] Add `_LIFEGAIN_RE = re.compile(r'you gain (\d+) life|gain (\d+) life', re.IGNORECASE)` to `ai_client/heuristic_player.py`; add `_score_life_gain(oracle_text, my_life) -> float`: extract N life gained; base score = `N * 3.0`; if `my_life <= 5` multiply by `2.0` per FR-046; wire `_score_control_gain()` when `_CONTROL_RE` matches and `_score_life_gain()` as bonus on spells matching `_LIFEGAIN_RE` into `_score_noncreature_spell()`

**Checkpoint**: Control and life gain spells score correctly based on game context.

---

## Phase 18: US16 — Holistic Board Position Evaluation (Priority: P3)

**Goal**: AI ranks actions by board position delta (before vs. after) not just individual action score.

**Independent Test**: Two actions with identical CMC but different board delta → AI picks higher delta action.

- [X] T052 [P] [US16] Add `_score_board_position(game_state: dict, player_name: str) -> float` to `ai_client/heuristic_player.py` implementing FR-048 formula: `sum(CMC of friendly permanents on battlefield) + (hand_size × 5) + (life × 0.5) - sum(CMC of opponent permanents) - (opp_hand_size × 5)`
- [X] T053 [US16] Integrate board-position delta into `choose_action()` in `ai_client/heuristic_player.py`: compute `before_score = _score_board_position(game_state, my_name)` once; for each action, after computing the individual action score, add `(estimated_after_position - before_score) * 0.2` as a delta modifier to rank sequencing choices; cap the delta modifier at ±15 to prevent it from overriding lethal/critical scores

**Checkpoint**: AI uses full board context, not just isolated action scores.

---

## Phase 19: US17 — AI Personality and Difficulty Profiles (Priority: P3)

**Goal**: Two distinct profiles ("default", "aggro") produce measurably different attack rates and counter behavior.

**Independent Test**: Aggro profile attacks into trades more often than default profile over 10 games.

- [X] T054 [P] [US17] Verify `AiPersonalityProfile` (from T003) is complete with all 13 boolean flags and 10 probability fields from spec FR-050/FR-051; verify `DEFAULT` constant has all defaults; verify `AGGRO` constant has `chance_to_attack_into_trade=0.8`, `attack_into_trade_when_tapped_out=True`, `chance_to_counter_cmc_1=0.0`, `chance_to_counter_cmc_2=0.25`, `token_generation_chance=0.9`
- [X] T055 [US17] Wire all personality profile properties into the scoring methods in `ai_client/heuristic_player.py`: in attack scoring, apply `self._profile.chance_to_attack_into_trade` as a threshold gating trade-into attacks; apply `self._profile.always_counter_*` booleans in counterspell logic (FR-015 area); apply `self._profile.token_generation_chance` multiplier in `_score_token_spell()`; apply `self._profile.hold_land_drop_for_main2_if_unused` in `_score_play_land()` to suppress land play in main-1 when no other plays exist
- [X] T056 [US17] Add `--personality` flag to CLI in `ai_client/__main__.py` parsing `"default"` or `"aggro"` (or custom JSON path); map to `AiPersonalityProfile.DEFAULT` / `AiPersonalityProfile.AGGRO` and store on `PlayerConfig.personality`

**Checkpoint**: Two profiles produce observably different AI behavior.

---

## Phase 20: US18 — Alternative Casting Costs: Convoke, Delve, Emerge (Priority: P3)

**Goal**: AI generates and uses Convoke, Delve, and Emerge cast actions when unable to pay normal costs.

**Independent Test**: Convoke spell with insufficient mana but 3 untapped creatures → Convoke cast offered and played.

- [X] T057 [P] [US18] Add Convoke legal action generation to `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`: detect `"convoke" in card.keywords`; enumerate untapped creatures the player controls; compute the reduced mana cost after tapping all available creatures; if cost ≤ 0 or payable, emit `action_type="cast"` with `alternative_cost="convoke"` and `valid_targets` listing creature IDs available to tap; add Convoke cast handler: tap specified creatures during cast resolution
- [X] T058 [P] [US18] Add Delve legal action generation to `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`: detect `"delve" in card.keywords`; count graveyard cards; emit `action_type="cast"` with `alternative_cost="delve"` when generic cost can be reduced to 0 by exiling graveyard cards; add Delve cast handler: exile specified graveyard card IDs from `req.targets`
- [X] T059 [P] [US18] Add Emerge legal action generation to `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`: detect `"emerge" in card.keywords`; for each friendly creature, compute reduced cost; if payable, emit `action_type="cast"` with `alternative_cost="emerge"` and sacrifice candidate in `valid_targets`; add Emerge cast handler: sacrifice the creature at `req.targets[0]` before resolving the spell
- [X] T060 [US18] Add `_score_convoke_tradeoff(action, game_state, my_name) -> float` to `ai_client/heuristic_player.py`: compare spell score vs sum of attacking-value of tapped creatures; only return positive if spell score > tapped creature attack value; add `_score_emerge_tradeoff()`: compare spell score vs sacrificed creature CMC; wire both into `_score_cast()` when `alternative_cost in {"convoke", "emerge"}`

**Checkpoint**: AI uses Convoke/Delve/Emerge when normal mana is insufficient.

---

## Phase 21: US19 — Token Generation Spell Scoring (Priority: P3)

**Goal**: Token-producing spells score based on total token power/toughness + keywords.

**Independent Test**: Spell creating two 2/2 tokens scores comparable to casting two 2/2 creatures.

- [X] T061 [P] [US19] Add `_TOKEN_RE = re.compile(r'create (\w+|\d+) (\d+/\d+|\*\*/\*\*)(?:\s+\w+)* tokens?', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T062 [US19] Add `_score_token_spell(oracle_text: str) -> float` to `ai_client/heuristic_player.py`: parse token count and P/T from `_TOKEN_RE`; score = `(total_power * 8.0 + total_toughness * 4.0) * self._profile.token_generation_chance`; add flying evasion bonus if token description includes "flying" (`+power * 8.0`); wire into `_score_noncreature_spell()` when `_TOKEN_RE` matches

**Checkpoint**: Token spells score above zero in all board states.

---

## Phase 22: US20 — Multiplayer Attack Direction (Priority: P3)

**Goal**: In 3+ player games, AI targets the opponent most advantageous to attack (lethal first, then biggest threat).

**Independent Test**: 4-player game; one opponent at 3 life with unblocked attacker → AI attacks them.

- [X] T063 [P] [US20] Add `_select_attack_direction(game_state: dict, my_name: str, attacking_power: int) -> str` to `ai_client/heuristic_player.py`: get all opponent player names from `game_state["players"]`; if any opponent's life ≤ attacking_power, return that player (lethal); else return the opponent with the highest sum of permanent CMC on battlefield per FR-064; currently `declare_attackers` always targets one opponent — extend to pass `defending_id` per opponent
- [X] T064 [US20] Wire `_select_attack_direction()` into `_score_attackers()` in `ai_client/heuristic_player.py`: when multiple opponents exist, call direction selector to determine which `defending_id` to assign in `AttackDeclaration`; update `compute_attack_declarations()` helper in `game_loop.py` to use the direction result

**Checkpoint**: AI attacks the correct opponent in multiplayer games.

---

## Phase 23: US21 — Transform and Meld Card Evaluation (Priority: P3)

**Goal**: DFC creatures score higher than front face alone when back face is more powerful.

**Independent Test**: DFC with 2/2 front / 5/5 back scores higher than vanilla 2/2.

- [X] T065 [P] [US21] Add `_score_transform_bonus(card: dict) -> float` to `ai_client/heuristic_player.py`: check `card.get("card_faces")` for DFC back face; compute delta = `(back_power - front_power) * 10.0 + (back_toughness - front_toughness) * 5.0`; return `max(0.0, delta)`; if transform condition string contains "if no spells were cast" or similar near-impossible condition, return `0.0` per FR-069
- [X] T066 [US21] Wire `_score_transform_bonus()` into `_score_creature()` in `ai_client/heuristic_player.py`; add meld bonus logic: when AI controls both meld pieces (detect via `card.get("all_parts")`), add `melded_cmc * 12.0` bonus per FR-070 to the second piece's cast score

**Checkpoint**: DFC and meld cards reflect their transformed value.

---

## Phase 24: US22 — Fog and Defensive Spell Recognition (Priority: P3)

**Goal**: AI holds Fog effects until opponent's attack step when incoming damage would be lethal.

**Independent Test**: AI at 2 life, opponent attacks for lethal; AI holds Fog until attack step then casts it.

- [X] T067 [P] [US22] Add `_FOG_RE = re.compile(r'prevent all combat damage|no combat damage', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T068 [US22] In `_score_cast()` in `ai_client/heuristic_player.py`: when `_FOG_RE` matches, score the spell at `-5.0` during the AI's own main phase (hold it); set `self._memory.chosen_fog_effect = card_id`; during the opponent's attack step when called with priority, evaluate Fog if `predicted_incoming_damage >= my_life - self._profile.phyrexian_life_threshold` (reuse attack prediction logic from US24 T076); in that case score at `200.0` (use it); clear `chosen_fog_effect` from memory after use
- [X] T069 [US22] In `ai_client/game_loop.py`: when `priority_player` is the AI and `step == "declare_attackers"` and `memory.chosen_fog_effect` is set, add Fog cast to the pool of evaluated actions at that window (do not auto-pass)

**Checkpoint**: AI holds Fog until lethal attack step.

---

## Phase 25: US23 — Artifact and Enchantment Removal Prioritization (Priority: P3)

**Goal**: Artifact/enchantment removal scores based on target CMC with urgency bonus for unblockable-granting permanents.

**Independent Test**: Opponent has threatening artifact (CMC 4); AI has destroy-artifact spell → scores positively and casts it.

- [X] T070 [P] [US23] Add `_ARTIFACT_REMOVAL_RE = re.compile(r'destroy target artifact|exile target artifact|destroy target enchantment|exile target enchantment', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T071 [US23] Add `_score_artifact_enchantment_removal(valid_targets, game_state) -> float` to `ai_client/heuristic_player.py`: find highest-CMC opponent artifact/enchantment in `valid_targets`; base score = `target_cmc * 10.0`; add `+15.0` if target oracle text contains draw/mana-add pattern (repeated value per turn); apply `×1.5` multiplier if target grants unblockable per FR-076; score equipment removal as `target_cmc * 10.0 + equipment_cmc * 5.0`; wire into `_score_noncreature_spell()` when `_ARTIFACT_REMOVAL_RE` matches and `self._profile.actively_destroy_artifacts_and_enchantments`

**Checkpoint**: AI actively removes threatening opponent artifacts and enchantments.

---

## Phase 26: US24 — Next-Turn Attack Prediction (Priority: P3)

**Goal**: AI predicts opponent's incoming damage next turn and prioritizes defense when it would be lethal.

**Independent Test**: Opponent has 10 power untapping next turn; AI at 9 life → AI prioritizes blocker/removal over offense.

- [X] T072 [P] [US24] Add `_predict_incoming_damage(game_state: dict, my_name: str) -> int` to `ai_client/heuristic_player.py`: sum power of all opponent creatures that will untap next turn (not tapped AND no summoning sickness next turn); add known pump spell bonuses from `self._memory.revealed_cards`; subtract total toughness of AI's available blockers (creatures that can block); return net incoming estimate
- [X] T073 [US24] In `choose_action()` in `ai_client/heuristic_player.py`: compute `predicted_damage = _predict_incoming_damage()` once per decision; if `predicted_damage >= my_life`: apply `-30.0` modifier to all offensive actions (cast creature for offense, attack) and `+30.0` to all defensive actions (block setup, removal of biggest attacker, blocker development); store prediction result for Fog evaluation (US22)

**Checkpoint**: AI correctly shifts to defensive mode when lethal attack is incoming next turn.

---

## Phase 27: US25 — Animate Land and Artifact Scoring (Priority: P3)

**Goal**: Animate effects score based on the resulting animated creature's P/T and keywords.

**Independent Test**: Animate-land-into-3/3 spell scores ≥ casting a vanilla 3/3 creature.

- [X] T074 [P] [US25] Add `_ANIMATE_RE = re.compile(r'becomes? a (\d+)/(\d+) creature|animate target', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T075 [US25] Add `_score_animate(oracle_text: str, targets: list[str], game_state: dict) -> float` to `ai_client/heuristic_player.py`: extract animated P/T from `_ANIMATE_RE` match; score = `power * 8.0 + toughness * 4.0` plus applicable keyword bonuses; if animating a land already on battlefield (from `valid_targets` matching a land permanent), treat as "free" creature; wire into `_score_noncreature_spell()` and `_score_activate()` when `_ANIMATE_RE` matches; record in `self._memory.animated_this_turn`

**Checkpoint**: AI correctly values animate effects.

---

## Phase 28: US26 — Library Search and Tutor Scoring (Priority: P3)

**Goal**: Tutor spells score based on the best card they can find given current game state.

**Independent Test**: Tutor (find any creature) scores above "pass priority" when deck has high-CMC creatures.

- [X] T076 [P] [US26] Add `_TUTOR_RE = re.compile(r'search your library for (?:a |an |any )?(\w+(?:\s\w+)?)\s*(?:card|spell)', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T077 [US26] Add `_score_tutor(oracle_text: str, game_state: dict, my_name: str) -> float` to `ai_client/heuristic_player.py`: extract card type restriction from `_TUTOR_RE` (e.g., "creature", "land", "instant"); find the highest-CMC card matching that type in the AI's deck (use `game_state.get("deck_contents", [])` if available, else default to `spell_cmc * 10.0` for generic tutors per FR-087); add urgency bonus based on game state: if `my_life <= 10` prefer removal/blocker; wire into `_score_noncreature_spell()` when `_TUTOR_RE` matches

**Checkpoint**: AI casts tutors and fetches the contextually best card.

---

## Phase 29: US27 — Fight Mechanic Scoring (Priority: P3)

**Goal**: Fight spells score positively when AI creature kills the target and survives; negatively otherwise.

**Independent Test**: 5/5 fights 3/3 → positive score. 1/1 fights 5/5 → negative score.

- [X] T078 [P] [US27] Add `_FIGHT_RE = re.compile(r'target creature you control fights target creature|each deals damage equal to its power', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T079 [US27] Add `_score_fight(valid_targets: list[str], game_state: dict, my_name: str) -> float` to `ai_client/heuristic_player.py`: for each pair of (friendly fighter, opponent target), compute outcome — SAFE if friendly_power ≥ opp_toughness AND opp_power < friendly_toughness; TRADE if mutual lethal; UNSAFE if only friendly dies; score SAFE = `opp_cmc * 10.0 + 15.0`; TRADE = `(opp_cmc - friend_cmc) * 10.0`; UNSAFE = `-friend_cmc * 8.0`; select the pair with best score and store in `action["chosen_target"]`; wire into `_score_activate()` when ability description contains fight pattern

**Checkpoint**: AI correctly uses fight effects as targeted removal.

---

## Phase 30: US28 — Goad Evaluation (Priority: P3)

**Goal**: Goad scores based on CMC of goaded creature; AI tracks goaded creatures as mandatory attackers.

**Independent Test**: Goad opponent's 5/5 → scores positively; goaded creature removed from AI's blocker calculations.

- [X] T080 [P] [US28] Add `_GOAD_RE = re.compile(r'goad target creature|goaded', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T081 [US28] Add `_score_goad(valid_targets: list[str], game_state: dict) -> float` to `ai_client/heuristic_player.py`: target the highest-CMC opponent creature; score = `target_cmc * 8.0` (× 1.5 in multiplayer games with 3+ players per FR-091); store goaded creature ID in `self._memory.mandatory_attackers`; wire into `_score_activate()` and `_score_noncreature_spell()` when `_GOAD_RE` matches
- [X] T082 [US28] In blocker calculation (`compute_block_declarations()` in `ai_client/heuristic_player.py`): exclude creature IDs in `memory.mandatory_attackers` from the opponent's available blocker pool (goaded creatures must attack, so they cannot block per MTG rules)

**Checkpoint**: AI uses goad tactically and accounts for it in blocker calculations.

---

## Phase 31: US29 — Connive, Explore, and Mutate Evaluation (Priority: P3)

**Goal**: AI makes informed discard (Connive), library manipulation (Explore), and base selection (Mutate) decisions.

**Independent Test**: Connive triggers; AI discards highest-CMC uncastable card, not lowest-CMC.

- [X] T083 [P] [US29] Add `_CONNIVE_RE = re.compile(r'connive', re.IGNORECASE)`, `_EXPLORE_RE = re.compile(r'explore', re.IGNORECASE)`, `_MUTATE_RE = re.compile(r'mutate', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T084 [US29] Add `_select_connive_discard(hand: list[dict], current_turn: int) -> str` to `ai_client/heuristic_player.py` per FR-093: return the card with highest CMC that cannot be cast within the next 2 turns given current mana; if all cards are castable, return a redundant land (when ahead on mana); wire into `ChoiceRequest` handler in `game_loop.py` for connive discard events
- [X] T085 [US29] Add `_select_explore_outcome(revealed_card: dict, my_land_count: int, needed_lands: int) -> str` to `ai_client/heuristic_player.py` per FR-094: if revealed is a land and `my_land_count < needed_lands`: return `"land"` (put onto battlefield); else return `"hand"` (put in hand); wire into `ChoiceRequest` handler for explore events; add `_select_mutate_target(valid_targets, game_state, mutating_card) -> str` per FR-095: return creature ID that maximizes combined resulting P/T; wire into `_select_best_target()` for mutate cast actions

**Checkpoint**: AI makes correct Connive/Explore/Mutate decisions.

---

## Phase 32: US30 — Remove From Combat Effects (Priority: P3)

**Goal**: AI uses tap-attacker and remove-blocker effects at the right combat timing.

**Independent Test**: AI being attacked by 6/6 with no blockers; has "tap target attacker" instant → casts it to prevent damage.

- [X] T086 [P] [US30] Add `_REMOVE_COMBAT_RE = re.compile(r'tap target attacking|remove target blocking|target creature loses all abilities until end of combat', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T087 [US30] Add `_score_remove_from_combat(oracle_text: str, game_state: dict, my_name: str) -> float` to `ai_client/heuristic_player.py`: for tap-attacker effects targeting opponent's attacking creature: score = `attacker_power * 6.0` if that damage would otherwise be unblocked; for remove-blocker effects: score = `blocked_attacker_power * 5.0` representing unblocked damage enabled; select best target via `_select_best_target()`; wire into `_score_noncreature_spell()` and `_score_activate()` when `_REMOVE_COMBAT_RE` matches; hold these instants for combat window (same logic as combat tricks in US2)

**Checkpoint**: AI uses remove-from-combat effects at combat timing.

---

## Phase 33: US31 — Cascade Trigger Decisions (Priority: P3)

**Goal**: When cascade fires, AI evaluates the cascaded card and casts it if score > 0.

**Independent Test**: Cascade into Lightning Bolt → AI casts it. Cascade into uncastable card → AI skips.

- [X] T088 [P] [US31] Add cascade trigger detection to `mtg_engine/engine/stack.py`: when a spell with `"cascade" in card.keywords` resolves, implement the cascade procedure — exile cards from top of library until finding a non-land card with `CMC < cascading_spell_cmc`; set `gs.cascade_pending = CascadePendingState(player_name, card, exiled_cards)` on `GameState`; add `"cascade_choice"` legal action emission in `_compute_legal_actions()` when `gs.cascade_pending` is set
- [X] T089 [US31] Add `POST /game/{game_id}/cascade-choice` endpoint to `mtg_engine/api/routers/game.py`: validate `gs.cascade_pending` exists; if `cast=True`: put the cascade card on the stack for free; if `cast=False` or cast is invalid: exile the cascade card; clear `gs.cascade_pending`; return resolution status
- [X] T090 [US31] In `ai_client/heuristic_player.py` `_score_action()`: add handler for `action_type="cascade_choice"`: score the cascade card using normal `_score_cast()` logic; if score > 0 return score (cast it); else return -1.0 (skip); update `_map_action_to_request()` in `game_loop.py` to handle cascade_choice → `CascadeChoiceRequest`

**Checkpoint**: AI resolves cascade triggers correctly.

---

## Phase 34: US32 — Delayed Trigger Handling (Priority: P3)

**Goal**: Delayed triggers fire at correct timing; their future value is included in the original spell's score.

**Independent Test**: Spell with "draw a card next upkeep" delayed trigger → spell score includes +15 draw bonus.

- [X] T091 [P] [US32] Add `_DELAYED_DRAW_RE = re.compile(r'at the beginning of (?:your )?next (?:upkeep|draw step).*draw (\d+) card|draw a card', re.IGNORECASE)` and `_DELAYED_DAMAGE_RE = re.compile(r'at the beginning of (?:your )?next (?:upkeep).*deals? (\d+) damage', re.IGNORECASE)` to `ai_client/heuristic_player.py`
- [X] T092 [US32] Add `_score_delayed_trigger_bonus(oracle_text: str) -> float` to `ai_client/heuristic_player.py`: extract delayed draw count → `+N * 15.0`; extract delayed damage count → `+N * 5.0`; return sum; wire as an additive bonus in `_score_noncreature_spell()` and `_score_creature()` when delayed trigger patterns are detected; in `game_loop.py` when a delayed trigger fires (engine sends `put_trigger` action for a delayed trigger), use same target selection heuristics as immediate effect targeting

**Checkpoint**: Delayed trigger value is reflected in original spell scores.

---

## Phase 35: US33 — Life Payment Cost Evaluation (Priority: P3)

**Goal**: AI pays Phyrexian mana (2 life) only when no colored mana available and life > threshold.

**Independent Test**: Phyrexian mana spell; AI has colored mana → pays colored, not life. AI has no colored mana + 10 life → pays 2 life.

- [X] T093 [P] [US33] Add Phyrexian mana detection to `mtg_engine/card_data/ability_parser.py` and `mtg_engine/engine/mana.py`: recognize `{W/P}`, `{U/P}`, `{B/P}`, `{R/P}`, `{G/P}` symbols in mana cost strings; in `can_pay_cost()` treat Phyrexian symbols as payable either with 1 colored mana OR 2 life
- [X] T094 [US33] Add Phyrexian alternative cost legal action generation in `_compute_legal_actions()` in `mtg_engine/api/routers/game.py`: when a card has Phyrexian mana symbols, emit a second `action_type="cast"` with `alternative_cost="phyrexian"` when the player lacks colored mana but has `life > 2`; add cast handler that deducts 2 life per Phyrexian symbol from `req.alternative_cost="phyrexian"` casts
- [X] T095 [US33] In `_score_cast()` in `ai_client/heuristic_player.py`: when `alternative_cost="phyrexian"`, apply life-threshold check: if `my_life <= self._profile.phyrexian_life_threshold + 2` return -999.0 (don't pay); if `my_life > phyrexian_life_threshold + 2` add `life_cost * -1.0` as a penalty but allow the cast; never pay life when the AI has sufficient colored mana (prefer normal cost action if both exist)

**Checkpoint**: AI correctly decides when to pay life for Phyrexian mana.

---

## Phase 36: US34 — Stack-Aware Non-Counter Responses and Spell Copying (Priority: P3)

**Goal**: AI activates instant-speed protection (pump to save creature from removal) and copies high-value opponent spells.

**Independent Test**: Opponent targets AI's creature with removal; AI holds +4/+4 instant → AI pumps in response.

- [X] T096 [P] [US34] In `ai_client/game_loop.py`: in the priority-granting loop, when `priority_player == ai_player_name` and `step` is NOT a combat step (i.e., opponent's main phase or stack has items), do NOT auto-pass; instead call `player.choose_action()` with the full legal actions list including any instant-speed responses — currently this window is auto-passed
- [X] T097 [US34] Add stack-response scoring to `ai_client/heuristic_player.py`: in `_score_cast()`, when `action.get("responding_to_stack_item")` is set (engine annotates if a spell is being targeted), score pump instants that would make the creature survive the targeting effect at `saved_creature_cmc * 12.0`; detect by checking if `valid_targets` includes a friendly creature currently targeted on the stack
- [X] T098 [US34] Add `CopySpellRequest` wiring to `ai_client/game_loop.py`: `CopySpellRequest` already exists in `mtg_engine/models/actions.py`; wire `action_type="copy_spell"` → `CopySpellRequest` in `_map_action_to_request()`; in `_score_action()`: score copy actions as `(copied_spell_score * 0.9)` where `copied_spell_score` is the score of the copied spell using normal cast scoring; add copy_spell to legal action generation in game.py when a copiable spell is on the stack and AI controls a copy effect

**Checkpoint**: AI protects its permanents from removal and copies high-value opponent spells.

---

## Phase 37: US35 — Make-Opponent-Lose-Life Scoring (Priority: P3)

**Goal**: "Target opponent loses N life" spells score identically to N damage burn spells.

**Independent Test**: "Loses 3 life" spell vs opponent at 3 life → lethal-first targeting, scores as lethal.

- [X] T099 [P] [US35] Ensure `_LIFE_LOSS_RE` (added in T012) correctly captures `(\d+)` life loss amount; add `_score_life_loss(oracle_text: str, opp_life: int) -> float` to `ai_client/heuristic_player.py`: extract N; if `N >= opp_life` return `10000.0` (lethal); else return `(N / opp_life) * 40.0`; identical formula to burn per FR-104
- [X] T100 [US35] Wire `_score_life_loss()` into `_score_noncreature_spell()` in `ai_client/heuristic_player.py` when `_LIFE_LOSS_RE` matches; ensure `_select_best_target()` sets target to opponent player for life-loss effects (target players, not creatures); confirm that existing burn scoring does not double-count if a spell has both damage and life-loss text

**Checkpoint**: Life-loss spells are treated equivalently to burn for scoring purposes.

---

## Phase 38: US36 — Safe Block Classification (Priority: P3)

**Goal**: Blocking assigns SAFE > TRADE > CHUMP classification and prefers higher-quality blocks.

**Independent Test**: 3/3 blocks 2/2 → SAFE classification; preferred over chump blocking the same attacker with a 1/1.

- [X] T101 [P] [US36] Add `_classify_block(blocker: dict, attacker: dict) -> BlockClassification` to `ai_client/heuristic_player.py`: SAFE if `blocker_power >= attacker_toughness AND attacker_power < blocker_toughness`; TRADE if both die (mutual lethal); CHUMP if only blocker dies; handle deathtouch (any damage is lethal) via `_card_has_kw()`
- [X] T102 [US36] Refactor `compute_block_declarations()` in `ai_client/heuristic_player.py` to use `_classify_block()`: for each attacker, collect all possible single-blocker options with their `BlockClassification`; prefer SAFE blocks over TRADE, TRADE over CHUMP; only assign CHUMP blocks when `must_survive=True` (lethal incoming) and no SAFE/TRADE block exists; update gang-block logic to classify combined-blocker scenarios as SAFE when combined power ≥ attacker toughness

**Checkpoint**: All block assignments prefer SAFE > TRADE > CHUMP correctly.

---

## Phase 39: Polish and Cross-Cutting Concerns

**Purpose**: Integration verification, regression check, performance validation, and cleanup.

- [X] T103 Run full test suite from project root: `python -m pytest tests/ -v` — verify all 376 existing tests still pass (SC-009 zero regressions)
- [X] T104 Performance validation: create a board state with 6 lands and 4 permanents per player; call `HeuristicPlayer.choose_action()` and time it; verify total decision time including lookahead is under 500ms (SC-010); if over budget, profile and optimize the slowest scoring method
- [X] T105 [P] Verify SC-001 through SC-027 acceptance criteria manually: for each success criterion, construct the described board state and confirm the AI makes the correct decision; document any that fail and create follow-up fixes
- [X] T106 [P] Add `AiPersonalityProfile` YAML-loading utility to `ai_client/models.py`: `from_dict(d: dict) -> AiPersonalityProfile` factory method for runtime profile customization without code changes
- [X] T107 Run linting: `ruff check .` from project root; fix all lint errors introduced by this feature
- [X] T108 Update `CLAUDE.md` via `.specify/scripts/bash/update-agent-context.sh claude` to record final technology additions from this feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundation)**: Depends on Phase 1 — **BLOCKS all user story phases**
  - T002, T003, T004, T005 are parallel (different files)
  - T006 depends on T002 and T003
  - T007 depends on T006
  - T008 is parallel with T006/T007
- **Phases 3–38 (User Stories)**: All depend on Phase 2 completion
- **Phase 39 (Polish)**: Depends on all desired user story phases being complete

### User Story Dependencies

Most user stories are independent after Phase 2. Key sequencing:

- **US1 (Target Selection)** — blocks nothing but enhances US3/US5/US7/US15/US23/US27/US28/US29 scoring accuracy
- **US2 (Combat Tricks)** — independent; US28 (Goad) T082 enhances it
- **US13 (Cross-Turn Memory)** — AIMemory from Phase 2 (T002) is the only dependency; T044 is light extension
- **US14 (Lookahead)** — depends on T008 (LookaheadSimulator stub); T047-T049 complete the implementation
- **US17 (Personality)** — T003 (AiPersonalityProfile from Phase 2) must be complete; T054-T056 wire it in
- **US22 (Fog)** — references US24 (Attack Prediction T072) for the `predicted_damage` calculation; implement US24 first or stub the call
- **US36 (Safe Block)** — T004 (BlockClassification enum from Phase 2) must be complete

### Parallel Opportunities Within Each Phase

- All `[P]`-marked tasks touch different files and can run in parallel
- Phase 2: T002, T003, T004, T005 all parallel (different areas of models)
- Phases 9-12, 17, 19-23, 25-32, 35, 37-38: All are `[P]` regex/scoring additions to `heuristic_player.py` — each adds a new method + regex constant without touching existing code

---

## Parallel Example: Phase 2 Foundation

```bash
# All four can launch simultaneously:
Task T002: "Add AIMemory dataclass to ai_client/models.py"
Task T003: "Add AiPersonalityProfile dataclass to ai_client/models.py"
Task T004: "Add BlockClassification enum to ai_client/models.py"
Task T005: "Extend LegalAction and add new request models in mtg_engine/models/actions.py"

# After T002+T003 complete:
Task T006: "Wire AiPersonalityProfile into PlayerConfig and HeuristicPlayer"
Task T008: "Create ai_client/lookahead.py LookaheadSimulator stub"  # parallel with T006
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only — 2 stories)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundation (T002–T008)
3. Complete Phase 3: US1 Target Selection (T009–T012)
4. Complete Phase 4: US2 Combat Tricks (T013–T016)
5. **STOP and VALIDATE**: Run existing tests; observe AI picking correct targets and holding instants
6. Demo: AI vs AI game — verify removal hits the biggest threat and Fog/pump instants are held for combat

### Incremental Delivery Order (Recommended)

1. Foundation → US1 → US2 (P1 stories — biggest correctness wins)
2. US3, US5 (scoring improvements — quick wins, just heuristic_player.py)
3. US4, US6 (engine changes — planeswalker + mulligan)
4. US7–US12 (P3 scoring cluster — all heuristic_player.py additions)
5. US13–US16 (memory, lookahead, board position — AI intelligence improvements)
6. US17–US38 (remaining P3 stories — parallel-friendly additions)

### Full Parallel Strategy

With 2 developers after Phase 2 completes:
- **Dev A**: Engine-side stories (US4, US6, US11, US18, US31, US33, US34)
- **Dev B**: Scoring-side stories (US1, US2, US3, US5, US7–US10, US12–US17, US19–US30, US32, US35–US36)

---

## Notes

- `[P]` = different files or new methods, no conflicts with concurrent tasks
- Tasks in Phases 9–38 that are `[P]` each add a new regex constant and scoring method to `heuristic_player.py` — they don't modify existing methods (append-only until the wire-in step)
- Wire-in steps (integrating new scoring into dispatcher) should be done in one pass per session to avoid merge conflicts on `_score_action()` and `_score_noncreature_spell()`
- Always run `python -m pytest tests/ -v` after each phase to catch regressions early
- Commit after each complete user story phase
- The `_score_action()` dispatcher and `_score_noncreature_spell()` sub-dispatch are the two integration hotspots — coordinate additions to these methods carefully

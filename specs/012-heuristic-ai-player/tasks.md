# Tasks: Heuristic AI Player

**Input**: Design documents from `/specs/012-heuristic-ai-player/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend PlayerConfig model and establish the player factory pattern that all stories depend on.

- [X] T001 Add `player_type: str = "llm"` optional field to `PlayerConfig` dataclass in `ai_client/models.py`
- [X] T002 Add optional `legal_actions: list[dict] | None = None` and `game_state: dict | None = None` kwargs to `AIPlayer.decide()` in `ai_client/ai_player.py` (ignored by AIPlayer; ensures forward-compat)
- [X] T003 Update `GameLoop.run()` in `ai_client/game_loop.py` to pass `legal_actions` and `game_state` kwargs when calling `ai_player.decide()`

**Checkpoint**: `AIPlayer` still works identically; `PlayerConfig` has `player_type`; `GameLoop` passes structured data to `decide()`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core HeuristicPlayer scaffold and scoring infrastructure that User Stories 2 and 3 depend on.

**⚠️ CRITICAL**: Phases 3+ depend on this phase being complete.

- [X] T004 Create `ai_client/heuristic_player.py` with `HeuristicPlayer` class skeleton: `__init__(config: PlayerConfig)`, mutable `_debug_callback = None`, stub `decide(prompt, legal_actions=None, game_state=None) -> tuple[int, str]` returning `(0, "heuristic fallback")`
- [X] T005 [P] Implement `_extract_my_info(game_state, my_name) -> dict` helper in `ai_client/heuristic_player.py`: extracts the priority player's `PlayerState` dict (life, mana_pool, hand) from `game_state["players"]`
- [X] T006 [P] Implement `_extract_battlefield(game_state, controller) -> list[dict]` helper in `ai_client/heuristic_player.py`: filters `game_state["battlefield"]` by controller name, returns list of permanent dicts
- [X] T007 [P] Implement `_cmc(mana_cost: str) -> int` helper in `ai_client/heuristic_player.py`: parses mana cost strings like `"{2}{G}{G}"` into converted mana cost integer
- [X] T008 [P] Implement `_has_keyword(card: dict, keyword: str) -> bool` helper in `ai_client/heuristic_player.py`: checks `card.get("keywords", [])` and oracle text for a given keyword string
- [X] T009 Implement `_score_action(action, game_state, my_name) -> float` in `ai_client/heuristic_player.py` with base scoring logic: `play_land` → 50, `put_trigger` → 30, `activate` (non-mana) → 20, `pass` → 0; delegates `cast`, `declare_attackers`, `declare_blockers` to sub-scorers (stubbed to return 25 initially)

**Checkpoint**: `HeuristicPlayer` can be instantiated and returns a valid (index, reasoning) for any legal action list

---

## Phase 3: User Story 1 - Start a Game With a Heuristic Opponent (Priority: P1) 🎯 MVP

**Goal**: Users can start any player-type combination using CLI flags; heuristic player completes games with no LLM calls.

**Independent Test**: `python -m ai_client --player "Bot1,," --player "Bot2,," --player1-type heuristic --player2-type heuristic --max-turns 0` completes to a winner without any HTTP calls to an LLM endpoint.

### Implementation for User Story 1

- [X] T010 [US1] Add `--player1-type {llm,heuristic}` and `--player2-type {llm,heuristic}` argparse flags (default `llm`) to `ai_client/__main__.py`
- [X] T011 [US1] Add `_make_player(config: PlayerConfig) -> AIPlayer | HeuristicPlayer` factory function in `ai_client/__main__.py`: returns `HeuristicPlayer(config)` when `player_type == "heuristic"`, else `AIPlayer(config)`
- [X] T012 [US1] Replace `[AIPlayer(pc) for pc in config.players]` with `[_make_player(pc) for pc in config.players]` in `ai_client/__main__.py`
- [X] T013 [US1] Wire `--player1-type` / `--player2-type` values into `PlayerConfig.player_type` for the corresponding player in `ai_client/__main__.py`
- [X] T014 [US1] Update `GameLoop.__init__` type annotation in `ai_client/game_loop.py` from `list[AIPlayer]` to `list[AIPlayer | HeuristicPlayer]` (or `list` for duck typing)
- [X] T015 [US1] Validate in `__main__.py`: when `player_type == "llm"`, require non-empty url and model; when `player_type == "heuristic"`, allow empty url/model with no error

**Checkpoint**: `python -m ai_client --player "B1,," --player "B2,," --player1-type heuristic --player2-type heuristic` starts a game; HeuristicPlayer's stub `decide()` returns pass; game runs to max-turns without crashing.

---

## Phase 4: User Story 2 - Competitive Heuristic Decisions (Priority: P2)

**Goal**: HeuristicPlayer makes optimal, competitive decisions: maximises mana, selects best spells, attacks for lethal, makes favourable trades, blocks strategically.

**Independent Test**: Run heuristic-vs-heuristic for 5 games; observe that both players develop boards, deal combat damage, and games resolve to a winner — with the winning player having exploited a combat or mana advantage.

### Implementation for User Story 2

- [X] T016 [US2] Implement `_score_cast(action, game_state, my_name) -> float` in `ai_client/heuristic_player.py`: base = `_cmc(mana_cost) × 10`; +20 if creature power ≥ 3; +15 for each of: trample, deathtouch, lifelink, flying; ×1.5 aggression multiplier if opponent life ≤ 6; returns score
- [X] T017 [US2] Wire `_score_cast` into `_score_action` for `action_type == "cast"` replacing the stub return of 25
- [X] T018 [US2] Implement `_simulate_combat(attacker_perms, blocker_perms, opp_life) -> float` in `ai_client/heuristic_player.py`: returns 10,000 if sum(attacker power) ≥ opp_life (lethal); otherwise iterates attackers and estimates likely blocker assignment; score = sum of (blocker CMC × 10) for favourable kills minus (attacker CMC × 8) for unfavourable deaths; returns net score
- [X] T019 [US2] Implement `_score_declare_attackers(action, game_state, my_name) -> float` in `ai_client/heuristic_player.py`: extracts attacker permanent IDs from `action["valid_targets"]`; retrieves attacker permanents from battlefield; retrieves opponent's untapped creatures as potential blockers; calls `_simulate_combat`; returns result (positive = attack, negative = hold back → cap at 0 meaning pass is preferred)
- [X] T020 [US2] Wire `_score_declare_attackers` into `_score_action` for `action_type == "declare_attackers"`
- [X] T021 [US2] Implement `_score_declare_blockers(action, game_state, my_name) -> float` in `ai_client/heuristic_player.py`: retrieve incoming attacker power totals from battlefield; if total unblocked damage ≥ my life → return 1,000 (must block); else score favourable trades (attacker CMC > blocker CMC and blocker survives or kills attacker); return net score
- [X] T022 [US2] Wire `_score_declare_blockers` into `_score_action` for `action_type == "declare_blockers"`
- [X] T023 [US2] Implement `decide()` body in `ai_client/heuristic_player.py`: iterate `legal_actions`, score each via `_score_action`, select index of highest score; build `reasoning` string: `f"Heuristic: {action_desc} (score={score:.1f})"` ; return `(best_index, reasoning)`
- [X] T024 [US2] Add land-play scoring to `_score_action` in `ai_client/heuristic_player.py`: `play_land` base score 50 but bump to 80 if player has 0 lands on battlefield (first land is critical)

**Checkpoint**: HeuristicPlayer reliably plays lands, casts best available creatures, attacks for lethal when possible, and makes strategic blocking decisions. Heuristic-vs-heuristic games complete with active board development.

---

## Phase 5: User Story 3 - Mixed Game Configurations via CLI (Priority: P3)

**Goal**: All three player-type combinations work via CLI flags with documented help text and proper validation.

**Independent Test**: Run each of the three combinations (heuristic vs heuristic, heuristic vs LLM, LLM vs LLM); confirm each starts, plays, and terminates cleanly. Run `python -m ai_client --help` and verify player-type flags are listed with descriptions.

### Implementation for User Story 3

- [X] T025 [US3] Add descriptive `help=` text to `--player1-type` and `--player2-type` argparse flags in `ai_client/__main__.py`: e.g. `"Decision engine for player 1: llm (calls LLM endpoint) or heuristic (local rule-based, no API calls)"`
- [X] T026 [US3] Update startup banner in `ai_client/game_loop.py` to display player type alongside name and model: e.g. `"Alice (devstral @ http://... [LLM])"` or `"Bot (heuristic [no LLM])"` so the user can confirm configuration at launch
- [X] T027 [US3] Verify heuristic-vs-LLM game: update `GameLoop` to skip `_forwarder.post_entry` for heuristic players (no prompt/response to forward) — check `isinstance(ai_player, HeuristicPlayer)` before posting debug entry in `ai_client/game_loop.py`

**Checkpoint**: All three combinations run cleanly; help text documents both flags; startup banner shows player types; debug panel is unaffected for LLM players.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T028 [P] Add `heuristic_player` import to `ai_client/__init__.py` if it exists, for clean package exports
- [X] T029 Add `HeuristicPlayer` to `CLAUDE.md` active technologies section to document the new player type
- [X] T030 Run `python -m ai_client --player "B1,," --player "B2,," --player1-type heuristic --player2-type heuristic --max-turns 0` and verify game completes to a winner with board development visible in output
- [X] T031 Run existing LLM invocation (if endpoints available) and confirm backwards-compatible behaviour is unchanged

---

## Phase 7: Bug Fixes (Post-Launch)

**Issues discovered during gameplay testing.**

- [X] T032 Fix combat trick timing in `ai_client/heuristic_player.py`: add `_is_combat_trick(card) -> bool` (instant with pump oracle text), `_current_step()`, `_has_attackable_creatures()` helpers; in `_score_cast()` penalise pump instants with -50 when not in combat and no attackers available, +40 during combat, +15 pre-combat with ready attacker — prevents Giant Growth being wasted in main phase with nothing to fight
- [X] T033 Extract `compute_block_declarations(action, game_state) -> list[dict]` as a module-level function in `ai_client/heuristic_player.py` (also extract `_perm_power`, `_perm_toughness`, `_cmc_str` as module-level helpers) so all player types benefit from smart blocking — previously only heuristic players sent real `block_declarations`, all others always sent `[]`
- [X] T034 Update `ai_client/game_loop.py` to call `compute_block_declarations` for ALL player types (not just `HeuristicPlayer`) when submitting a `declare_blockers` action — removes the `isinstance(ai_player, HeuristicPlayer)` guard
- [X] T035 Fix `_score_cast` in `ai_client/heuristic_player.py` — add `_has_any_creatures(game_state, my_name) -> bool` helper; for combat tricks, check this first and return -100 if the player controls no creatures (engine may still offer the action if opponent has creatures, but buffing an opponent's creature is never correct)
- [X] T036 Fix `_simulate_combat` in `ai_client/heuristic_player.py` — rewrite blocker simulation to model opponent's optimal response: find cheapest blocker that can KILL our attacker (`blk_power >= att_toughness`); mutual kill scores `(att_cmc - blk_cmc) × 8`; attacker-only death scores `-att_cmc × 8`; chump block scores `+blk_cmc × 8`; unblocked scores `+att_power × 10`; add +5 aggression bonus when net ≥ 0 to break ties with pass — previously inverted logic caused bots to never attack
- [X] T037 Fix infinite `declare_blockers` loop — add `blockers_declared: bool = False` to `CombatState` in `mtg_engine/models/game.py`; set to `True` in `combat.py:declare_blockers()`; reset in `turn_manager.py:advance_step()`; guard in `game.py` legal-actions with `not gs.combat.blockers_declared` — same pattern as `damage_assigned` fix
- [X] T038 Fix Giant Growth cast in upkeep — restrict `+15` pre-combat bonus in `_score_cast` to `phase == "precombat_main"` only; return `-50` for any other non-combat step (upkeep, draw, postcombat_main) to prevent wasting pump spells outside of combat windows

## Phase 8: Forge-Inspired Heuristic Improvements (Post-Launch)

**Analysis of CardForge AI source revealed significant gaps in combat and card evaluation heuristics.**

- [X] T039 Add `_can_block(blocker, attacker) -> bool` module-level helper in `ai_client/heuristic_player.py` — checks flying evasion (blocker needs flying or reach to block a flier); wire into `_simulate_combat` to filter eligible blockers per attacker and into `compute_block_declarations` to exclude illegal blockers
- [X] T040 Forge-style keyword multipliers in `_score_cast` in `ai_client/heuristic_player.py` — replace flat `+15` per keyword with: flying `power × 8`; double strike `10 + power × 10`; first strike `5 + power × 3`; deathtouch fixed 25; lifelink `power × 5`; trample `(power-1) × 4`; haste `power × 4`; vigilance `power × 3 + toughness × 3`; indestructible fixed 40; hexproof fixed 20; shroud fixed 15
- [X] T041 Life-pressure clock scaling in `_score_declare_attackers` in `ai_client/heuristic_player.py` — add pressure bonus `(10 - opp_life) × 4` when `opp_life ≤ 10`; at `opp_life ≤ 5` accept small unfavourable trades (`score > -30 → floor to 10`); near-lethal evasion swing detection; `×1.2` race multiplier when our life is lower than opponent's
- [X] T042 Gang block tier in `compute_block_declarations` in `ai_client/heuristic_player.py` — after single-blocker check fails, try 2-blocker combinations: if `combined_power >= att_toughness` and `att_cmc >= blk1_cmc + blk2_cmc` (or lethal incoming), assign both blockers to the attacker; mirrors Forge `makeGangBlocks` tier

## Phase 9: Forge Parity — Full Heuristic Improvements

**Gap analysis of Forge AI source identified additional missing combat math and spell categorisation.**

- [X] T043 Fix `_score_declare_blockers` evasion filter — add `_can_block(blk, att)` check to `my_creatures` loop so non-fliers are never considered as trades against flying attackers; also add deathtouch awareness: `_card_has_kw(blk.card, "deathtouch")` makes any blocker a killing blocker, `att_has_dt` means any attacker kills any blocker
- [X] T044 Deathtouch in `_simulate_combat` — for the killing-blocker search: if blocker has deathtouch, treat as killing (power ≥ 1 suffices); if our attacker has deathtouch, treat as killing any blocker regardless of power vs toughness check
- [X] T045 Trample bleed in `_simulate_combat` — when attacker has trample and opponent chumps, add `max(0, att_power - blk_toughness) × 6` excess damage to net score (unblocked damage to player)
- [X] T046 First-strike awareness in `_simulate_combat` — if blocker has first/double strike and attacker does not, set `attacker_kills_blocker = False` (blocker kills attacker before retaliation); if attacker has first/double strike, it kills blocker before taking damage (use normal power check)
- [X] T047 Selective attacking via `HeuristicPlayer.select_attackers(action, game_state, my_name) -> list[str]` — greedy subset selection: score full group, if positive send all; otherwise remove lowest-marginal-contribution attacker iteratively until score ≥ 0; fallback to unblocked evasion attackers only; wire into `ai_client/game_loop.py` to override `attack_declarations` for `HeuristicPlayer`
- [X] T048 Removal/burn detection in `_score_cast` — add `_DESTROY_RE` and `_DAMAGE_TO_TARGET_RE` regexes; for "destroy/exile target" instants, score = `min(best_target_cmc × 12, 80)`; for damage spells, score based on kills a creature (`best_kill_cmc × 10 + 20`) or face burn `(dmg / opp_life) × 40`
- [X] T049 Aura scoring in `_score_cast` — detect "enchant creature" + `_AURA_BOOST_RE` for stat grants; score `p_boost × 8 + t_boost × 4` plus 10 per keyword granted; return -20 if no friendly creatures available to enchant
- [X] T050 Planeswalker scoring in `_score_cast` — detect "planeswalker" type line; base 40 + `loyalty × 8` to reflect sustained card advantage

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS Phases 3, 4, 5
- **Phase 3 (US1)**: Depends on Phase 2 — delivers runnable heuristic player (stub)
- **Phase 4 (US2)**: Depends on Phase 2 — can start alongside Phase 3 (different files: scoring logic vs CLI wiring)
- **Phase 5 (US3)**: Depends on Phase 3 and Phase 4 — needs both CLI flags and real decisions working
- **Phase 6 (Polish)**: Depends on all phases

### User Story Dependencies

- **US1 (P1)**: After Phase 2. CLI wiring — independent of US2 scoring logic.
- **US2 (P2)**: After Phase 2. Scoring implementation — independent of US1 CLI wiring.
- **US3 (P3)**: After US1 and US2 — needs both working to test all combinations.

### Within Each Phase

- T005, T006, T007, T008 (Phase 2) are all independent helpers — fully parallel
- T016, T018, T021 (Phase 4) are independent scorer implementations — fully parallel; T017, T020, T022 wiring tasks depend on their respective scorers

### Parallel Opportunities

- T005, T006, T007, T008: All Phase 2 helpers run in parallel
- T010–T015: US1 tasks mostly sequential (each builds on previous)
- T016, T018, T021: Three scorer functions are independent; implement in parallel
- T025, T026, T027: US3 tasks are independent (different concerns)

---

## Parallel Example: Phase 2 (Foundational Helpers)

```bash
# All four helpers can be implemented simultaneously:
Task T005: _extract_my_info() helper
Task T006: _extract_battlefield() helper
Task T007: _cmc() helper
Task T008: _has_keyword() helper
```

## Parallel Example: Phase 4 (Scorer Functions)

```bash
# Three scorers are independent:
Task T016: _score_cast()
Task T018: _simulate_combat() + T019: _score_declare_attackers()
Task T021: _score_declare_blockers()
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Extend `PlayerConfig` and `AIPlayer.decide()` signature
2. Complete Phase 2: `HeuristicPlayer` scaffold with stub `decide()`
3. Complete Phase 3 (US1): CLI flags and factory
4. **STOP and VALIDATE**: Run heuristic-vs-heuristic — game runs (all passes), no crash, no LLM calls
5. Proceed to Phase 4 to add competitive decisions

### Incremental Delivery

1. Phase 1 + 2 + 3 → Heuristic player exists, game runs (passes only) ✓
2. Phase 4 (US2) → Heuristic player plays competitively ✓
3. Phase 5 (US3) → All three combinations fully documented and validated ✓
4. Phase 6 → Polish and confirm backwards compat ✓

---

## Notes

- [P] tasks = different files, no shared dependencies — safe to implement simultaneously
- `_auto_tap_mana` in `GameLoop` already handles land tapping before `decide()` is called — HeuristicPlayer will never see mana activation in `legal_actions`
- HeuristicPlayer's `_debug_callback` is intentionally not called — no LLM prompt/response to stream
- Always return `(0, reason)` as fallback in `decide()` — index 0 is always `pass` in the engine's legal action list

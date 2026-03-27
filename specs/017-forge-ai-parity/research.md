# Research: Forge AI Parity

**Branch**: `017-forge-ai-parity` | **Date**: 2026-03-25

---

## 1. Target Selection — How Valid Targets Flow Today

**Finding**: `_compute_legal_actions` in `game.py:808` already populates `valid_targets` on each `LegalAction`, but the engine auto-selects only a single "best guess" target (e.g., first creature, highest-priority creature for Auras). The engine does not offer all valid targets — it narrows to one. This means the AI client currently has no choice to make.

**Decision**: Two-part fix:
1. **Engine**: Expand `valid_targets` to return ALL valid targets (not just the first one) for removal, burn, and Aura spells, so the AI client sees the full target set.
2. **AI client**: Add `_select_best_target(valid_targets, game_state, spell_type)` to `HeuristicPlayer` that picks from the list using spec heuristics (highest-CMC for removal, player-if-lethal for burn, highest-power-friendly for Aura).

**Rationale**: Minimal engine change (expand the target list); all selection intelligence stays in AI client.

**Alternatives considered**: Let the engine pick best target (rejected — heuristics belong in AI layer); pass all permanents and let AI filter (rejected — engine already filters legality).

---

## 2. Modal Spell Mode Selection — How modes_chosen Works Today

**Finding**: `CastRequest.modes_chosen` (`models/actions.py:35`) is a `list[int]` field, already wired through to the engine stack handler (`game.py:411`). It is always sent as `[]` from the game loop today — the engine uses the first mode when empty.

**Decision**: The AI client populates `modes_chosen` before building the `CastRequest`. A new `_select_modes(card, game_state)` method in `HeuristicPlayer` scores each mode by its oracle text effect (removal, draw, burn, etc.) and returns the top N mode indices for choose-N spells.

**Rationale**: Zero engine changes needed; modes are already modeled.

---

## 3. Planeswalker Loyalty Abilities — Engine Gap

**Finding**: `_compute_legal_actions` does not generate any legal actions for planeswalker loyalty abilities. Planeswalkers are on the battlefield as `Permanent` objects but their loyalty abilities are not in `ability_parser.py`'s `ActivatedAbility` output — loyalty abilities have `[+N]`, `[0]`, `[−N]` cost format that the parser doesn't handle yet.

**Decision**:
1. **Engine**: Add loyalty-ability parsing to `ability_parser.py` — detect `[+N]`, `[-N]`, `[0]` patterns in planeswalker oracle text.
2. **Engine**: In `_compute_legal_actions`, emit `action_type="activate_loyalty"` actions for each loyalty ability the planeswalker can legally use (check: has it already activated this turn? is loyalty sufficient for − abilities?).
3. **Engine**: Add `activate_loyalty` handler in `game.py` that adjusts the planeswalker's loyalty counter and resolves the ability effect.

**Rationale**: Planeswalkers need engine support since loyalty counters and "once per turn" timing are rules-level constraints.

---

## 4. Graveyard Zone Casting (Flashback, Escape, Unearth, Disturb) — Engine Gap

**Finding**: `PlayerState.graveyard` exists in `game.py:107` and keywords (flashback, escape, unearth, disturb) are recognized by `ability_parser.py:50-61`, but `_compute_legal_actions` never iterates `player.graveyard`. No `cast_from_graveyard` action type exists.

**Decision**:
1. **Engine**: Add `cast_from_graveyard` branch in `_compute_legal_actions` that iterates `player.graveyard`, detects flashback/escape/unearth/disturb keywords, validates the alternative cost can be paid (escape requires N cards in graveyard to exile), and emits `action_type="cast"` with `alternative_cost="flashback"` (or `"escape"` etc.).
2. **Engine**: Add graveyard exile handling in the cast resolution path for escape costs.
3. **AI client**: `HeuristicPlayer._score_cast` already handles `action_type="cast"` — graveyard casts will get scored automatically with a +10 bonus via `alternative_cost` detection.

**Rationale**: Uses existing `alternative_cost` field in `CastRequest` — no new API surface needed.

---

## 5. Mulligan — Engine Gap

**Finding**: No mulligan endpoint or phase exists. Games start with 7-card hands drawn automatically. The `TurnManager` has no mulligan phase.

**Decision**:
1. **Engine**: Add a `POST /game/{id}/mulligan` endpoint that, when called, discards the player's current hand and draws N−1 new cards (London mulligan). Add a `mulligan_phase_active` flag to `GameState` that gates this action to before turn 1.
2. **AI client**: Before the game loop starts, if the game is in mulligan phase, call `HeuristicPlayer.evaluate_mulligan(hand, deck_stats)` to decide keep/mulligan. The game loop retries up to 3 times (7→6→5 cards) before forcing a keep.

**Rationale**: Minimal new engine surface; London mulligan is the current MTG standard and easiest to implement (draw N−1, no partial scry needed for MVP).

---

## 6. Cascade Trigger Resolution — Engine Gap

**Finding**: Cascade is listed as a keyword in `ability_parser.py:50` but has no engine resolution logic. When a cascade spell is cast, the engine does not implement the cascade effect.

**Decision**:
1. **Engine**: In `stack.py`, detect cascade keyword on spells resolving from the stack. When cascade triggers, implement: exile cards from top of library until a non-land card with CMC < cascading spell's CMC is found, offer it to the controller as a free cast (generate a `cascade_choice` event on `GameState`).
2. **Engine**: Add `POST /game/{id}/cascade-choice` endpoint with `card_id` and `cast: bool` body — AI can choose to cast or not.
3. **AI client**: `HeuristicPlayer` evaluates the cascade card using normal cast scoring; casts if score > 0.

---

## 7. AIMemory — Architecture

**Decision**: New dataclass `AIMemory` in `ai_client/models.py` with 9 named `dict` / `set` fields corresponding to Forge's `AiCardMemory` categories. One `AIMemory` instance is created per player per game in `game_loop.py` and passed as a parameter to all `HeuristicPlayer` decision methods.

**Rationale**: Per-game, per-player scope; no persistence needed. Passing as parameter (not stored on HeuristicPlayer) keeps the player class stateless and testable.

---

## 8. AiPersonalityProfile — Architecture

**Decision**: New dataclass `AiPersonalityProfile` in `ai_client/models.py` with all boolean flags and float probabilities from spec FR-049–FR-054. Profiles are loaded from a YAML or dict config; two built-in profiles ("default", "aggro") are defined as class constants. The profile is attached to `PlayerConfig`.

**Rationale**: Dict-based config allows runtime override without code changes; two built-in profiles satisfy SC-012.

---

## 9. LookaheadSimulator — Architecture

**Decision**: New module `ai_client/lookahead.py` containing `LookaheadSimulator` class. It takes a `game_state` dict (the serialized API response), makes a deep copy, and simulates the AI's next turn by calling `HeuristicPlayer._score_action` on each hypothetical action after the current action is applied. Depth capped at 1 future turn. Returns a `float` bonus (max +30) added to the current action's score.

**Rationale**: Isolating lookahead in its own module keeps `heuristic_player.py` manageable and makes lookahead independently testable. A dict-copy approach (not full engine replay) is fast enough for 500ms budget.

**Performance check**: A typical board has ≤15 legal actions per turn. Lookahead evaluates each of those actions' resulting states (~15 × 15 = 225 score calls). Each `_score_action` is O(N permanents) ≈ O(20). Total: ~4,500 operations per lookahead — well within 500ms.

---

## 10. Phyrexian Mana / Alternative Cost Evaluation

**Finding**: `CastRequest.alternative_cost` field exists. `ability_parser.py` does not yet parse Phyrexian mana symbols (`{W/P}`, `{U/P}` etc.) from mana cost strings.

**Decision**:
1. **Engine**: Extend `ability_parser.py` and `engine/mana.py` to recognize Phyrexian mana symbols and generate two legal action options when a card has them: one with colored mana payment (normal), one with `alternative_cost="phyrexian"` that subtracts 2 life instead.
2. **AI client**: `HeuristicPlayer` detects `alternative_cost="phyrexian"` and applies FR-059/FR-060 life-threshold logic.

---

## 11. Convoke / Delve / Emerge

**Finding**: `ability_parser.py` recognizes Convoke/Delve/Emerge as keywords but `_compute_legal_actions` does not generate alternative-cost cast actions for them.

**Decision**:
1. **Engine**: For Convoke, detect untapped creature count; emit a `cast` action with `alternative_cost="convoke"` and `valid_targets` listing creature IDs usable for tapping.
2. **Engine**: For Delve, emit `cast` with `alternative_cost="delve"` when graveyard has cards; include count of exilable cards.
3. **Engine**: For Emerge, emit `cast` with `alternative_cost="emerge"` and `valid_targets` listing sacrifice-eligible creatures.
4. **AI client**: Score these alternatives using FR-055–FR-058 trade-off logic.

---

## 12. Safe Block Classification

**Finding**: `compute_block_declarations` in `heuristic_player.py` already computes favorable vs. chump blocks but does not label them SAFE/TRADE/CHUMP.

**Decision**: Add `BlockClassification` enum (`SAFE`, `TRADE`, `CHUMP`) to `ai_client/models.py`. Refactor `compute_block_declarations` to classify each proposed block before final assignment, then prefer SAFE > TRADE > CHUMP.

---

## 13. Stack-Aware Responses and Spell Copying

**Finding**: The game loop in `game_loop.py` currently processes the AI's turn only when the AI holds priority. Responding to the opponent's stack items requires the engine to grant priority mid-stack to the non-active player, which already happens per MTG rules but the game loop immediately passes.

**Decision**:
1. **AI client**: In `game_loop.py`, when `priority_player` is the AI during the opponent's turn (mid-stack), evaluate instant-speed responses: pump to save creature from removal (FR-102), copy spell on stack (FR-103). Do not auto-pass.
2. **Engine**: `CopySpellRequest` already exists (`models/actions.py:110`). Wire it as a legal action when the stack has a copiable spell and the AI controls a copy effect.

---

## Summary of Engine Endpoints Added

| Endpoint | Purpose |
|----------|---------|
| `POST /game/{id}/mulligan` | London mulligan — discard hand, draw N−1 |
| `POST /game/{id}/activate-loyalty` | Activate a planeswalker loyalty ability |
| `POST /game/{id}/cast` (extended) | Graveyard casting via `alternative_cost`; Convoke/Delve/Emerge |
| `POST /game/{id}/cascade-choice` | Resolve cascade trigger — cast or skip |

## Summary of New AI Client Modules / Classes

| Module | New Additions |
|--------|--------------|
| `ai_client/models.py` | `AIMemory`, `AiPersonalityProfile`, `BlockClassification` |
| `ai_client/lookahead.py` | `LookaheadSimulator` |
| `ai_client/heuristic_player.py` | ~36 new scoring methods + profile integration |
| `ai_client/game_loop.py` | Mulligan phase, AIMemory instantiation, stack-aware pass logic |

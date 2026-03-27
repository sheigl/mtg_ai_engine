# Feature Specification: Full Rules Engine Parity

**Feature Branch**: `018-rules-engine-full-parity`
**Created**: 2026-03-26
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Spell Effects Actually Resolve (Priority: P1)

A user casting any common spell (Lightning Bolt, Giant Growth, Counterspell, Divination, Murder, etc.) expects that spell to change the game state when it resolves. Currently, only damage, pump, and counter effects are implemented — all others silently no-op.

**Why this priority**: This is the single most impactful gap. Roughly 80% of all MTG cards produce effects the engine ignores. Without this, the game is unplayable for any realistic card pool.

**Independent Test**: Play a game where Player 1 casts Divination (draw 2 cards) — player's hand size should increase by 2. Cast Murder on a creature — creature should leave the battlefield. Cast Raise the Alarm (create tokens) — tokens should appear on the battlefield.

**Acceptance Scenarios**:

1. **Given** Player A casts Divination (draw 2 cards), **When** the spell resolves, **Then** Player A's hand increases by exactly 2 cards drawn from their library.
2. **Given** Player A casts Murder targeting an opponent's creature, **When** the spell resolves, **Then** that creature is moved to the graveyard and dies triggers fire.
3. **Given** Player A casts Boomerang targeting a permanent, **When** the spell resolves, **Then** that permanent is returned to its owner's hand and removed from the battlefield.
4. **Given** Player A casts an exile spell targeting a creature, **When** the spell resolves, **Then** that creature is moved to exile zone (not graveyard) and dies triggers do NOT fire.
5. **Given** Player A casts Raise the Alarm (create two 1/1 Soldier tokens), **When** the spell resolves, **Then** two 1/1 token permanents appear on Player A's side of the battlefield, ETB triggers fire for each.
6. **Given** Player A casts Swords to Plowshares (exile creature, controller gains life), **When** the spell resolves, **Then** creature goes to exile AND the creature's controller gains life equal to the creature's power.
7. **Given** Player A casts Diabolic Tutor (search library, put card in hand), **When** the spell resolves, **Then** a `pending_tutor_choice` is set on game state blocking priority, and on resolution the card moves to Player A's hand.
8. **Given** Player A casts Mind Rot (opponent discards 2 cards), **When** the spell resolves, **Then** opponent discards 2 cards from hand.
9. **Given** Player A casts Solidarity of Heroes (put +1/+1 counters on a creature), **When** the spell resolves, **Then** the targeted permanent's counters field is updated and its effective P/T increases.

---

### User Story 2 - Targeting Rules Enforced (Priority: P2)

A user with a Hexproof creature should not be able to have that creature targeted by opponent's spells. A player with a Shroud creature cannot target it even with their own spells. Menace attackers cannot be legally blocked by a single creature.

**Why this priority**: Targeting rule violations create fundamentally illegal game states and would be immediately noticed during any real game.

**Independent Test**: Start a game with a Hexproof creature on the battlefield. Verify that no opponent spell actions list that creature as a valid target. Add a Shroud creature — verify neither player can target it. Send a Menace attacker — verify the declare_blockers validation rejects a single-blocker assignment.

**Acceptance Scenarios**:

1. **Given** Player A has a creature with Hexproof, **When** Player B's `_compute_legal_actions` computes cast actions, **Then** the hexproof creature does not appear in `valid_targets` for any of Player B's spells.
2. **Given** a creature has Shroud, **When** either player's `_compute_legal_actions` runs, **Then** that creature appears in no spell's `valid_targets`.
3. **Given** Player A attacks with a Menace creature and Player B declares only one blocker, **When** the declare_blockers action is validated, **Then** the action is rejected with an error indicating menace requires 2+ blockers.
4. **Given** a Ward permanent is targeted by an opponent's spell, **When** the spell would resolve without the ward cost being paid, **Then** the spell is countered.

---

### User Story 3 - X Spells Cast for Variable Amounts (Priority: P3)

A user with 5 mana and Fireball in hand should see legal actions for Fireball with X=1, X=2, X=3, X=4 (reserving 1 for the colored pip). The actual damage dealt should equal the X value chosen.

**Why this priority**: X spells are a major MTG card category. Without this, X=0 always, making all X spells useless.

**Independent Test**: Load a game with Fireball in hand and 5 available mana. Verify that `_compute_legal_actions` returns multiple cast actions for Fireball with different X values. Cast Fireball with X=3 targeting a creature with 3 toughness — creature should die.

**Acceptance Scenarios**:

1. **Given** Player A has Fireball (cost {X}{R}) in hand and 5 available mana, **When** legal actions are computed, **Then** cast actions are returned for X=1, X=2, X=3, X=4.
2. **Given** Player A casts Fireball with X=4 targeting a creature with 4 toughness, **When** the spell resolves, **Then** the creature takes 4 damage and dies.
3. **Given** Player A has a 0-colored-pip X spell and 6 mana, **When** legal actions are computed, **Then** X=1 through X=6 variants are all offered.

---

### User Story 4 - Modal Spells Apply Only Chosen Mode (Priority: P4)

A user casting a charm spell choosing one mode should see exactly that effect applied — not all mode effects simultaneously.

**Why this priority**: Modal spells are extremely common (Commands, charms, etc.) and the current behavior of applying full oracle text produces incorrect multi-effect resolution.

**Independent Test**: Cast a charm spell choosing one mode. Verify only that mode's effect resolves, not all modes.

**Acceptance Scenarios**:

1. **Given** Player A casts a modal spell and selects mode "deal 3 damage to target creature", **When** the spell resolves, **Then** only the damage effect applies — other modes do NOT apply.
2. **Given** Player A casts a 2-mode spell selecting both modes, **When** the spell resolves, **Then** both chosen effects apply in oracle text order.

---

### User Story 5 - Cascade Trigger Works (Priority: P5)

A user casting a cascade spell (e.g., Shardless Agent) should trigger the cascade procedure: exile cards until finding a legal free cast, then choose to cast or exile it.

**Why this priority**: Cascade is a complete mechanic requiring library manipulation, legal action emission, and resolution branches. It cannot be approximated.

**Independent Test**: Cast a cascade spell and observe that `cascade_choice` legal action appears with a revealed card; choose to cast the free card or exile it.

**Acceptance Scenarios**:

1. **Given** Player A casts a cascade spell, **When** it resolves, **Then** cards are exiled from the top of Player A's library until a non-land card with CMC less than the cascade spell is found.
2. **Given** the cascade card is found, **When** `cascade_choice` legal action is presented, **Then** Player A may cast it for free (without paying mana cost) or exile it.
3. **Given** cascade resolves, **Then** all non-chosen exiled cards are placed on the bottom of the library.

---

### User Story 6 - Scry/Surveil Create Blocking Choice (Priority: P6)

When a card resolves with "scry 2", the player should be prompted to look at the top 2 cards of their library and arrange/replace them. The game should not advance until this choice is made.

**Why this priority**: The AI already has scoring for scry/surveil choices; the engine just needs to emit the blocking choice.

**Independent Test**: Cast a card with "scry 2". Verify that `pending_scry_choice` appears in game state with the revealed cards, and that `choice` legal actions are emitted.

**Acceptance Scenarios**:

1. **Given** a spell with "scry 2" resolves, **When** the effect is applied, **Then** `pending_scry_choice` is set on game state with the top 2 cards revealed.
2. **Given** `pending_scry_choice` is active, **When** the player submits their arrangement, **Then** library top is updated and `pending_scry_choice` is cleared.
3. **Given** a spell with "surveil 2" resolves, **When** the effect is applied, **Then** player may put any of the top N cards into graveyard or back on top.

---

### User Story 7 - Keyword Mechanics Implemented (Priority: P7)

Kicker, Jump-start, Suspend, Foretell, and Unearth are common keyword mechanics that should each offer appropriate legal actions in the correct game phase.

**Why this priority**: Each mechanic is self-contained and used by numerous cards. Implementing them unlocks broad swaths of the card pool.

**Independent Test**: For each keyword: put a card with that keyword in hand, verify the alternate-cost legal action appears; take the action; verify the effect.

**Acceptance Scenarios**:

1. **Given** Player A has a Kicker card in hand with mana to pay kicker, **When** legal actions are computed, **Then** two cast actions are offered: one with and one without kicker.
2. **Given** Player A has a Jump-start card in graveyard and a card in hand, **When** in main phase, **Then** a jump-start cast action appears and consumes a discard.
3. **Given** Player A suspends a card (exile with time counters), **When** their upkeep begins, **Then** one time counter is removed; when the last is removed, the card is cast for free.
4. **Given** Player A foretells a card (exile face-down for {2}), **When** on a later turn, **Then** a foretell cast action appears at the discounted cost.
5. **Given** a creature with Unearth is cast from the graveyard, **When** end of turn arrives, **Then** it moves to exile (not graveyard) and cannot be unearthed again.

---

### User Story 8 - Protection from Color Targeting Enforced (Priority: P8)

A creature with "protection from red" cannot be targeted by red spells, cannot be blocked by red creatures, and red damage is prevented.

**Why this priority**: Protection is a common keyword and the targeting enforcement is simply missing.

**Independent Test**: Cast a "protection from red" creature. Verify no red spells list it as a valid target.

**Acceptance Scenarios**:

1. **Given** a creature has "protection from red", **When** Player B tries to cast a red spell targeting it, **Then** that creature does not appear in the spell's `valid_targets`.
2. **Given** a creature has protection from a color, **When** a spell of that color resolves with that creature as target, **Then** the spell is countered for that target (protection prevents the effect).

---

### User Story 9 - AI Responds During Opponent's Priority Window (Priority: P9)

When the opponent casts a creature spell and passes priority, the AI holding a Counterspell should evaluate whether to counter it rather than auto-passing.

**Why this priority**: This is a fundamental AI correctness gap — the AI currently cannot interact on the opponent's turn at all.

**Independent Test**: Opponent casts a high-value creature. AI has a Counterspell. Verify that AI evaluates the counterspell action rather than auto-passing.

**Acceptance Scenarios**:

1. **Given** AI has priority during opponent's turn with a non-empty stack, **When** deciding an action, **Then** AI scores all instant-speed actions against the stack context and may choose to respond.
2. **Given** AI has a pump spell and the opponent is attacking, **When** a friendly creature is declared as a blocker facing lethal damage, **Then** AI evaluates the pump spell as a saving action.
3. **Given** AI has priority during opponent's end step with flash/instant spells available, **Then** AI evaluates casting them before the opponent untaps.

---

### User Story 10 - Menace-Aware AI Blocking (Priority: P10)

The AI should not illegally assign a single blocker to a Menace attacker — it must either assign 2 blockers or let it through.

**Why this priority**: Assigning one blocker to a Menace creature produces an illegal game state that would be rejected by the engine.

**Independent Test**: Opponent attacks with a Menace creature. AI has 2 available blockers. Verify AI assigns both or assigns none.

**Acceptance Scenarios**:

1. **Given** opponent attacks with a Menace creature and AI has 2 creatures that can block, **When** AI computes block declarations, **Then** either both are assigned as co-blockers or neither is (AI never assigns exactly 1).
2. **Given** 2 blockers together kill the Menace creature, **When** computing blocks, **Then** AI prefers the gang-block over letting it through.

---

### Edge Cases

- What happens when draw resolves with an empty library? Player loses due to draw from empty library (state-based action).
- What happens when destroy is used on an Indestructible permanent? Effect fizzles — permanent remains.
- What happens when exile targets a permanent that left the battlefield before resolution? Spell fizzles (no legal target remaining).
- What happens when cascade reveals 0 valid cards (all non-land cards have CMC >= cascade spell)? Exile all revealed cards, nothing is cast for free.
- What happens when a Kicker card is cast with kicker via Jump-start? Jump-start allows the card to be cast; kicker is an additional cost that may also be paid.
- What happens if X=0 in an X spell? Cast action is not offered for X=0 (X>=1 required for meaningful effect).
- What happens if scry choice times out (heuristic AI)? AI auto-calls `_score_scry_choice()` immediately and submits the result.
- What if a DFC's transform condition is checked on a non-DFC permanent? Condition check is guarded by `layout == "transform"` check; skipped silently.

---

## Requirements *(mandatory)*

### Functional Requirements

**Spell Effect Resolution**

- **FR-001**: `_apply_spell_effect()` MUST resolve "draw N cards" by moving N cards from the top of the active player's library to their hand, triggering draw triggers.
- **FR-002**: `_apply_spell_effect()` MUST resolve "destroy target [permanent type]" by moving the permanent to the owner's graveyard and firing dies/leaves-battlefield triggers.
- **FR-003**: `_apply_spell_effect()` MUST resolve "exile target [permanent/card]" by moving the permanent/card to the exile zone; ETB/dies triggers MUST NOT fire for exiled permanents.
- **FR-004**: `_apply_spell_effect()` MUST resolve "return target permanent to its owner's hand" (bounce) by removing the permanent from the battlefield and adding the corresponding card to the owner's hand.
- **FR-005**: `_apply_spell_effect()` MUST resolve "create N [type] tokens" by adding N new Permanent objects with `is_token=True` to the battlefield, firing ETB triggers for each.
- **FR-006**: `_apply_spell_effect()` MUST resolve "gain N life" by adding N to the target player's `life` field.
- **FR-007**: `_apply_spell_effect()` MUST resolve "search your library for a card" by setting `pending_tutor_choice` on GameState; a `choice` legal action must be emitted until resolved, then the selected card moves to the searching player's hand.
- **FR-008**: `_apply_spell_effect()` MUST resolve "discard N cards" by prompting the affected player to discard (AI uses lowest-value selection; human player gets `pending_discard_choice`).
- **FR-009**: `_apply_spell_effect()` MUST resolve "put N +1/+1 counters on target creature" by updating `permanent.counters["+1/+1"]` by +N.
- **FR-010**: All existing spell effect resolution (damage, pump, counter) MUST continue to function unchanged.
- **FR-011**: The effect pattern matcher MUST use a priority-ordered list of regex patterns; unrecognized patterns MUST log a warning and no-op (not crash).

**Targeting Rule Enforcement**

- **FR-012**: `_compute_legal_actions` MUST exclude from `valid_targets` any permanent with the Hexproof keyword when the targeting player is not the permanent's controller.
- **FR-013**: `_compute_legal_actions` MUST exclude from `valid_targets` any permanent with the Shroud keyword regardless of the targeting player.
- **FR-014**: `declare_blockers` validation in `combat.py` MUST reject assignments where exactly 1 blocker is assigned to a Menace creature; 0 or 2+ blockers are valid.
- **FR-015**: When a permanent with Ward is targeted by an opponent's spell/ability, the engine MUST create a `pending_ward_payment` state and offer the option to pay the ward cost; failure to pay counters the targeting spell.

**X Spells**

- **FR-016**: `_compute_legal_actions` MUST detect `{X}` in a card's `mana_cost` field.
- **FR-017**: For each X spell in hand, `_compute_legal_actions` MUST emit a separate cast legal action for each value of X from 1 to (available_mana - colored_pips), capped at X=10.
- **FR-018**: The `CastRequest` model MUST include an optional `x_value: int` field (default 0).
- **FR-019**: `_apply_spell_effect()` MUST use `x_value` from the resolved stack entry when computing damage, life gain, card draw, or other X-scaled effects.
- **FR-020**: The heuristic AI MUST score X spells at `X * per_unit_value` (e.g., Fireball at X=4 scores as 4 damage worth of value).

**Modal Spell Modes**

- **FR-021**: `_apply_spell_effect()` MUST check for a `modes_chosen` field on the stack entry before processing oracle text.
- **FR-022**: When `modes_chosen` is set, `_apply_spell_effect()` MUST split oracle text by mode delimiters (`•`, "Mode N:", semicolons) and apply ONLY the selected mode clauses.
- **FR-023**: The AI's `_select_modes()` method MUST be called before submitting a cast action for modal spells, and the selected modes MUST be included in the cast request.

**Cascade Trigger**

- **FR-024**: `resolve_top()` in `stack.py` MUST detect the "cascade" keyword on the resolving spell's oracle text.
- **FR-025**: When cascade is triggered, the engine MUST exile cards from the top of the caster's library one at a time until finding a non-land card with CMC strictly less than the cascade spell's CMC.
- **FR-026**: The engine MUST set `gs.pending_cascade` with the found card and all exiled cards, and emit a `cascade_choice` legal action to the cascading player.
- **FR-027**: On cascade resolution when the player chooses to cast: the card is cast for free and placed on the stack; all other exiled cards go to the bottom of the library.
- **FR-028**: If the player chooses not to cast (or no valid card exists): the found card (if any) is also exiled; all other cards go to the bottom of the library.

**Keyword Mechanics**

- **FR-029**: Kicker: `_compute_legal_actions` MUST detect kicker cost in oracle text; emit two cast actions — base and with-kicker. `_apply_spell_effect()` MUST apply additional kicker effect when `kicker_paid=True` in the stack entry.
- **FR-030**: Jump-start: graveyard cast set MUST include jump-start cards when the player has at least one other card in hand to discard; the cast request must include `jump_start_discard_id`.
- **FR-031**: Suspend: `_compute_legal_actions` MUST offer a `suspend` action for suspend cards in hand during main phase; suspended cards are exiled with N time counters; upkeep trigger removes one counter; at zero counters, the card is cast for free.
- **FR-032**: Foretell: `_compute_legal_actions` MUST offer a `foretell` action in main phase (cost {2}); foretold cards are exiled face-down; on subsequent turns the foretell cast action appears at the discounted cost.
- **FR-033**: Unearth: `_compute_legal_actions` MUST offer `unearth` cast from graveyard; unearthed permanent MUST have `unearthed=True` flag; end-of-turn SBA MUST exile all unearthed permanents.

**Scry/Surveil Engine Integration**

- **FR-034**: When any spell effect resolves with "scry N", the engine MUST set `pending_scry_choice` on GameState with N revealed cards from library top and the player who must choose.
- **FR-035**: `pending_scry_choice` MUST block all other priority actions until resolved; `choice` legal actions for valid arrangements must be emitted.
- **FR-036**: Surveil N MUST follow the same pattern as scry N, but the player may put any of the N cards into the graveyard (not only bottom of library).

**Protection from Color**

- **FR-037**: A helper `get_spell_colors(card)` MUST extract color symbols (`W`, `U`, `B`, `R`, `G`) from the card's `mana_cost`.
- **FR-038**: A helper `get_protection_colors(permanent)` MUST parse "protection from [color]" from `oracle_text`.
- **FR-039**: `_compute_legal_actions` MUST exclude from `valid_targets` any permanent where at least one spell color matches at least one protection color.

**Double-Faced Cards / Transform**

- **FR-040**: When a permanent with `layout == "transform"` has a transform trigger condition in oracle text, the engine MUST evaluate that condition at the appropriate game step and flip the Permanent between front and back face data.
- **FR-041**: Werewolves (identified by "transform" in upkeep trigger text) MUST transform at beginning of upkeep if no spells were cast last turn, and transform back if 2+ spells were cast.
- **FR-042**: Modal DFCs (`layout: "modal_dfc"`) MUST NOT transform; casting the back face directly MUST be supported as a separate cast action from hand.

**AI Gaps — Non-Active Priority**

- **FR-043**: The game loop MUST NOT auto-pass when the AI has priority during the opponent's turn if there are instant-speed spells or abilities available.
- **FR-044**: The heuristic AI MUST score instant-speed spells against the current stack context (e.g., counterspell value increases when opponent's spell is on top of stack).
- **FR-045**: The heuristic AI MUST score pump spells targeting a friendly creature facing lethal combat damage at `saved_creature_cmc * 12`.

**AI Gaps — Menace Blocking**

- **FR-046**: `compute_block_declarations()` in `heuristic_player.py` MUST detect Menace on attacking creatures.
- **FR-047**: For Menace attackers, the AI MUST assign either 0 or 2+ blockers; a single-blocker assignment is never generated.
- **FR-048**: If 2 blockers together can kill the Menace attacker and the damage prevented exceeds the blockers' combined value, the AI MUST prefer the gang-block.

**AI Gaps — Revealed Card Memory**

- **FR-049**: When the engine returns a game state where opponent's hand cards are visible (e.g., after Thoughtseize), `AIMemory.revealed_cards` MUST be populated with those cards.
- **FR-050**: The AI MUST use `revealed_cards` when scoring opponent threats to avoid double-counting hidden cards.

### Key Entities *(include if feature involves data)*

- **StackEntry**: Extended with `x_value: int = 0`, `kicker_paid: bool = False`, `modes_chosen: list[int] = []`, `jump_start_discard_id: str | None = None`.
- **GameState**: Extended with `pending_scry_choice`, `pending_surveil_choice`, `pending_tutor_choice`, `pending_discard_choice`, `pending_cascade`, `pending_ward_payment` — all optional blocking-choice states.
- **Permanent**: Extended with `unearthed: bool = False`, `time_counters: int = 0` (for suspend), `foretold: bool = False`.
- **CastRequest**: Extended with `x_value: int = 0`, `kicker_paid: bool = False`, `modes_chosen: list[int] = []`, `jump_start_discard_id: str | None = None`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 9 new spell effect types (draw, destroy, exile, bounce, token, life gain, tutor, discard, +1/+1 counters) produce correct game-state changes when their corresponding cards are cast and resolved. Each is verified by a dedicated unit test.
- **SC-002**: A creature with Hexproof does not appear in valid_targets for any opponent spell; a creature with Shroud does not appear for any spell. Verified by unit test with mock game state.
- **SC-003**: The engine rejects a single-blocker assignment to a Menace creature via a 400 error; 0-blocker and 2-blocker assignments are accepted without error.
- **SC-004**: Fireball with 5 available mana generates 4 distinct legal cast actions (X=1 through X=4) in `_compute_legal_actions`; resolving at X=3 deals exactly 3 damage.
- **SC-005**: A modal spell cast with one mode selected applies only that mode's effect; the other modes' effects are absent from the resulting game state.
- **SC-006**: Casting a cascade spell results in a `cascade_choice` legal action appearing before priority passes to the opponent.
- **SC-007**: Scry 2 produces `pending_scry_choice` on game state with exactly 2 revealed cards; after choice submission the library top matches the chosen arrangement.
- **SC-008**: All 376 existing tests continue to pass after all changes (no regressions).
- **SC-009**: A heuristic AI vs heuristic AI game with a card pool including Fireball, Murder, Divination, Counterspell, and Menace creatures completes without errors or illegal game states within 200 turns.
- **SC-010**: The AI correctly evaluates counterspell responses at least 50% of the time when it has a Counterspell and an opponent's spell is on the top of the stack.

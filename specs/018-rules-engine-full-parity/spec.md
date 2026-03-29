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

---

### User Story 11 - Indestructible Replacement Effect (Priority: P1-CRITICAL)

A creature with Indestructible should not be destroyed by destroy effects, lethal damage, or SBAs — it survives everything except exile and -toughness.

**Why this priority**: Indestructible is on thousands of cards. Currently the keyword is parsed but not enforced — a destroy spell kills an indestructible creature, which is fundamentally wrong.

**Independent Test**: Put a creature with Indestructible on the battlefield. Target it with Murder. Verify it stays on the battlefield.

**Acceptance Scenarios**:

1. **Given** a creature has the Indestructible keyword, **When** a destroy effect targets it, **Then** the creature remains on the battlefield and dies triggers do NOT fire.
2. **Given** an Indestructible creature takes lethal damage, **When** SBAs are checked, **Then** the creature is NOT moved to the graveyard (damage is still marked but not lethal).
3. **Given** an Indestructible creature has toughness reduced to 0, **When** SBAs are checked, **Then** the creature IS moved to the graveyard (toughness-0 SBA still applies).
4. **Given** an Indestructible permanent is the target of an exile effect, **When** the spell resolves, **Then** the permanent IS exiled (indestructible does not prevent exile).

---

### User Story 12 - Unearth End-of-Turn Exile SBA (Priority: P1-CRITICAL)

A creature brought back via Unearth must be exiled at end of turn rather than returning to the graveyard.

**Why this priority**: The `unearthed` flag is already set on permanents but no SBA cleans them up at end of turn. This leaves unearthed creatures permanently on the battlefield.

**Independent Test**: Cast a creature from graveyard via Unearth. Advance to end step. Verify the creature is in exile, not the battlefield or graveyard.

**Acceptance Scenarios**:

1. **Given** a permanent with `unearthed=True` is on the battlefield, **When** the end step SBA fires, **Then** the permanent is moved to exile.
2. **Given** an unearthed creature would die from lethal damage, **When** SBAs are checked, **Then** it goes to exile instead of the graveyard (replacement effect).
3. **Given** an unearthed creature is exiled, **Then** it cannot be unearthed again (graveyard is bypassed entirely).

---

### User Story 13 - Double Strike Two-Damage-Step Enforcement (Priority: P1-HIGH)

A creature with Double Strike must deal damage in both the first-strike step and the regular combat damage step. Currently the keyword is parsed but not enforced — double strike creatures only deal damage once.

**Why this priority**: Double strike on creatures like Mirran Crusader or Sublime Archangel is a core combat keyword present on many popular cards.

**Independent Test**: Declare a Double Strike creature as an attacker. Verify that after the first-strike damage step the creature has already dealt its power in damage, and then deals damage again in the regular step.

**Acceptance Scenarios**:

1. **Given** an attacking creature has Double Strike, **When** the First Strike Damage step resolves, **Then** it deals its power in damage and that damage is marked on the blocker/player.
2. **Given** an attacking Double Strike creature killed the blocker in the first strike step, **When** the regular Combat Damage step resolves, **Then** the Double Strike creature deals its power in damage directly to the defending player (trample rules apply if it has trample).
3. **Given** a blocking creature with First Strike and an attacking Double Strike creature, **When** damage resolves, **Then** both deal damage in the first-strike step; the attacking creature also deals damage in the regular step.

---

### User Story 14 - Lifelink Combat Damage Application (Priority: P1-HIGH)

A creature with Lifelink must cause its controller to gain life equal to its power when it deals damage in combat (and from spell effects). Currently lifelink is detected in some replacement effects but not applied during combat damage assignment.

**Why this priority**: Lifelink is on hundreds of popular creatures (Serra Angel, Baneslayer Angel, Loxodon Smiter). Not applying it makes the life total inaccurate.

**Independent Test**: Attack with a Lifelink creature. After combat damage resolves, verify the attacking player's life total increased by the creature's power.

**Acceptance Scenarios**:

1. **Given** an attacking Lifelink creature deals N damage to the defending player, **When** combat damage resolves, **Then** the attacking player gains N life.
2. **Given** an attacking Lifelink creature deals damage to a blocker, **When** combat damage resolves, **Then** the attacking player gains life equal to the damage dealt.
3. **Given** a Lifelink creature with a pump spell is +2/+2 until end of turn, **When** it deals combat damage, **Then** lifelink triggers for the pumped power value.
4. **Given** a spell grants a creature Lifelink via "gains lifelink until end of turn", **When** that creature deals damage, **Then** its controller gains life.

---

### User Story 15 - Fear and Intimidate Blocking Restrictions (Priority: P2-HIGH)

Creatures with Fear can only be blocked by artifact creatures and black creatures. Creatures with Intimidate can only be blocked by artifact creatures and creatures that share a color with the intimidate creature. Neither keyword is currently in the supported keyword list.

**Why this priority**: Fear and Intimidate appear on many creatures in older and remastered sets.

**Independent Test**: Declare a Fear creature as an attacker. Verify that green, red, white, and blue creatures cannot be declared as blockers.

**Acceptance Scenarios**:

1. **Given** an attacking creature has Fear, **When** legal blockers are computed, **Then** only artifact creatures and black creatures are in the valid blocker set.
2. **Given** an attacking creature has Intimidate and is red, **When** legal blockers are computed, **Then** only artifact creatures and red-or-colorless creatures are valid blockers.
3. **Given** Fear/Intimidate is granted via enchantment ("gains fear"), **When** blockers are computed, **Then** the restriction applies.

---

### User Story 16 - Persist and Undying Death Replacements (Priority: P2-HIGH)

A creature with Persist that dies without a -1/-1 counter should return to the battlefield with a -1/-1 counter. A creature with Undying that dies without a +1/+1 counter should return with a +1/+1 counter. Neither keyword is enforced — creatures with these keywords simply go to the graveyard.

**Why this priority**: Both keywords are common in graveyard/sacrifice archetypes and fundamentally change how creatures interact with removal.

**Independent Test**: A creature with Persist dies with no -1/-1 counter. Verify it returns to the battlefield with one -1/-1 counter.

**Acceptance Scenarios**:

1. **Given** a Persist creature dies with no -1/-1 counters, **When** the death zone-change event fires, **Then** the creature re-enters the battlefield with one -1/-1 counter instead of going to the graveyard.
2. **Given** a Persist creature dies with at least one -1/-1 counter, **When** the death zone-change event fires, **Then** the creature goes to the graveyard normally.
3. **Given** an Undying creature dies with no +1/+1 counters, **When** the death zone-change event fires, **Then** the creature re-enters the battlefield with one +1/+1 counter.
4. **Given** an Undying creature dies with at least one +1/+1 counter, **When** the death zone-change event fires, **Then** the creature goes to the graveyard normally.

---

### User Story 17 - Storm Mechanic (Priority: P1-CRITICAL)

A spell with Storm should copy itself for each spell cast before it in the same turn. Currently Storm is not detected or implemented at all.

**Why this priority**: Storm is a complete mechanic required for entire card archetypes (Mind's Desire, Grapeshot, Empty the Warrens, etc.). Its absence causes those cards to have zero effect.

**Independent Test**: Cast 3 spells then cast Grapeshot. Verify 3 Grapeshot copies appear on the stack, each dealing 1 damage.

**Acceptance Scenarios**:

1. **Given** a Storm spell is cast after N spells this turn, **When** the storm trigger fires, **Then** N-1 copies of the spell are created on the stack (the original + N-1 copies = N total).
2. **Given** Storm copies are on the stack, **When** they resolve, **Then** each copy applies the spell's effect independently.
3. **Given** Storm copies are on the stack, **Then** they cannot be countered by "counter target spell" (they are copies, not cast spells) — though specific counterspells may target them.
4. **Given** `GameState.spells_cast_this_turn` is tracked, **When** a Storm spell is cast, **Then** the copy count is exactly `len(spells_cast_this_turn) - 1` (excluding the storm spell itself).

---

### User Story 18 - Cycling (Priority: P2-MEDIUM)

A card with Cycling can be discarded for its cycling cost to draw a card. Currently Cycling is not detected as a keyword and no legal action is emitted for it.

**Why this priority**: Cycling appears on hundreds of cards across every set and is a fundamental card selection mechanic.

**Independent Test**: Put a card with "Cycling {2}" in hand. Verify a cycling legal action is emitted during the player's turn. Take the action, verify the card is in the graveyard and a card was drawn.

**Acceptance Scenarios**:

1. **Given** Player A has a Cycling card in hand, **When** legal actions are computed, **Then** a `cycle` legal action is emitted with the cycling cost.
2. **Given** Player A takes the cycle action, **When** it resolves, **Then** the card is discarded to the graveyard and Player A draws one card from their library.
3. **Given** a Cycling card has an additional cycling trigger ("when you cycle this card, ..."), **When** the card is cycled, **Then** the trigger fires.
4. **Given** Cycling can be performed at instant speed, **When** Player A is not the active player, **Then** the cycle action is still available.

---

### User Story 19 - Overload (Priority: P2-MEDIUM)

A spell with Overload can be cast for its overload cost, replacing "target" with "each" in the effect. Currently Overload is not detected and no overload cast action is emitted.

**Why this priority**: Overload spells (Mizzium Mortars, Cyclonic Rift) are played in many competitive and casual decks.

**Independent Test**: Put Mizzium Mortars in hand with enough mana for overload. Verify both a normal cast action and an overload cast action appear. Take the overload action. Verify all appropriate targets are affected.

**Acceptance Scenarios**:

1. **Given** Player A has an Overload card in hand with enough mana for the overload cost, **When** legal actions are computed, **Then** two cast actions are emitted: the normal cast and an overload cast.
2. **Given** Player A casts a spell with overload, **When** it resolves, **Then** the effect applies to all valid targets on the battlefield (e.g., "destroy target creature" → "destroy each creature").
3. **Given** overload is paid, **Then** the spell has no targets (it cannot be countered for lack of legal targets).

---

### User Story 20 - Multikicker (Priority: P2-MEDIUM)

A spell with Multikicker can have its kicker cost paid multiple times, scaling the effect with each payment. Currently only single Kicker is supported.

**Why this priority**: Multikicker cards (Everflowing Chalice, Rite of Replication) are common and their value scales entirely with the multikicker count.

**Independent Test**: Cast a Multikicker card paying the kicker cost 3 times. Verify `kicker_count=3` is stored on the stack object and the effect scales correctly.

**Acceptance Scenarios**:

1. **Given** Player A has a Multikicker card in hand with 5 mana available, **When** legal actions are computed, **Then** cast actions for kicker_count 0, 1, 2, 3 (etc.) are emitted based on available mana.
2. **Given** Player A casts the spell with kicker_count=3, **When** it resolves, **Then** the effect is applied 3 extra times (or scaled by 3, depending on the card).
3. **Given** a Multikicker spell resolves, **Then** the `kicker_count` field on the resolved stack entry reflects the chosen value.

---

### User Story 21 - Equipment Attach / Detach Mechanics (Priority: P2-HIGH)

Cards with the Equip keyword can be attached to creatures by paying the equip cost as a sorcery-speed activated ability. Fortify does the same for Fortifications. Currently these keywords are parsed but attaching does nothing and no equip actions are generated.

**Why this priority**: Equipment is one of the most popular card categories in all formats (Swords of X and Y, Lightning Greaves, etc.). Without attach mechanics, equipped permanents provide no benefit.

**Independent Test**: Put an equipment on the battlefield. Verify an equip legal action appears. Take the action targeting a creature. Verify the equipment's `attached_to` field is set and the creature gains the equipment's bonuses.

**Acceptance Scenarios**:

1. **Given** Player A controls an unattached equipment during their main phase, **When** legal actions are computed, **Then** an `equip` action is emitted for each legal target creature they control.
2. **Given** Player A takes the equip action targeting a creature, **When** the cost is paid, **Then** the equipment's `attached_to` is set to the creature's ID and the creature gains the equipment's P/T bonus and keywords.
3. **Given** an equipped creature leaves the battlefield, **When** SBAs are checked, **Then** the equipment becomes unattached and stays on the battlefield.
4. **Given** an equipment is already attached to a creature, **When** the equip action targets a different creature, **Then** the equipment detaches from the first and attaches to the second.
5. **Given** a creature has Lightning Greaves attached, **When** the creature would be targeted, **Then** Hexproof from the Greaves prevents targeting.

---

### User Story 22 - Transform / Double-Faced Cards (Priority: P2-HIGH)

Permanents with transform conditions (e.g., Werewolves, Arlinn Kord) should flip between their front and back faces when their conditions are met. Currently card faces are stored in `card.faces` but the transform action is never triggered.

**Why this priority**: Transform cards appear throughout Magic history (Innistrad, Eldritch Moon, Midnight Hunt, etc.) and their alternate faces are often the entire point of the card.

**Independent Test**: Put a Werewolf on the battlefield. Advance to the next upkeep without casting spells. Verify the Werewolf has transformed to its night side (type/P/T changes to back face).

**Acceptance Scenarios**:

1. **Given** a Werewolf permanent has no spells cast last turn, **When** the active player's upkeep trigger fires, **Then** the permanent transforms to its Night side (face index 1).
2. **Given** a transformed Werewolf is on the battlefield and 2+ spells are cast in a turn, **When** the active player's upkeep trigger fires, **Then** the permanent transforms back to its Day side (face index 0).
3. **Given** a permanent with an explicit transform trigger ("When X happens, transform"), **When** that trigger fires, **Then** the permanent transforms.
4. **Given** a transformed permanent's current side has different P/T, keywords, and oracle text, **When** the permanent is transformed, **Then** the active face data is used for all game rules purposes.
5. **Given** `GameState.spells_cast_this_turn` tracks spells cast during the turn, **When** the upkeep fires, **Then** it is compared to the werewolf transform condition.

---

### User Story 23 - Sacrifice Trigger Detection (Priority: P2-HIGH)

"When you sacrifice X" and "Whenever a creature is sacrificed" triggers are never detected or fired. The sacrifice action occurs (permanent leaves the battlefield) but no triggered abilities respond.

**Why this priority**: Sacrifice synergies are the backbone of entire archetypes (aristocrats, Goblin sacrifice, token sacrifice, etc.).

**Independent Test**: Put a "when you sacrifice a creature, draw a card" enchantment on the battlefield. Sacrifice a creature. Verify the enchantment's trigger fires and a card is drawn.

**Acceptance Scenarios**:

1. **Given** a permanent has "when you sacrifice [permanent type]" in its oracle text, **When** a matching permanent is sacrificed, **Then** that trigger is queued in pending_triggers.
2. **Given** a permanent has "whenever a creature is sacrificed" trigger, **When** any controller sacrifices a creature, **Then** the trigger fires.
3. **Given** a sacrifice trigger fires, **When** it resolves, **Then** the associated effect is applied.
4. **Given** a card says "sacrifice X: [effect]" as an activated ability, **When** the ability resolves, **Then** any "when you sacrifice" triggers that match also fire.

---

### User Story 24 - Cast Triggers ("When You Cast a Spell") (Priority: P2-HIGH)

Triggered abilities that fire when spells are cast (e.g., Guttersnipe's "whenever you cast an instant or sorcery, deal 2 damage to each opponent") are not detected or fired. Currently cast triggers silently no-op.

**Why this priority**: Cast triggers are the foundation of spellslinger archetypes and appear on iconic cards like Guttersnipe, Niv-Mizzet, and Monastery Mentor.

**Independent Test**: Put Guttersnipe on the battlefield. Cast a Lightning Bolt. Verify Guttersnipe's trigger fires and deals 2 damage to the opponent.

**Acceptance Scenarios**:

1. **Given** a permanent has "whenever you cast an instant or sorcery" trigger, **When** the controller casts an instant or sorcery, **Then** the trigger is queued.
2. **Given** a "whenever you cast a spell" trigger, **When** any spell is cast by the controller, **Then** the trigger fires.
3. **Given** triggers fire after a spell is placed on the stack, **When** the cast trigger resolves, **Then** the original spell is still on the stack and resolves normally after.
4. **Given** a cast trigger fires due to a cascade-cast spell, **When** it resolves, **Then** the cast trigger applies (cascaded spells are cast).

---

### User Story 25 - Loyalty Ability Turn Limit (Priority: P2-HIGH)

Planeswalker loyalty abilities can currently be activated multiple times per turn. CR 606.3 states a loyalty ability may only be activated once per turn and only during the controller's main phase.

**Why this priority**: This is a basic planeswalker rules violation. Without enforcement, planeswalkers are dramatically overpowered.

**Independent Test**: Activate a planeswalker loyalty ability once. Verify the ability does not appear in legal actions again until the next turn.

**Acceptance Scenarios**:

1. **Given** a planeswalker has not activated a loyalty ability this turn, **When** legal actions are computed during the controller's main phase, **Then** the loyalty ability actions are listed.
2. **Given** a planeswalker has already activated a loyalty ability this turn, **When** legal actions are computed, **Then** no loyalty ability actions are listed for that planeswalker.
3. **Given** the turn advances, **When** legal actions are computed on the next turn, **Then** the loyalty ability is available again.
4. **Given** it is not the planeswalker controller's main phase, **When** legal actions are computed, **Then** no loyalty ability actions are listed.

---

### User Story 26 - Mana Ability Special Timing (Priority: P2-HIGH)

Mana abilities (CR 605.1: activated abilities that add mana to the mana pool) can be activated at any time, including times when other activated abilities cannot be activated. Currently mana abilities are gated by the same priority rules as other activated abilities.

**Why this priority**: Players cannot pay mana costs mid-resolution if mana abilities require priority. This breaks the fundamental casting flow.

**Independent Test**: Cast a spell requiring {G}{G}. Activate two Forests for mana while casting (before placing spell on stack). Verify the land tap actions are available without requiring priority outside of the casting sequence.

**Acceptance Scenarios**:

1. **Given** a player is paying a mana cost, **When** they activate a mana ability (tap a land), **Then** the action is allowed without requiring the player to have priority.
2. **Given** a split-second spell is on the stack, **When** a player activates a mana ability, **Then** the activation is allowed (split second does not stop mana abilities).
3. **Given** a mana ability is activated, **Then** it does not use the stack — it resolves immediately.
4. **Given** a mana dork (creature with "{T}: Add {G}") is on the battlefield, **When** a player is paying for a spell, **Then** the creature's mana ability can be activated.

---

### User Story 27 - Buyback and Retrace (Priority: P3-LOW)

Buyback allows a spell to be returned to hand instead of the graveyard if its buyback cost was paid. Retrace allows a sorcery to be cast from the graveyard by discarding a land. Neither is implemented.

**Why this priority**: Both appear on enough cards to be archetype-relevant (Capsize is a classic Buyback card; Raven's Crime and Worm Harvest are key Retrace cards).

**Acceptance Scenarios**:

1. **Given** Player A has a Buyback card in hand with enough mana to pay both the base cost and the buyback cost, **When** legal actions are computed, **Then** a cast-with-buyback action is emitted.
2. **Given** Player A casts a spell with buyback and the spell resolves, **When** it would go to the graveyard, **Then** instead it returns to the caster's hand.
3. **Given** Player A has a Retrace card in the graveyard and a land in hand, **When** it is their main phase, **Then** a retrace cast action is emitted that discards a land as part of the cost.
4. **Given** a Retrace spell resolves, **When** it is placed in the graveyard, **Then** it is available to retrace again on the next turn.

---

### User Story 28 - Cycling Trigger Detection (Priority: P3-MEDIUM)

Some cards have additional effects when cycled ("When you cycle this card, ..."). Currently even basic cycling is not implemented (see US18), and cycling triggers are additionally absent.

**Acceptance Scenarios**:

1. **Given** a card has a cycling trigger, **When** the card is cycled, **Then** the trigger fires after the draw.
2. **Given** multiple cycling triggers exist (e.g., Fluctuator reduces cycling cost, Drake Haven creates a token on cycle), **When** a card is cycled, **Then** all relevant triggers fire.

---

### User Story 29 - Saga Chapter Progression (Priority: P3-MEDIUM)

Sagas are enchantments that add a lore counter at the beginning of each controller's main phase and trigger chapter abilities based on the counter count. When the final chapter triggers, the Saga is sacrificed. None of this is detected or implemented.

**Why this priority**: Sagas are in many popular recent sets (Theros Beyond Death, Kaldheim, Modern Horizons 2, etc.).

**Independent Test**: Put a 3-chapter Saga on the battlefield. Verify Chapter I triggers when it first enters. Advance through turns verifying Chapter II and III. After Chapter III, verify the Saga is sacrificed.

**Acceptance Scenarios**:

1. **Given** a Saga enters the battlefield, **When** it ETBs, **Then** a lore counter is added and Chapter I effect fires.
2. **Given** a Saga is on the battlefield at the beginning of the controller's precombat main phase, **When** the phase begins, **Then** a lore counter is added and the matching chapter(s) trigger.
3. **Given** a Saga's lore counter count equals its final chapter number after that chapter triggers, **When** the chapter trigger resolves, **Then** the Saga is sacrificed.

---

### User Story 30 - Adventure Cards (Priority: P3-MEDIUM)

Adventure cards can be cast for their adventure spell (instant or sorcery) and then exiled; from exile the creature can be cast for its regular mana cost on a later turn. Currently adventure is not detected.

**Why this priority**: Adventure cards appear in Eldraine and Wilds of Eldraine sets (Brazen Borrower, Giant Killer, Edgewall Innkeeper synergies, etc.).

**Independent Test**: Put a creature with Adventure in hand. Verify both a "cast creature" and "cast adventure spell" action appear. Take the adventure action. Verify the card is in exile and a "cast from exile" action appears.

**Acceptance Scenarios**:

1. **Given** Player A has an Adventure card in hand during their main phase, **When** legal actions are computed, **Then** two cast actions appear: one for the creature and one for the adventure spell.
2. **Given** Player A casts the adventure spell and it resolves, **When** it goes to exile, **Then** the card is marked as `adventured=True` in exile.
3. **Given** an adventured card is in Player A's exile zone, **When** legal actions are computed on any subsequent turn, **Then** a cast-from-exile action appears for the creature side.
4. **Given** Player A casts the creature from exile, **When** it resolves, **Then** the creature enters the battlefield normally.

---

### User Story 31 - Proliferate (Priority: P3-MEDIUM)

Proliferate allows the player to choose any number of permanents and players that already have counters, then add one more counter of a type already there. Currently not detected or implemented.

**Why this priority**: Proliferate appears on multiple popular cards and is a core mechanic in poison/counter archetypes.

**Independent Test**: Put a creature with 2 +1/+1 counters and a planeswalker with 3 loyalty on the battlefield. Cast a Proliferate spell. Verify the player is prompted to choose, and the chosen permanents each gain one more counter.

**Acceptance Scenarios**:

1. **Given** a spell with Proliferate resolves, **When** the effect is applied, **Then** `pending_proliferate_choice` is set on game state listing all valid targets (players/permanents with counters).
2. **Given** the player submits their proliferate choices, **When** the choice is processed, **Then** each chosen permanent gains one counter of a type it already has.
3. **Given** poison counters exist on a player, **When** proliferate targets that player, **Then** they gain one more poison counter.

---

### User Story 32 - Infect and Wither in Combat (Priority: P3-MEDIUM)

Infect creatures deal damage to creatures as -1/-1 counters and to players as poison counters. Wither deals damage to creatures as -1/-1 counters but deals normal damage to players. Currently both keywords are parsed but combat damage is still applied as normal damage rather than as counters.

**Why this priority**: Infect is an entire archetype (Phyrexian Crusader, Glistener Elf, etc.) that cannot function without this rule.

**Acceptance Scenarios**:

1. **Given** an Infect creature deals combat damage to a player, **When** damage resolves, **Then** the player receives poison counters equal to the damage amount (not life loss).
2. **Given** an Infect creature deals combat damage to a blocking creature, **When** damage resolves, **Then** the blocking creature receives -1/-1 counters equal to the damage amount.
3. **Given** a Wither creature deals damage to a creature, **When** damage resolves, **Then** the creature receives -1/-1 counters.
4. **Given** a Wither creature deals damage to a player, **When** damage resolves, **Then** the player loses that much life (not poison counters).

---

### User Story 33 - AI Discard and Tutor Choice Selection (Priority: P3-MEDIUM)

When `pending_discard_choice` or `pending_tutor_choice` is set on the game state, the heuristic AI receives a blocking `choice` legal action but has no logic to evaluate which card to discard or search for. It currently auto-selects index 0.

**Why this priority**: Discard and tutor choices are among the most impactful AI decisions in any given game. The AI should discard its least-valuable card and tutor for the most-valuable card.

**Independent Test**: The opponent's Thoughtseize prompts the AI to discard. Verify the AI discards its lowest-value card (e.g., land over key spell).

**Acceptance Scenarios**:

1. **Given** `pending_discard_choice` is set with a list of cards, **When** the heuristic AI evaluates, **Then** it selects the card with the lowest `_score_cast` value.
2. **Given** `pending_tutor_choice` is set with a list of cards, **When** the heuristic AI evaluates, **Then** it selects the card with the highest `_score_cast` value given the current board state.
3. **Given** the AI is discarding in cleanup, **When** over hand size, **Then** lands are discarded last, spells with the worst situational score are discarded first.

---

### User Story 34 - Token Creation Triggers (Priority: P3-MEDIUM)

"Whenever you create a token" triggers (e.g., Anointed Procession, Doubling Season effects) are not detected or fired. Token creation occurs but no triggers respond to it.

**Why this priority**: Token creation triggers are the engine of token/go-wide archetypes. Cards like Anointed Procession are powerful precisely because of this interaction.

**Acceptance Scenarios**:

1. **Given** a permanent has "whenever you create a token" trigger, **When** any token is created under the controller's control, **Then** the trigger is queued.
2. **Given** Doubling Season (or similar) is on the battlefield, **When** a token would be created, **Then** a replacement effect doubles the number of tokens created.
3. **Given** a token is created by a spell effect, **When** the token ETBs, **Then** ETB triggers fire for the token normally.

---

### User Story 35 - Ninjutsu (Priority: P4-LOW)

Ninjutsu is an activated ability (cost: return an unblocked attacking creature you control to hand) that lets a Ninja enter the battlefield from hand tapped and attacking. Currently the keyword is parsed but the mechanic is not implemented.

**Acceptance Scenarios**:

1. **Given** Player A has a Ninja with Ninjutsu in hand and an unblocked attacker, **When** legal actions are computed during the blockers step or combat damage step, **Then** a ninjutsu action appears.
2. **Given** Player A takes the ninjutsu action, **When** it resolves, **Then** the chosen attacker is returned to hand, the Ninja enters tapped and attacking, and ETB triggers fire.
3. **Given** the Ninja is now attacking unblocked, **When** combat damage resolves, **Then** the Ninja deals its power in damage.

---

### User Story 36 - Ward Enforcement (Priority: P1-HIGH)

Ward is partially implemented (pending_ward_payment field exists) but enforcement is incomplete. When a permanent with Ward is targeted by an opponent's spell, the opponent must pay the ward cost or the spell is countered for that target.

**Why this priority**: Ward is on hundreds of modern cards (Goldspan Dragon, Raffine, Professor Onyx, etc.) and is the primary protection mechanic in recent sets.

**Independent Test**: Target a Ward {2} creature with a removal spell. Verify `pending_ward_payment` is set. Decline to pay. Verify the removal spell is countered for that target.

**Acceptance Scenarios**:

1. **Given** a creature with Ward {2} is targeted by an opponent's spell, **When** the spell goes on the stack, **Then** `pending_ward_payment` is set and a `pay_ward` or `decline_ward` legal action is emitted.
2. **Given** the opponent pays the ward cost, **When** the choice is submitted, **Then** the spell resolves normally against the ward creature.
3. **Given** the opponent declines to pay the ward cost, **When** the choice is submitted, **Then** the spell is countered (removed from stack, goes to graveyard).
4. **Given** Ward {life}: pay 3 life variant, **When** the opponent chooses to pay, **Then** 3 life is deducted from their life total.

---

### User Story 37 - Counter Synergy Effects (Priority: P4-LOW)

Effects like "if a creature would be put into a graveyard with a counter on it, exile it instead" (Solemnity-adjacent), "+1/+1 counters are put on in addition" (Hardened Scales), and other counter-interaction replacement effects are not detected.

**Acceptance Scenarios**:

1. **Given** Hardened Scales is on the battlefield and a creature would receive N +1/+1 counters, **When** the counters are applied, **Then** the creature receives N+1 counters instead.
2. **Given** a permanent that replaces counter placement, **When** a counter would be placed, **Then** the replacement effect fires before the counter is applied.

---

### User Story 38 - Entwine (Priority: P3-LOW)

Entwine lets you pay an additional cost to choose all modes of a modal spell instead of just one. Currently modal spells require explicit mode selection; there is no Entwine implementation.

**Acceptance Scenarios**:

1. **Given** a player has an Entwine card and enough mana to pay both the base cost and entwine cost, **When** legal actions are computed, **Then** an entwine cast action (select all modes) is emitted alongside single-mode actions.
2. **Given** an Entwine spell resolves with entwine paid, **When** it resolves, **Then** all modes apply.

---

### User Story 39 - Replicate (Priority: P3-LOW)

Replicate lets you pay a spell's replicate cost multiple times to create additional copies of the spell on the stack.

**Acceptance Scenarios**:

1. **Given** a Replicate spell is cast with replicate paid N times, **When** it resolves, **Then** N copies are created on the stack (in addition to the original).
2. **Given** Replicate copies are on the stack, **When** they resolve, **Then** each applies the spell's effect independently.

---

### User Story 40 - Morph and Megamorph (Priority: P3-MEDIUM)

Morph allows creatures to be cast face-down as a 2/2 for {3}, then turned face-up later by paying their morph cost. Megamorph is similar but adds a +1/+1 counter when turned up. Currently the mechanic is not implemented.

**Why this priority**: Morph appears across Onslaught, Khans of Tarkir, and is a defining Limited mechanic.

**Acceptance Scenarios**:

1. **Given** Player A has a Morph creature in hand, **When** legal actions are computed during their main phase, **Then** a "cast face-down" action is emitted for {3}.
2. **Given** Player A casts a morph creature face-down, **When** it enters the battlefield, **Then** it appears as a 2/2 colorless creature with no name or abilities shown.
3. **Given** a face-down creature is on the battlefield and Player A can pay its morph cost, **When** legal actions are computed during their main phase, **Then** a "turn face-up" action is emitted.
4. **Given** Player A turns a face-down creature face-up, **When** it turns, **Then** it becomes the card's actual front face; turn-face-up triggers fire.

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

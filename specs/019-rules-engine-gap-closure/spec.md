# Feature Specification: Rules Engine Gap Closure

**Feature Branch**: `019-rules-engine-gap-closure`
**Created**: 2026-03-29
**Status**: Draft

## Overview

Close the remaining rules engine gaps identified in a comprehensive analysis between the MTG engine and the Forge reference implementation. This feature addresses critical missing behaviors across triggered abilities, combat mechanics, keyword enforcement, stack mechanics, zone transitions, planeswalkers, counters, and Commander format rules. The goal is near-Forge parity for the most impactful rules areas.

---

## User Scenarios & Testing

### User Story 1 - Spell Cast Trigger Detection (Priority: P1-CRITICAL)

When any player casts a spell, all permanents with "whenever you cast a spell" or "whenever a player casts a spell" abilities must detect the cast event and put their triggers on the stack. This is the foundation for prowess, storm, and hundreds of common cards.

**Why this priority**: Spell cast triggers are the most commonly missing trigger category. Prowess alone is on 50+ widely-played creatures. Without this, entire mechanic categories (storm, magecraft, spell-matter) are completely broken.

**Independent Test**: Put a creature with "Whenever you cast an instant or sorcery spell, this creature gets +1/+1 until end of turn" (Prowess) on the battlefield. Cast a Lightning Bolt. Verify the creature gets +1/+1.

**Acceptance Scenarios**:

1. **Given** a creature with "Whenever you cast a spell, this creature gets +1/+1 until end of turn" is on the battlefield, **When** the controller casts any spell, **Then** a trigger is placed on the stack granting +1/+1 until end of turn.
2. **Given** a permanent with "Whenever a player casts a spell, draw a card", **When** either player casts a spell, **Then** the trigger fires for each spell cast.
3. **Given** two prowess creatures on the battlefield, **When** one spell is cast, **Then** both triggers fire independently and stack correctly.
4. **Given** a spell is countered, **When** the counter resolves, **Then** cast triggers that already fired remain on the stack (triggers fire on cast, not resolution).
5. **Given** the active player casts a spell during their main phase, **When** the cast is confirmed, **Then** cast triggers from both players' permanents are collected and put on the stack in APNAP order.

---

### User Story 2 - Attack and Block Trigger Detection (Priority: P1-CRITICAL)

When a creature attacks, triggers with "whenever [this creature / a creature / creatures you control] attacks" must fire. When a creature blocks, "when/whenever [this creature] blocks" triggers fire.

**Why this priority**: Attack triggers are fundamental — exalted, battle cry, and hundreds of individual creature abilities depend on them. Without attack triggers, combat-themed cards are completely non-functional.

**Independent Test**: Put a creature with "Whenever this creature attacks, it gets +2/+0 until end of turn" on the battlefield. Declare it as an attacker. Verify it gains +2/+0.

**Acceptance Scenarios**:

1. **Given** a creature with "Whenever this creature attacks, it gets +2/+0 until end of turn", **When** it is declared as an attacker, **Then** a trigger fires granting +2/+0 until end of turn.
2. **Given** a creature with "Whenever a creature you control attacks, draw a card", **When** any creature is declared as an attacker under that player's control, **Then** the draw trigger fires.
3. **Given** multiple creatures attack simultaneously, **When** attackers are declared, **Then** each individual attack trigger fires once per attacking creature that meets the condition.
4. **Given** a creature with "Whenever this creature blocks, it gets +0/+2 until end of turn", **When** it is declared as a blocker, **Then** the block trigger fires.
5. **Given** a creature with "Whenever this creature attacks alone, it gets +1/+1 until end of turn", **When** it is the only attacker, **Then** the trigger fires; **When** two creatures attack, **Then** the trigger does NOT fire.

---

### User Story 3 - Double Strike Two-Step Damage Resolution (Priority: P1-CRITICAL)

Creatures with double strike must deal damage in both the first-strike damage step and the regular combat damage step. The first-strike step must fully resolve (including SBAs checking for creature deaths) before the regular step begins.

**Why this priority**: Double strike is on widely-played creatures. Currently `has_first_strike_combatants()` detects the presence of first-strike/double-strike creatures but the two-step damage flow is never triggered — double-strike creatures only hit once.

**Independent Test**: Declare a 2/2 Double Strike creature as an attacker against a 3/3 blocker. After first-strike damage the blocker has 2 damage marked. After regular damage the blocker has 4 total damage and dies. The attacker takes 3 damage in the regular step.

**Acceptance Scenarios**:

1. **Given** a double-strike creature attacks a creature with higher toughness, **When** first-strike damage resolves, **Then** damage is marked; **When** regular combat damage resolves, **Then** the double-strike creature deals its power again.
2. **Given** a double-strike creature attacks a creature with toughness equal to the attacker's power, **When** first-strike damage resolves, **Then** the blocker dies and SBAs fire; **When** regular combat damage would resolve, **Then** the double-strike creature has no blocker and deals no damage (or trample damage if applicable).
3. **Given** only first-strike creatures (no double-strike) are in combat, **When** first-strike damage resolves, **Then** those creatures do NOT deal damage again in the regular step.
4. **Given** no first-strike or double-strike creatures are in combat, **When** combat damage resolves, **Then** only one combat damage step occurs.
5. **Given** a double-strike creature with lifelink, **When** it deals damage in both steps, **Then** the controller gains life equal to damage dealt in each step separately.

---

### User Story 4 - Keyword Mana Cost Modifiers (Priority: P1-HIGH)

Five keywords — Convoke, Delve, Improvise, Affinity, and Emerge — allow players to pay mana costs using alternative resources. Each must be detectable from card oracle text and reduce the effective mana cost during casting.

**Why this priority**: These keywords are format-defining. Affinity and Convoke enable entire archetypes. Delve enables graveyard-based decks. Without enforcement, these cards cost their full mana value, making them effectively unplayable as designed.

**Independent Test**: Cast a creature with "Convoke" and cost {3}{W}. Tap two white creatures before paying mana. Verify the mana cost is reduced to {1}.

**Acceptance Scenarios**:

1. **Given** a spell with Convoke, **When** the player taps creatures before confirming the cast, **Then** each tapped creature reduces the cost by {1} or one mana of a color matching that creature's color.
2. **Given** a spell with Delve, **When** the player exiles cards from their graveyard as part of casting, **Then** each exiled card reduces the generic cost by {1}.
3. **Given** a spell with Improvise, **When** the player taps artifacts before confirming the cast, **Then** each tapped artifact reduces the generic cost by {1}.
4. **Given** a spell with "Affinity for artifacts" and cost {5}, **When** the player controls 3 artifacts, **Then** the effective cost is {2}.
5. **Given** a spell with Emerge and cost {6}{G}, **When** the player sacrifices a creature with CMC 3, **Then** the effective cost is {3}{G}.
6. **Given** any of these alternative-cost keywords, **When** the player does not use the alternative payment, **Then** the spell can still be cast at its full mana cost.

---

### User Story 5 - Persist and Undying Death Replacement Effects (Priority: P1-HIGH)

When a creature with Persist dies with no -1/-1 counter on it, instead of going to the graveyard it returns to the battlefield with a -1/-1 counter. When a creature with Undying dies with no +1/+1 counter on it, it returns with a +1/+1 counter.

**Why this priority**: Persist and Undying are keywords on many widely-played creatures and define entire archetypes (Kitchen Finks, Mikaeus combos). Currently they are parsed and stored but never enforced — these creatures simply die normally.

**Independent Test**: Put a creature with Persist and no -1/-1 counters on the battlefield. Destroy it. Verify it returns to the battlefield with a -1/-1 counter instead of going to the graveyard.

**Acceptance Scenarios**:

1. **Given** a creature with Persist has no -1/-1 counter, **When** it would be put into the graveyard from the battlefield, **Then** instead it returns to the battlefield under its owner's control with a -1/-1 counter.
2. **Given** a creature with Persist already has a -1/-1 counter, **When** it would die, **Then** it goes to the graveyard normally (persist does not trigger again).
3. **Given** a creature with Undying has no +1/+1 counter, **When** it would be put into the graveyard from the battlefield, **Then** instead it returns to the battlefield under its owner's control with a +1/+1 counter.
4. **Given** a creature with Undying already has a +1/+1 counter, **When** it would die, **Then** it goes to the graveyard normally.
5. **Given** a creature has both Persist and Undying, **When** it dies with neither counter, **Then** the controller chooses which replacement effect applies.

---

### User Story 6 - Storm Spell Copies (Priority: P1-HIGH)

When a spell with Storm resolves, the engine counts all spells cast before it this turn and creates that many copies of the storm spell on the stack. Copies do not go to the graveyard when they leave the stack.

**Why this priority**: Storm is a defining mechanic in Legacy and Vintage (Tendrils of Agony, Grapeshot, Empty the Warrens). Without it, entire storm combo decks are non-functional.

**Independent Test**: Cast three spells in a turn, then cast a storm spell (storm count = 3). Verify 3 copies of the spell appear on the stack, each resolving independently.

**Acceptance Scenarios**:

1. **Given** a player casts 3 spells before casting a storm spell, **When** the storm spell resolves, **Then** 3 copies are created on the stack.
2. **Given** storm copies are on the stack, **When** the copies resolve, **Then** they do NOT go to the graveyard (copies cease to exist, CR 706.10).
3. **Given** a storm spell resolves with 0 prior spells this turn, **When** it resolves, **Then** no copies are created.
4. **Given** a storm spell is cast, **When** the turn counter is checked, **Then** storm count equals spells cast this turn BEFORE the storm spell itself (the storm spell does not count itself).
5. **Given** a player's storm spell is countered, **When** the counter resolves, **Then** no storm copies are created (storm triggers on resolution, not cast).

---

### User Story 7 - Buyback and Replicate (Priority: P2-HIGH)

Buyback allows paying an additional cost when casting a spell to return it to hand instead of the graveyard on resolution. Replicate allows paying the kicker cost multiple times — each additional payment creates one copy of the spell on the stack.

**Why this priority**: Both mechanics enable key archetypes. Buyback enables recurring effect engines. Replicate is the Izzet mechanic for spell-copy builds.

**Independent Test (Buyback)**: Cast a spell with "Buyback {3}" paying the buyback cost. Verify it returns to hand on resolution instead of going to the graveyard.

**Independent Test (Replicate)**: Cast a spell with "Replicate {R}" and pay the replicate cost twice. Verify two copies appear on the stack.

**Acceptance Scenarios**:

1. **Given** a spell with Buyback is cast with the buyback cost paid, **When** it resolves, **Then** it returns to the caster's hand instead of going to the graveyard.
2. **Given** a spell with Buyback is cast without paying buyback, **When** it resolves, **Then** it goes to the graveyard as normal.
3. **Given** a spell with Replicate is cast, **When** the player pays the replicate cost N additional times, **Then** N copies of the spell are placed on the stack.
4. **Given** replicate copies are on the stack, **When** the copies resolve, **Then** the copies do not go to the graveyard (copies cease to exist).
5. **Given** a replicate spell with targets required, **When** copies are created, **Then** the player may choose new targets for each copy.

---

### User Story 8 - Flashback and Escape Zone Casting (Priority: P2-HIGH)

Flashback allows casting a spell from the graveyard at an alternate cost; on resolution it is exiled. Escape allows casting from the graveyard by paying a mana cost plus exiling a specified number of other graveyard cards.

**Why this priority**: Flashback is one of the most common graveyard mechanics across multiple sets (Odyssey block, Modern Horizons, Strixhaven). Escape is the Theros Beyond Death set mechanic. Both are unplayable without this implementation.

**Independent Test**: Put a spell with "Flashback {2}{R}" in the graveyard. Cast it from the graveyard for {2}{R}. Verify it resolves and is then exiled (not returned to graveyard).

**Acceptance Scenarios**:

1. **Given** a spell with a Flashback cost is in the graveyard, **When** the player casts it from the graveyard, **Then** it is cast at the flashback cost (not the normal mana cost).
2. **Given** a flashback spell resolves, **When** it leaves the stack, **Then** it is exiled, not put into the graveyard.
3. **Given** a flashback spell is countered, **When** it would go to the graveyard, **Then** it is instead exiled.
4. **Given** a spell with "Escape — {3}{B}, Exile four other cards from your graveyard", **When** the player casts it from the graveyard, **Then** the player pays {3}{B} AND exiles four other cards from their graveyard as the cost.
5. **Given** an escape spell resolves, **When** it leaves the stack, **Then** it is exiled, not returned to the graveyard.

---

### User Story 9 - Cycling Mechanic (Priority: P2-MEDIUM)

Cycling is an activated ability: pay the cycling cost, discard the card, draw a card. Cycling triggers ("whenever you cycle a card") fire when a card is cycled.

**Why this priority**: Cycling is an evergreen mechanic appearing in Onslaught, Ikoria, and many other sets. Without it, any cycling card is just an expensive spell with no filtering option.

**Independent Test**: Put a card with "Cycling {2}" in hand. Activate cycling. Verify the card is discarded and a new card is drawn.

**Acceptance Scenarios**:

1. **Given** a card with Cycling in hand, **When** the player pays the cycling cost and discards it, **Then** it moves to the graveyard and the player draws one card.
2. **Given** a cycling card is cycled, **When** the cycling ability resolves, **Then** any "whenever you cycle" triggers fire.
3. **Given** a card with "Cycling {0}", **When** cycled, **Then** the player discards it and draws without paying any mana.
4. **Given** a card with a specific cycling trigger "When you cycle [card name], [effect]", **When** it is cycled, **Then** both the draw and the specific trigger fire.
5. **Given** cycling is an activated ability, **When** the player activates it, **Then** it can be activated at instant speed (unless the card specifies otherwise).

---

### User Story 10 - Dredge Draw Replacement (Priority: P2-MEDIUM)

Dredge N is a replacement effect: whenever a player would draw a card, they may instead return the dredge card from their graveyard to hand by milling N cards.

**Why this priority**: Dredge is the defining mechanic of the Legacy Dredge deck. Without it, any dredge card in the graveyard is simply a dead card with no way to leverage the mechanic.

**Independent Test**: Put a card with "Dredge 6" in the graveyard. On the next draw step, choose to dredge instead of drawing. Verify 6 cards are milled and the dredge card returns to hand.

**Acceptance Scenarios**:

1. **Given** a card with Dredge N is in the graveyard, **When** the controller would draw a card, **Then** they may instead mill N cards and return the dredge card to hand.
2. **Given** a player chooses to dredge, **When** there are fewer than N cards in their library, **Then** they cannot dredge with that card (must draw normally or choose another dredge card with a lower N).
3. **Given** multiple dredge cards are in the graveyard, **When** the player would draw, **Then** they choose which dredge card to use (or draw normally).
4. **Given** a dredge card is returned to hand via dredge, **When** it is later discarded again, **Then** it is available to dredge again on future draws.
5. **Given** a dredge replacement is used, **When** the milled cards include dredge cards, **Then** those newly milled dredge cards are available for future draw replacements.

---

### User Story 11 - Suspend Auto-Cast (Priority: P2-MEDIUM)

When a suspended card has its last time counter removed during upkeep, it must be automatically cast for free. Creature spells cast via suspend gain haste.

**Why this priority**: Suspended cards already track time counter decrements correctly but never trigger the free cast. Any suspended card is effectively trapped in exile once its counters reach zero.

**Independent Test**: Suspend a creature card with 2 time counters. After 2 upkeeps when the last counter is removed, verify the creature is cast for free and enters the battlefield with haste.

**Acceptance Scenarios**:

1. **Given** a suspended card has exactly 1 time counter at the start of upkeep, **When** the upkeep action removes it, **Then** the card is cast as a spell for free (without paying its mana cost).
2. **Given** a suspended creature is cast via suspend, **When** it enters the battlefield, **Then** it has haste until end of turn.
3. **Given** a suspended non-creature (instant or sorcery) is cast via suspend, **When** it resolves, **Then** it resolves as normal with no haste rule.
4. **Given** a suspended spell is cast for free, **When** it is on the stack, **Then** it may be countered like any other spell.
5. **Given** a suspended spell's free cast is countered, **When** it is countered, **Then** it goes to the graveyard (not back to exile with time counters).

---

### User Story 12 - Command Tax Enforcement (Priority: P1-CRITICAL)

Each time a commander is cast from the command zone, it costs {2} more per previous time it was cast from the command zone this game. The `commander_cast_count` field exists but is never used in cost calculation.

**Why this priority**: Command tax is a fundamental Commander format rule. Without it, commanders cost the same every time, making commander decks dramatically stronger than intended and breaking the format's core risk/reward structure.

**Independent Test**: Cast a commander with CMC 4 from the command zone ({4}). It dies and returns to the command zone. Cast it a second time. Verify the cost is now {6}.

**Acceptance Scenarios**:

1. **Given** a commander is cast from the command zone for the first time, **When** its cost is calculated, **Then** the cost equals its printed mana cost with no additional tax.
2. **Given** a commander has been cast from the command zone once before, **When** its cost is calculated for the second cast, **Then** the cost equals its printed mana cost plus {2}.
3. **Given** a commander has been cast N times from the command zone, **When** the cost is calculated, **Then** the cost equals the printed mana cost plus {2N}.
4. **Given** a commander is returned to hand (not command zone) and recast from hand, **When** its cost is calculated, **Then** no additional tax applies (tax only applies when cast from command zone).
5. **Given** command tax applies, **When** the player cannot afford the taxed cost, **Then** the cast is not allowed even if they could afford the base cost.

---

### User Story 13 - Proliferate (Priority: P2-MEDIUM)

Proliferate is an effect that allows the player to choose any number of permanents and/or players that have at least one counter, then put one additional counter of each type already on each chosen permanent or player.

**Why this priority**: Proliferate appears on 30+ cards and enables counter-doubling strategies. Without it, proliferate cards do nothing after resolution.

**Independent Test**: Have a permanent with two +1/+1 counters and a player with two poison counters. Trigger proliferate. Verify the permanent now has three +1/+1 counters and the player has three poison counters.

**Acceptance Scenarios**:

1. **Given** proliferate resolves, **When** the player selects a permanent with counters, **Then** one counter of each type already on that permanent is added.
2. **Given** proliferate resolves, **When** the player selects a player with poison counters, **Then** that player gains one more poison counter.
3. **Given** a permanent has both +1/+1 and charge counters, **When** proliferate targets it, **Then** it gains one +1/+1 counter AND one charge counter.
4. **Given** proliferate resolves, **When** the player chooses no targets, **Then** nothing happens (choosing zero targets is valid).
5. **Given** a planeswalker has loyalty counters, **When** it is selected for proliferate, **Then** it gains one additional loyalty counter.

---

### User Story 14 - Sagas and Lore Counters (Priority: P2-MEDIUM)

Sagas are enchantments that enter with one lore counter. At the beginning of each controller's upkeep, one lore counter is added. Each chapter ability (I, II, III, etc.) triggers when its lore counter count is reached. After the final chapter triggers, the saga is sacrificed.

**Why this priority**: Sagas are featured in every recent set (Dominaria, Kaldheim, Modern Horizons 2). Without saga mechanics, these cards enter the battlefield and do nothing.

**Independent Test**: Put a three-chapter saga on the battlefield. Verify it enters with one lore counter and chapter I triggers immediately. After the next upkeep, chapter II triggers. After the following upkeep, chapter III triggers and then the saga is sacrificed.

**Acceptance Scenarios**:

1. **Given** a saga enters the battlefield, **When** it enters, **Then** it immediately gets one lore counter and chapter I ability triggers.
2. **Given** a saga is on the battlefield at the beginning of the controller's upkeep, **When** the upkeep begins, **Then** one lore counter is added and the corresponding chapter ability triggers.
3. **Given** a saga gets its final chapter lore counter, **When** the final chapter ability triggers and resolves, **Then** the saga is sacrificed.
4. **Given** a saga has multiple chapter abilities at the same chapter number, **When** lore counter count reaches that number, **Then** all matching chapter abilities trigger simultaneously.
5. **Given** a saga is removed from the battlefield before reaching its final chapter, **When** it leaves, **Then** no additional sacrifice trigger fires.

---

### User Story 15 - World Enchantment SBA (Priority: P2-MEDIUM)

When more than one world enchantment is simultaneously on the battlefield, all but the one with the most recent timestamp are put into their owners' graveyards as a state-based action.

**Why this priority**: World enchantments are a legacy mechanic. Without this SBA, having two world enchantments creates an illegal game state that should be self-correcting.

**Independent Test**: Put two different world enchantments on the battlefield simultaneously. Verify SBAs put all but the most recently played one into their owners' graveyards.

**Acceptance Scenarios**:

1. **Given** two world enchantments are on the battlefield, **When** SBAs are checked, **Then** all but the one with the most recent entry timestamp are put into their owners' graveyards.
2. **Given** a world enchantment enters while another is already on the battlefield, **When** SBAs are checked after the ETB, **Then** the older world enchantment goes to its owner's graveyard.
3. **Given** only one world enchantment is on the battlefield, **When** SBAs are checked, **Then** it remains on the battlefield unaffected.
4. **Given** a world enchantment is removed by this SBA, **When** it leaves, **Then** any "when this leaves the battlefield" triggers fire normally.

---

### User Story 16 - Unearth End-of-Turn Exile SBA (Priority: P1-CRITICAL)

Permanents returned via Unearth have the `unearthed=True` flag set in the model, but no SBA currently exiles them at the end step. They must be exiled at the beginning of the end step, and if they would leave the battlefield for any other reason, they go to exile instead of the graveyard.

**Why this priority**: The `unearthed` flag already exists — this is purely a missing SBA. Without it, unearthed creatures remain permanently on the battlefield.

**Independent Test**: Unearth a creature. Advance to the end step. Verify the creature is in exile, not the battlefield or graveyard.

**Acceptance Scenarios**:

1. **Given** a permanent with `unearthed=True` is on the battlefield, **When** the beginning of the end step occurs, **Then** it is exiled.
2. **Given** an unearthed creature would be destroyed or put into the graveyard for any reason, **When** that event occurs, **Then** it goes to exile instead (replacement effect).
3. **Given** an unearthed creature is targeted by an exile effect directly, **When** the exile resolves, **Then** it goes to exile normally.
4. **Given** an unearthed creature leaves the battlefield during the opponent's end step, **When** the opponent's end step begins, **Then** the unearth exile SBA still applies.
5. **Given** an unearthed creature is bounced to hand, **When** it returns to hand, **Then** the `unearthed` flag is cleared (it is a new object; no longer subject to exile).

---

### User Story 17 - Planeswalker Rules Enforcement (Priority: P2-MEDIUM)

Three planeswalker rules are currently missing: (1) loyalty abilities may only be activated once per turn; (2) damage dealt to a player may be redirected to a planeswalker they control (CR 644); (3) emblems from planeswalker ultimates have no model or tracking.

**Why this priority**: The once-per-turn rule is trivially exploitable without enforcement. Damage redirect is standard planeswalker gameplay. Emblems appear in nearly every planeswalker ultimate.

**Independent Test**: Activate a planeswalker loyalty ability. Attempt to activate it a second time this turn. Verify the second activation is rejected.

**Acceptance Scenarios**:

1. **Given** a planeswalker's loyalty ability has been activated this turn, **When** the player attempts to activate any loyalty ability of that planeswalker again, **Then** the activation is rejected.
2. **Given** the turn passes to the next turn, **When** the player attempts to activate a loyalty ability again, **Then** it is allowed (once-per-turn resets each turn).
3. **Given** a player controls a planeswalker and an opponent's spell would deal damage to that player, **When** the damage would be assigned, **Then** the player may redirect any or all of that damage to their planeswalker.
4. **Given** a planeswalker's ultimate resolves with "You get an emblem with...", **When** it resolves, **Then** an Emblem is added to the game state under that player's control with the specified ability.
5. **Given** a player has an emblem with a triggered or static ability, **When** the emblem's condition is met, **Then** the emblem's ability functions like a permanent's ability.

---

### User Story 18 - Exalted and Battle Cry Combat Keywords (Priority: P2-MEDIUM)

Exalted: whenever a creature attacks alone, each exalted instance on permanents the controller controls fires, giving +1/+1 until end of turn to the lone attacker. Battle cry: whenever a creature with battle cry attacks, other attacking creatures get +1/+0 until end of turn.

**Why this priority**: Both are attack-based keywords that depend on US2 (attack trigger detection). Exalted was the signature mechanic of Conflux/Alara Reborn sets and sees competitive play.

**Independent Test**: Control two permanents with Exalted. Attack with exactly one creature. Verify that creature gets +2/+2 (two exalted triggers).

**Acceptance Scenarios**:

1. **Given** a player controls two permanents with Exalted and attacks with exactly one creature, **When** the attack is declared, **Then** two exalted triggers fire, each giving the lone attacker +1/+1 until end of turn.
2. **Given** a player attacks with two or more creatures, **When** the attack is declared, **Then** exalted triggers do NOT fire.
3. **Given** a creature with Battle Cry attacks alongside other creatures, **When** the attack is declared, **Then** all other attacking creatures get +1/+0 until end of turn.
4. **Given** two creatures with Battle Cry attack together, **When** the attack is declared, **Then** each other attacker gets +2/+0 (one from each battle cry trigger).
5. **Given** a creature with both Exalted and Battle Cry attacks alone, **When** the attack is declared, **Then** exalted triggers fire; battle cry does not boost itself.

---

### User Story 19 - Partner Commanders (Priority: P3-LOW)

If both commanders in the command zone have the Partner keyword (or matching "Partner with [name]" keyword), they may both be used as the player's commanders simultaneously. Commander damage is tracked per commander. Command tax applies to each commander individually.

**Why this priority**: Partner commanders are a Commander-only mechanic from Commander 2016 and Battlebond. Without it, partner pairs are unusable in the Commander format.

**Independent Test**: Start a game with two commanders that both have Partner. Verify both are in the command zone. Cast one; verify the other remains. Cast the other; verify command tax applies based on each card's individual cast count.

**Acceptance Scenarios**:

1. **Given** two commanders both with the Partner keyword are chosen, **When** the game starts, **Then** both are placed in the command zone.
2. **Given** two partner commanders are in the command zone, **When** one is cast, **Then** the other remains in the command zone.
3. **Given** a commander with "Partner with [Name]" is chosen, **When** validating the second commander, **Then** only "[Name]" is accepted as the partner.
4. **Given** each partner commander has its own cast count, **When** command tax is calculated, **Then** each commander's tax is based only on its own number of previous casts.
5. **Given** a player controls both partner commanders, **When** commander damage is tracked, **Then** damage from each commander is tracked separately with an independent 21-damage threshold per commander.

---

### User Story 20 - Multiplayer "Each Opponent" Targeting (Priority: P3-LOW)

Effects that say "each opponent" must apply to all opponents individually. In a 3+ player game, "target opponent" must prompt the player to select which opponent.

**Why this priority**: Commander is a multiplayer format. Without this, "each opponent discards a card" only hits one player, fundamentally breaking symmetrical effects.

**Independent Test**: In a 3-player game, resolve "each opponent loses 2 life." Verify both opponents each lose 2 life (4 total life lost).

**Acceptance Scenarios**:

1. **Given** a 3-player game where player A casts "each opponent loses 2 life", **When** it resolves, **Then** both B and C each lose 2 life.
2. **Given** a 2-player game, **When** "each opponent" resolves, **Then** only the one opponent is affected (no behavior change).
3. **Given** a 3-player game and a spell with "target opponent", **When** the spell is cast, **Then** the caster is prompted to choose which opponent to target.
4. **Given** a spell with "each opponent" and the caster has no opponents remaining, **When** it resolves, **Then** nothing happens.
5. **Given** a player leaves the game mid-resolution of "each opponent", **When** the effect resolves, **Then** the leaving player is unaffected but remaining opponents are still affected.

---

### Edge Cases

- What happens when a persist creature returns with a -1/-1 counter and immediately has its counters removed? (It can persist again on next death since the -1/-1 counter is gone.)
- How does storm count interact with copies on the stack? (Copies are not "cast" so they do not increment the storm count.)
- Can a player cycle a card in response to a spell? (Yes — cycling is an activated ability usable at instant speed unless the card specifies otherwise.)
- How does command tax interact with cost reduction effects? (Tax is added to the total cost; cost reducers apply after; tax cannot reduce the cost below {0}.)
- What happens if a saga has all its lore counters removed by an effect? (It stays on the battlefield; the sacrifice SBA only fires after the final chapter ability resolves.)
- Can a flashback spell be cast from exile? (No — flashback only works from the graveyard.)
- What happens with double strike when a creature gains it mid-combat after first-strike damage? (It only deals regular damage once; double strike must be present before the first-strike step.)
- Can convoke tap a creature with summoning sickness? (No — tapping a creature for convoke still requires tapping, which summoning sickness prevents.)
- Can a player redirect damage from a spell to a planeswalker even if the spell's target was the planeswalker? (No — redirection only applies when the damage targets the player; if it already targets the planeswalker, no redirection is needed.)

---

## Requirements

### Functional Requirements

- **FR-001**: The trigger system MUST detect spell cast events and check all permanents' oracle text for "whenever you cast a spell" and "whenever a player casts a spell" patterns.
- **FR-002**: Cast triggers MUST fire immediately when a spell is placed on the stack (not when it resolves).
- **FR-003**: The trigger system MUST detect attack declaration events and fire triggers matching "whenever [creature/type] attacks" patterns.
- **FR-004**: The trigger system MUST detect block declaration events and fire triggers matching "when/whenever [creature] blocks" patterns.
- **FR-005**: Combat damage resolution MUST support a two-step flow: first-strike/double-strike damage step followed by a regular damage step when first-strike or double-strike creatures are present in combat.
- **FR-006**: SBAs MUST be run between the first-strike damage step and the regular combat damage step.
- **FR-007**: The mana cost calculation system MUST support Convoke (tap creatures to pay costs during casting).
- **FR-008**: The mana cost calculation system MUST support Delve (exile graveyard cards to pay generic costs).
- **FR-009**: The mana cost calculation system MUST support Improvise (tap artifacts to pay generic costs).
- **FR-010**: The mana cost calculation system MUST support Affinity (count permanents of type to reduce cost).
- **FR-011**: The mana cost calculation system MUST support Emerge (sacrifice creature, reduce cost by its CMC).
- **FR-012**: The replacement effect system MUST implement Persist: creature with Persist and no -1/-1 counter returns to battlefield with -1/-1 counter instead of going to graveyard.
- **FR-013**: The replacement effect system MUST implement Undying: creature with Undying and no +1/+1 counter returns to battlefield with +1/+1 counter instead of going to graveyard.
- **FR-014**: The stack system MUST implement Storm: on resolution, count spells cast before this spell this turn, create that many copies on the stack.
- **FR-015**: Storm copies MUST cease to exist when they leave the stack (not go to graveyard).
- **FR-016**: The stack system MUST implement Buyback: detect buyback cost in oracle text; on resolution with buyback paid, return to hand instead of graveyard.
- **FR-017**: The stack system MUST implement Replicate: detect replicate cost in oracle text; each additional replicate payment creates one copy on the stack.
- **FR-018**: The stack system MUST auto-detect Flashback cost from oracle text and allow casting from graveyard.
- **FR-019**: Flashback spells MUST be exiled on resolution (or when countered) rather than returned to the graveyard.
- **FR-020**: The stack system MUST support Escape: detect escape cost in oracle text; require exiling N other graveyard cards as part of casting cost.
- **FR-021**: Escape spells MUST be exiled on resolution rather than returned to the graveyard.
- **FR-022**: The game system MUST support Cycling as an activated ability: pay cycling cost, discard the card, draw a card.
- **FR-023**: Cycling MUST emit a "cycled" event that triggers "whenever you cycle" abilities.
- **FR-024**: The draw replacement system MUST support Dredge: when a player would draw, they may instead return a dredge card from graveyard to hand by milling N cards.
- **FR-025**: Dredge replacement MUST be optional; players may choose to draw normally instead.
- **FR-026**: The upkeep trigger system MUST detect suspended cards at 0 time counters and cast them for free.
- **FR-027**: Creatures cast via suspend MUST receive haste until end of turn.
- **FR-028**: In Commander format, the cost calculation for casting from the command zone MUST add {2} per `commander_cast_count` for that commander.
- **FR-029**: After each commander cast from the command zone, `commander_cast_count` MUST be incremented.
- **FR-030**: The game system MUST support a Proliferate action: choose any permanents/players with counters, add one counter of each type already present.
- **FR-031**: Sagas MUST enter the battlefield with one lore counter and immediately trigger their first chapter ability.
- **FR-032**: At the beginning of each controller's upkeep, sagas MUST gain one lore counter and trigger the corresponding chapter ability.
- **FR-033**: When a saga's final chapter ability resolves, the saga MUST be sacrificed.
- **FR-034**: The SBA system MUST implement the world enchantment rule: when two or more world enchantments are on the battlefield, all but the most recently entered one go to their owners' graveyards.
- **FR-035**: The SBA system MUST exile permanents with `unearthed=True` at the beginning of the end step.
- **FR-036**: If an unearthed permanent would leave the battlefield for any reason other than direct exile, it MUST go to exile instead (replacement effect).
- **FR-037**: Planeswalker loyalty ability activation MUST be blocked if `loyalty_activated_this_turn` is True for that permanent.
- **FR-038**: `loyalty_activated_this_turn` MUST be reset at the beginning of each turn's upkeep step.
- **FR-039**: The damage system MUST allow players to redirect combat/spell damage targeting them to a planeswalker they control (CR 644).
- **FR-040**: An Emblem model MUST be added to the game state with: controller, source planeswalker name, and abilities list.
- **FR-041**: Emblem abilities MUST function identically to permanent abilities of the same type (triggered, static, activated).
- **FR-042**: Exalted MUST be implemented as an attack trigger: when a creature attacks alone, each exalted instance on permanents the controller controls triggers +1/+1 on that attacker.
- **FR-043**: Battle cry MUST be implemented as an attack trigger: when a battle-cry creature attacks, all other attacking creatures get +1/+0 until end of turn.
- **FR-044**: In Commander format, two commanders with the Partner keyword MUST both be placed in the command zone at game start.
- **FR-045**: Partner commander validation MUST accept only Partner+Partner or "Partner with [Name]"+matching name combinations.
- **FR-046**: Each partner commander MUST have its own independent `commander_cast_count` and command tax calculation.
- **FR-047**: Commander damage MUST be tracked per commander in multi-commander setups.
- **FR-048**: Effects with "each opponent" wording MUST be applied to every opponent individually, not just one.
- **FR-049**: In games with 3+ players, "target opponent" effects MUST require the caster to choose a specific opponent.

### Key Entities

- **Emblem**: Controller player name, source planeswalker name, list of ability strings. Stored in the game state's `emblems` collection per player.
- **StormCount**: Per-turn integer tracking total spells cast before the current one. Stored on GameState as `spells_cast_this_turn: int`.
- **CyclingEvent**: Event emitted when a card is cycled, carrying the cycled card's name and type for trigger matching.
- **DredgeChoice**: A pending choice presented to a player's draw step when a dredge card is in their graveyard.
- **ProliferateTargets**: A set of (permanent_id | player_name, counter_type) pairs representing the proliferate selections.
- **SagaState**: Tracks `lore_counter` count on the Permanent model; chapter triggers are derived from the saga's oracle text.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 421 existing tests continue to pass after implementing this feature (zero regressions).
- **SC-002**: A creature with Prowess gains +1/+1 when its controller casts a spell, verified by automated test.
- **SC-003**: A storm spell cast after 5 prior spells this turn produces exactly 5 copies on the stack, verified by automated test.
- **SC-004**: A commander cast for the third time from the command zone costs {4} more than its printed mana cost, verified by automated test.
- **SC-005**: A creature with Double Strike deals combat damage in two separate steps with SBAs checked in between, verified by automated test.
- **SC-006**: A creature with Persist returns to the battlefield with a -1/-1 counter instead of going to the graveyard, verified by automated test.
- **SC-007**: A flashback spell resolves and is exiled rather than going to the graveyard, verified by automated test.
- **SC-008**: A suspended card with its last time counter removed is automatically cast for free and enters with haste, verified by automated test.
- **SC-009**: Cycling a card draws exactly one card and fires any "whenever you cycle" triggers, verified by automated test.
- **SC-010**: In a 3-player game, "each opponent loses 2 life" causes both opponents to each lose 2 life, verified by automated test.

---

## Assumptions

- The existing trigger system's pattern-matching infrastructure will be extended (not replaced) for cast and attack triggers.
- Keyword mana cost modifiers (Convoke, Delve, etc.) will require new API request fields to indicate which creatures/cards/artifacts are being tapped/exiled as payment.
- Storm count (`spells_cast_this_turn`) will be tracked on GameState and reset at the beginning of each turn.
- Dredge is a player choice — the engine will present a pending choice to the player rather than auto-dredging.
- Flashback cost detection will use regex matching on oracle_text for the pattern `Flashback {cost}`.
- Escape cost detection will use regex matching on oracle_text for the pattern `Escape — {cost}, Exile N other cards from your graveyard`.
- Saga chapter text follows Scryfall data conventions.
- The `loyalty_activated_this_turn` flag already exists on the Permanent model; only the enforcement check is missing.
- Partner validation occurs at game creation time.
- The multiplayer "each opponent" implementation assumes the engine structurally supports 3+ players (multiple players in `game_state.players`).

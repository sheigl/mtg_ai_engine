# Feature Specification: Rules Engine Complete Parity

**Feature Branch**: `020-rules-engine-complete-parity`
**Created**: 2026-04-01
**Status**: Draft

## Overview

Achieve complete MTG Comprehensive Rules parity by closing all 30 remaining gaps identified in the post-019 gap analysis. This feature addresses critical missing behaviors in the cleanup step, targeting enforcement (hexproof/shroud/protection), mana ability resolution, split card / MDFC casting, ETB replacement effects, trigger pattern recognition, legend rule player choice, toughness-0 vs destruction semantics, blocker damage assignment ordering, additional combat phases, step-level phase skipping, ward enforcement, kicker effect application, damage doubling/tripling, phasing, vehicles/crew, morph/megamorph, adventure cards, persistent mana pools, split second vs activated abilities, type-changing layer effects, snow mana tracking, trample over planeswalkers, flanking, fading, echo, P/T switching, foretell mechanics, and mutate. Together these close the gap between the engine and a full Comprehensive Rules implementation.

---

## User Scenarios & Testing

### User Story 1 - Cleanup Step Implementation (Priority: P1-CRITICAL)

The cleanup step (CR 514) is the final step of the ending phase and must perform three actions in order: (a) the active player discards down to their maximum hand size (CR 514.1), (b) all damage marked on permanents is removed and all "until end of turn" and "this turn" effects expire (CR 514.2), and (c) no player receives priority during cleanup unless a state-based action fires or a triggered ability triggers — in which case SBAs are checked, triggers are put on the stack, priority is given, and then another cleanup step begins (CR 514.3a).

**Why this priority**: The cleanup step is reached every single turn. Without it, damage accumulates across turns (making all creatures effectively fragile), "until end of turn" pump effects become permanent, and hand-size limits are never enforced. This corrupts every game that lasts more than one turn cycle.

**Independent Test**: End a turn where the active player has 9 cards in hand with a max hand size of 7. Verify the player is prompted to discard 2 cards. After discarding, verify all damage on creatures is removed and any +1/+1 "until end of turn" bonus from a pump spell has expired.

**Acceptance Scenarios**:

1. **Given** the active player has 9 cards in hand and max_hand_size is 7, **When** the cleanup step begins, **Then** the player must discard exactly 2 cards of their choice.
2. **Given** a creature has 3 damage marked on it, **When** the cleanup step processes, **Then** damage_marked is reset to 0.
3. **Given** a creature received +2/+2 "until end of turn" from Giant Growth, **When** the cleanup step processes, **Then** the power_bonus and toughness_bonus fields are reset to 0.
4. **Given** no SBAs fire and no triggers are placed during cleanup, **When** cleanup completes, **Then** no player receives priority and the turn ends immediately.
5. **Given** an SBA fires during cleanup (e.g. a creature now has 0 toughness after "until end of turn" bonus expires), **When** SBAs are checked, **Then** the SBA is processed, priority is granted to the active player, and a new cleanup step begins after the stack empties.
6. **Given** a triggered ability fires during cleanup (e.g. "at the beginning of the next cleanup step"), **When** triggers are placed, **Then** priority is granted and a new cleanup step occurs after the stack empties.

---

### User Story 2 - Hexproof, Shroud, and Protection Targeting Enforcement (Priority: P1-CRITICAL)

When a player casts a spell or activates an ability that targets a permanent or player, the engine must enforce hexproof (CR 702.11), shroud (CR 702.18), and protection (CR 702.16) as targeting restrictions. A permanent with hexproof cannot be the target of spells or abilities controlled by opponents. A permanent with shroud cannot be the target of any spell or ability. A permanent with protection from [quality] cannot be the target of spells or abilities with that quality. The helper `_has_hexproof_or_shroud()` exists in `combat.py` but is never invoked in the spell/ability targeting pipeline.

**Why this priority**: Hexproof and shroud are among the most commonly relevant keywords in competitive Magic. Without enforcement, removal spells freely target creatures that should be immune — fundamentally breaking the game balance for any deck running hexproof or shroud creatures, and making protection entirely decorative.

**Independent Test**: Put a creature with hexproof on the battlefield controlled by Player B. Have Player A attempt to cast Murder targeting that creature. Verify the cast is rejected with an illegal-target error. Then have Player B attempt to target their own hexproof creature with a pump spell — verify it succeeds.

**Acceptance Scenarios**:

1. **Given** a permanent has hexproof and is controlled by Player B, **When** Player A attempts to target it with a spell, **Then** the target is rejected as illegal.
2. **Given** a permanent has hexproof and is controlled by Player B, **When** Player B targets their own hexproof permanent, **Then** the target is legal (hexproof only restricts opponents).
3. **Given** a permanent has shroud, **When** any player (including the controller) attempts to target it with a spell or ability, **Then** the target is rejected.
4. **Given** a creature has protection from red, **When** a player casts a red spell targeting it, **Then** the target is rejected.
5. **Given** a creature has protection from red, **When** a player casts a blue spell targeting it, **Then** the target is legal.
6. **Given** a creature has protection from creatures, **When** a creature-sourced ability targets it, **Then** the target is rejected.

---

### User Story 3 - Mana Abilities Bypass the Stack (Priority: P1-CRITICAL)

Mana abilities (CR 605) are activated abilities that could produce mana when they resolve, do not have a target, and are not loyalty abilities. Mana abilities do not go on the stack — they resolve immediately when activated (CR 605.3b). A player may activate mana abilities at any time they have priority, including during the announcement of another spell or ability (to pay costs), and even while a spell with split second is on the stack (CR 702.61a). Currently the engine routes all abilities through the stack, which means tapping a land for mana incorrectly uses the stack and can be blocked by split second.

**Why this priority**: Every game involves tapping lands for mana. If mana abilities use the stack, any spell with split second locks players out of tapping lands entirely. More fundamentally, the game flow is incorrect — mana abilities should resolve instantly, not wait for priority passes.

**Independent Test**: Have a player tap a Forest for {G} while a split second spell is on the stack. Verify the mana is added to the player's mana pool immediately and the split second spell remains unaffected. Then verify the player cannot activate a non-mana ability while split second is on the stack.

**Acceptance Scenarios**:

1. **Given** a permanent has an activated ability that produces mana, has no target, and is not a loyalty ability, **When** the player activates it, **Then** the ability resolves immediately without going on the stack.
2. **Given** a spell with split second is on the stack, **When** a player activates a mana ability, **Then** the activation is legal and resolves immediately.
3. **Given** a spell with split second is on the stack, **When** a player attempts to activate a non-mana activated ability, **Then** the activation is rejected.
4. **Given** a player is in the process of casting a spell, **When** they need to pay mana costs, **Then** they can activate mana abilities as part of the payment process.
5. **Given** an activated ability produces mana but also targets a permanent, **When** the player activates it, **Then** it goes on the stack (it is NOT a mana ability due to having a target).

---

### User Story 4 - Split Cards and MDFC Casting (Priority: P1-CRITICAL)

Split cards (CR 709), modal double-faced cards (MDFCs, CR 712), and aftermath cards (CR 702.125) have two faces that can each be cast independently. The `Card.faces` field already stores `CardFace` objects for each half, but no logic exists to select which face to cast. Split cards allow casting the left or right half from hand; fuse allows casting both halves as a single spell if the card has fuse. MDFCs allow casting the front face normally or playing the back face (often a land) from hand. Aftermath cards allow casting the first half from hand and the second half from the graveyard.

**Why this priority**: MDFCs and split cards are ubiquitous in Standard, Modern, and Commander. Pathway lands (MDFCs) are in every mana base. Without face selection, these cards are entirely uncastable — they show as a single card with combined text that matches no valid spell type.

**Independent Test**: Create a split card "Fire // Ice" with `faces = [CardFace(name="Fire", mana_cost="{1}{R}", ...), CardFace(name="Ice", mana_cost="{1}{U}", ...)]`. Cast the "Fire" half by submitting `face_index=0`. Verify it goes on the stack with Fire's mana cost and effect. Then cast "Ice" with `face_index=1`. Verify it uses Ice's cost and effect.

**Acceptance Scenarios**:

1. **Given** a split card with two faces in hand, **When** the player casts with `face_index=0`, **Then** the left half's name, mana cost, type line, and oracle text are used for the stack object.
2. **Given** a split card with two faces in hand, **When** the player casts with `face_index=1`, **Then** the right half's name, mana cost, type line, and oracle text are used.
3. **Given** a split card with the fuse keyword, **When** the player casts with `fuse=True`, **Then** both halves are combined into a single spell on the stack with the total mana cost of both halves.
4. **Given** an MDFC whose back face is a land, **When** the player plays it as a land, **Then** the back face enters the battlefield as the land type indicated on the back face.
5. **Given** an aftermath card in the graveyard, **When** the player casts the second half from the graveyard, **Then** the card is exiled after resolution (not returned to graveyard).
6. **Given** a split card in hand, **When** legal actions are computed, **Then** separate legal actions appear for each castable face (and fuse if applicable).

---

### User Story 5 - ETB Replacement Effects (Priority: P1-CRITICAL)

When a permanent enters the battlefield, replacement effects from other permanents on the battlefield may modify how it enters (CR 614.1c). Common examples: "Nonbasic lands enter tapped" (Thalia, Heretic Cathar), "Creatures your opponents control enter tapped" (Blind Obedience via extort), "enters with N +1/+1 counters" modified by doubling season. The `put_permanent_onto_battlefield()` function accepts a `tapped=` parameter but does not consult the board state for effects that impose entering tapped or modify counter amounts.

**Why this priority**: ETB replacement effects are pervasive in competitive play. Thalia, Blood Moon making lands enter as Mountains, and counter-doubling effects (Doubling Season, Vorinclex) are format staples. Without this pipeline, these cards have no functional effect on other permanents entering the battlefield.

**Independent Test**: Put Thalia, Heretic Cathar (nonbasic lands enter tapped) on the battlefield. Play a nonbasic land. Verify it enters the battlefield tapped. Play a basic land and verify it enters untapped.

**Acceptance Scenarios**:

1. **Given** a permanent with "Nonbasic lands enter the battlefield tapped" is on the battlefield, **When** a nonbasic land enters, **Then** it enters tapped regardless of the `tapped` parameter passed.
2. **Given** a permanent with "Creatures your opponents control enter the battlefield tapped" is controlled by Player A, **When** Player B puts a creature onto the battlefield, **Then** the creature enters tapped.
3. **Given** Doubling Season is on the battlefield ("if an effect would put one or more counters, put twice that many instead"), **When** a creature enters with 2 +1/+1 counters, **Then** it enters with 4 +1/+1 counters.
4. **Given** no ETB replacement effects are on the battlefield, **When** a creature enters the battlefield, **Then** it enters with its default state (untapped, base counters).
5. **Given** multiple ETB replacement effects apply to the same permanent entering, **When** the permanent enters, **Then** the affected player chooses the order in which to apply replacement effects (CR 616.1).

---

### User Story 6 - Extended Trigger Pattern Recognition (Priority: P1-CRITICAL)

The regex-based trigger detection in `triggers.py` currently handles approximately 15 patterns. Many common trigger conditions are not recognized: "whenever you gain life", "whenever a land enters the battlefield", "whenever a spell or ability an opponent controls counters a spell you control", "whenever you draw a card", "whenever an enchantment enters", "whenever a creature you control dies", "whenever you sacrifice a permanent", and "at the beginning of your end step". Each unrecognized pattern means the corresponding card's triggered ability is silently ignored.

**Why this priority**: Triggered abilities are on the majority of played permanents. Missing patterns mean entire card categories are non-functional: lifegain payoffs (Soul Warden, Ajani's Pridemate), landfall (Lotus Cobra, Omnath), death triggers (Blood Artist, Zulaport Cutthroat), draw triggers (Consecrated Sphinx), and sacrifice triggers (Korvold). This is the single largest category of missing functionality.

**Independent Test**: Put a permanent with "Whenever you gain life, put a +1/+1 counter on this creature" on the battlefield. Gain 3 life. Verify 3 separate triggers are placed on the stack (one per life-gain event).

**Acceptance Scenarios**:

1. **Given** a permanent with "Whenever you gain life, put a +1/+1 counter on this creature", **When** the controller gains life, **Then** a trigger is placed on the stack for each discrete life-gain event.
2. **Given** a permanent with "Whenever a land enters the battlefield under your control" (landfall), **When** a land enters the controller's battlefield, **Then** the trigger fires.
3. **Given** a permanent with "Whenever a creature you control dies", **When** a creature the controller owns is put into the graveyard from the battlefield, **Then** the trigger fires.
4. **Given** a permanent with "Whenever you draw a card", **When** the controller draws one or more cards, **Then** a trigger fires for each card drawn.
5. **Given** a permanent with "Whenever you sacrifice a permanent", **When** the controller sacrifices a permanent, **Then** the trigger fires.
6. **Given** a permanent with "At the beginning of your end step", **When** the controller's end step begins, **Then** the trigger fires.

---

### User Story 7 - Legend Rule Player Choice (Priority: P1-HIGH)

When a player controls two or more legendary permanents with the same name, state-based actions require that player to choose one to keep and put the rest into their owner's graveyard (CR 704.5j). The current `sba.py` implementation auto-selects the permanent with the highest timestamp. The same applies to the planeswalker uniqueness rule (CR 704.5j) — the player must choose which to keep.

**Why this priority**: The legend rule interaction is a deliberate strategic choice in many decks. Cloning a legendary creature to remove the opponent's copy (by forcing yourself to legend-rule your own, keeping the clone) is a well-known play pattern. Auto-keeping the newest removes this strategic dimension.

**Independent Test**: Control two legendary permanents with the same name (e.g. by casting Clone targeting your own legend). Verify the game pauses with a `pending_legend_choice` prompt requiring the controller to choose which to keep. Submit the choice and verify the unchosen one goes to the graveyard.

**Acceptance Scenarios**:

1. **Given** a player controls two legendary permanents with the same name, **When** SBAs are checked, **Then** a `pending_legend_choice` is set requiring the player to choose which to keep.
2. **Given** a pending legend choice exists, **When** the player submits their choice, **Then** the chosen permanent stays and the other is put into the graveyard.
3. **Given** three legendary permanents with the same name exist under one controller, **When** SBAs fire, **Then** the player chooses one to keep and the other two go to the graveyard.
4. **Given** two players each control a legendary permanent with the same name, **When** SBAs are checked, **Then** no legend rule applies (each player independently controls only one).
5. **Given** a pending legend choice, **When** the player chooses the older permanent, **Then** the newer one is put into the graveyard (confirming the choice is not auto-resolved).

---

### User Story 8 - Toughness-0 is Not Destruction (Priority: P1-HIGH)

When a creature has 0 or less toughness, it is put into its owner's graveyard as a state-based action (CR 704.5f). This is NOT destruction — it cannot be replaced by regeneration or indestructible. Currently `sba.py` routes toughness-0 through `_destroy_permanent()`, which incorrectly allows regeneration shields to prevent the creature from dying.

**Why this priority**: This is a rules correctness issue that affects layer interactions. Giving a creature -N/-N to reduce toughness to 0 should kill it even if it has a regeneration shield or is indestructible. The current implementation incorrectly allows these to save the creature, which is wrong per CR 704.5f.

**Independent Test**: Give an indestructible creature -X/-X to reduce its toughness to 0. Verify it is put into the graveyard. Then give a creature with an active regeneration shield -X/-X to 0 toughness and verify it dies without the regeneration shield activating.

**Acceptance Scenarios**:

1. **Given** a creature has toughness 0 or less after continuous effects, **When** SBAs are checked, **Then** it is put into the graveyard without going through the destruction pipeline.
2. **Given** an indestructible creature has 0 toughness, **When** SBAs are checked, **Then** it is put into the graveyard (indestructible does not prevent this).
3. **Given** a creature with a regeneration shield has 0 toughness, **When** SBAs are checked, **Then** it is put into the graveyard and the regeneration shield is NOT consumed.
4. **Given** a creature has toughness reduced to 0 by a -X/-X effect, **When** the effect resolves and SBAs fire, **Then** the creature dies even if it has "protection from" the source color.
5. **Given** a creature has base toughness 1 and receives -1/-1 from a layer 7c effect, **When** SBAs are checked, **Then** the creature is put into the graveyard via the non-destruction path.

---

### User Story 9 - Blocker Damage Assignment Order (Priority: P1-HIGH)

When an attacking creature is blocked by multiple creatures, the attacking player must order the blockers (CR 509.2). During the combat damage step, the attacker must assign at least lethal damage to the first blocker in the order before assigning any damage to the next (CR 510.1c). Currently damage is split evenly across blockers, which violates the assignment order rule and produces incorrect combat results.

**Why this priority**: Multi-block scenarios are common and the current even-split behavior produces incorrect combat outcomes. A 5/5 attacker blocked by a 1/1 and a 4/4 should kill both (assigning 1 to the first, 4 to the second), but even-splitting assigns 2 and 3, killing neither 4-toughness blocker.

**Independent Test**: Attack with a 5/5, blocked by a 2/2 and a 3/3. Set blocker order as [2/2, 3/3]. Verify that during damage assignment, at least 2 damage must go to the 2/2 before any damage goes to the 3/3. With default assignment, the 5/5 deals 2 to the 2/2 and 3 to the 3/3, killing both.

**Acceptance Scenarios**:

1. **Given** an attacker is blocked by two creatures and the blocker order is set, **When** combat damage is assigned automatically, **Then** lethal damage is assigned to the first blocker before any damage goes to the second.
2. **Given** an attacker with 5 power is blocked by a 2-toughness and a 3-toughness creature (in that order), **When** damage is assigned, **Then** 2 damage goes to the first blocker and 3 to the second.
3. **Given** an attacker with 3 power is blocked by two 3-toughness creatures, **When** damage is assigned, **Then** 3 damage goes to the first blocker and 0 to the second (insufficient power to reach second blocker).
4. **Given** an attacker has deathtouch and is blocked by two creatures, **When** damage is assigned, **Then** 1 damage (lethal due to deathtouch) goes to the first, and remaining power goes to the second.
5. **Given** an attacker has trample and all blockers have been assigned lethal damage, **When** excess damage exists, **Then** the excess tramples through to the defending player.

---

### User Story 10 - Additional Combat Phases (Priority: P1-HIGH)

Cards like Aurelia the Warleader and Aggravated Assault grant additional combat phases within a single turn. The `extra_turns` list exists for extra turns but there is no mechanism to insert additional combat phases into the current turn's phase sequence. When an effect grants an additional combat phase, the engine must queue a new combat phase (with all combat steps) to occur after the current combat phase or postcombat main phase.

**Why this priority**: Additional combat phases are central to aggro and combo strategies in Commander. Aurelia is one of the most popular Boros commanders. Without this, these cards have no effect and extra-combat strategies are impossible.

**Independent Test**: Trigger Aurelia the Warleader's attack trigger (first time she attacks each turn, get an additional combat phase after this one). Verify that after the current combat phase ends and the postcombat main phase completes, a new combat phase begins with all steps (beginning of combat through end of combat), followed by another postcombat main phase.

**Acceptance Scenarios**:

1. **Given** an effect grants an additional combat phase, **When** the current combat phase ends, **Then** a postcombat main phase occurs, followed by a new full combat phase (beginning of combat through end of combat).
2. **Given** an additional combat phase is queued, **When** it begins, **Then** creatures that attacked in a previous combat this turn can attack again (if untapped).
3. **Given** two additional combat phases are granted in the same turn, **When** combat resolves, **Then** both additional combat phases occur in sequence with postcombat main phases between them.
4. **Given** an additional combat phase is granted but no creatures can attack, **When** the additional combat phase begins, **Then** it still proceeds through its steps normally (even if no attackers are declared).
5. **Given** an additional combat phase, **When** "beginning of combat" triggers fire, **Then** they fire for the additional combat phase as well.

---

### User Story 11 - Step-Granular Phase Skipping (Priority: P1-HIGH)

The `phase_skip_flags` dict can skip entire phases, but some effects skip individual steps within a phase. Necropotence skips the draw step while keeping the upkeep step. Stasis skips the untap step. The engine needs a `step_skip_flags` mechanism that operates at step granularity within a phase, independent of the phase-level skip.

**Why this priority**: Necropotence is one of the most powerful cards in the game and defines multiple archetypes. Skipping the draw step is its core constraint. Without step-level skipping, implementing Necropotence forces skipping the entire beginning phase (losing upkeep too), which is incorrect.

**Independent Test**: Set `step_skip_flags["draw"] = True` for the active player. Advance to the beginning phase. Verify the untap step occurs, the upkeep step occurs, and the draw step is skipped.

**Acceptance Scenarios**:

1. **Given** `step_skip_flags["draw"]` is True for the active player, **When** the beginning phase processes, **Then** untap and upkeep steps occur normally but the draw step is skipped.
2. **Given** `step_skip_flags["untap"]` is True for the active player, **When** the beginning phase processes, **Then** the untap step is skipped but upkeep and draw occur.
3. **Given** both `step_skip_flags["draw"]` and `phase_skip_flags["beginning"]` are set, **When** the turn processes, **Then** the entire beginning phase is skipped (phase-level skip takes priority).
4. **Given** a step skip is in effect, **When** the skipped step would occur, **Then** no priority is granted and no triggers fire for that step.
5. **Given** a step skip expires ("skip your next draw step"), **When** the draw step is skipped once, **Then** the flag is cleared and subsequent turns draw normally.

---

### User Story 12 - Ward Enforcement (Priority: P1-HIGH)

Ward is a triggered ability: "Whenever this permanent becomes the target of a spell or ability an opponent controls, counter that spell or ability unless its controller pays [cost]" (CR 702.21). The current `_ward()` stub in `stack.py` logs a message but does not actually require payment or counter the spell. The engine must detect ward triggers when a permanent is targeted, prompt the targeting player to pay the ward cost, and counter the spell/ability if the cost is not paid.

**Why this priority**: Ward is evergreen since Strixhaven and appears on dozens of Standard and Commander staples. Without enforcement, ward creatures have no protection whatsoever, making the keyword entirely decorative.

**Independent Test**: Put a creature with "Ward {2}" on the battlefield. Have an opponent target it with a removal spell. Verify the game sets `pending_ward_payment` prompting the opponent to pay {2}. If they pay, the spell continues. If they decline, the spell is countered.

**Acceptance Scenarios**:

1. **Given** a creature has ward {2} and is targeted by an opponent's spell, **When** the targeting is confirmed, **Then** a `pending_ward_payment` is set with the ward cost.
2. **Given** a pending ward payment, **When** the player pays the ward cost, **Then** the spell remains on the stack and resolves normally.
3. **Given** a pending ward payment, **When** the player declines or cannot pay, **Then** the spell is countered and removed from the stack.
4. **Given** a creature has ward {2} and is targeted by the controller's own spell, **When** the targeting is confirmed, **Then** ward does NOT trigger (ward only triggers from opponents).
5. **Given** a creature has "Ward — Discard a card", **When** an opponent targets it, **Then** the opponent must discard a card or the spell is countered.

---

### User Story 13 - Kicker Effects Applied at Resolution (Priority: P1-HIGH)

The `kicker_paid` field exists on both `CastRequest` and `StackObject`, but kicker never modifies the spell's effect when it resolves. Kicker (CR 702.32) allows paying an additional cost when casting to enhance the spell's effect — additional damage, additional targets, extra counters, or a completely different mode. When a kicked spell resolves, the engine must detect `kicker_paid=True` on the StackObject and apply the kicked effect from the oracle text.

**Why this priority**: Kicker is a heavily-used mechanic spanning many sets. Cards like Rite of Replication (kicked = 5 copies instead of 1) and Jokulhaups variants define game-winning plays. The field exists and cost is already paid — only the resolution effect is missing.

**Independent Test**: Cast a spell with "Kicker {2}. When this spell enters the battlefield, it deals 2 damage to target creature. If it was kicked, it deals 4 damage instead." Pay the kicker cost. Verify the spell deals 4 damage on resolution, not 2.

**Acceptance Scenarios**:

1. **Given** a spell with kicker is cast and `kicker_paid=True`, **When** the spell resolves, **Then** the kicked effect from oracle_text is applied instead of (or in addition to) the base effect.
2. **Given** a spell with kicker is cast without paying kicker, **When** the spell resolves, **Then** only the base effect is applied.
3. **Given** a spell with multikicker and `kicker_count=3`, **When** it resolves, **Then** the kicker effect is applied 3 times.
4. **Given** a kicked spell that creates tokens, **When** it resolves with kicker, **Then** the token count matches the kicked version (e.g. 5 tokens instead of 1).
5. **Given** a kicked spell is copied on the stack, **When** the copy resolves, **Then** the copy retains the kicked status and applies the kicked effect.

---

### User Story 14 - Damage Doubling and Tripling (Priority: P1-HIGH)

Replacement effects that modify damage amounts — Dictate of the Twin Gods (double all damage), Fiery Emancipation (triple damage from sources you control), Gratuitous Violence (double creature combat damage) — are not implemented. These effects replace a damage event with a modified amount before the damage is dealt (CR 614.1a). Multiple doublers/triplers stack multiplicatively. Damage prevention shields interact with the final amount after modification.

**Why this priority**: Damage multipliers are a core strategy in Commander and are present in many competitive and casual decks. Without them, these permanents have no effect, and damage-centric strategies (Purphoros, Torbran) underperform dramatically.

**Independent Test**: Put Dictate of the Twin Gods on the battlefield. Deal 3 damage with Lightning Bolt. Verify 6 damage is dealt. Then add a second Dictate and verify 12 damage is dealt (double applied twice).

**Acceptance Scenarios**:

1. **Given** a permanent with "If a source would deal damage, it deals double that damage instead" is on the battlefield, **When** any source deals damage, **Then** the damage amount is doubled.
2. **Given** a permanent with "If a source you control would deal damage, it deals triple that damage instead", **When** a source the controller owns deals damage, **Then** the damage is tripled.
3. **Given** two damage doublers are on the battlefield, **When** damage is dealt, **Then** the damage is quadrupled (2x * 2x).
4. **Given** a damage doubler and a 3-damage prevention shield, **When** a source deals 3 damage (doubled to 6), **Then** 3 is prevented and 3 goes through.
5. **Given** a combat-only damage doubler (Gratuitous Violence), **When** a creature deals combat damage, **Then** the damage is doubled; **When** a creature deals non-combat damage (e.g. ping ability), **Then** the damage is NOT doubled.

---

### User Story 15 - Phasing (Priority: P1-HIGH)

Phasing (CR 702.25) causes permanents to "phase out" and "phase in" during the untap step. A phased-out permanent is treated as if it does not exist — it cannot be targeted, dealt damage, or interact with the game in any way. Auras, Equipment, and Fortifications attached to a phasing permanent phase out with it ("indirect phasing") and phase back in still attached. Tokens that phase out cease to exist. Phasing is relevant for Teferi's Protection, Teferi's Veil, and numerous older cards.

**Why this priority**: Teferi's Protection is one of the most played cards in Commander. Without phasing, it has no protective effect. Phasing is also core to several Legacy-playable cards and numerous Commander staples.

**Independent Test**: Phase out a creature with an Aura attached. Verify both the creature and the Aura are treated as not existing (not returned by battlefield queries, cannot be targeted). On the controller's next untap step, verify both phase back in with the Aura still attached.

**Acceptance Scenarios**:

1. **Given** a permanent phases out, **When** any game query asks about the battlefield, **Then** the phased-out permanent is excluded (as if it does not exist).
2. **Given** a permanent phases out with an Aura attached, **When** it phases out, **Then** the Aura phases out as well (indirect phasing).
3. **Given** a phased-out permanent exists, **When** the controller's untap step begins, **Then** the permanent phases back in before the untap occurs.
4. **Given** a token phases out, **When** it would phase back in, **Then** it ceases to exist instead (CR 702.25d).
5. **Given** a creature phases out, **When** a board wipe ("destroy all creatures") resolves, **Then** the phased-out creature is unaffected.
6. **Given** a permanent phases back in, **When** it returns, **Then** it does NOT trigger "enters the battlefield" abilities (phasing in is not entering).

---

### User Story 16 - Vehicles and Crew (Priority: P1-HIGH)

Vehicle artifacts (CR 702.122) have a crew cost. A player taps any number of creatures whose total power is greater than or equal to the crew number to "crew" the vehicle, turning it into an artifact creature until end of turn. Vehicles have power and toughness printed on them but are not creatures unless crewed (or animated by another effect). Crewing can only be done at sorcery speed (when you could cast a sorcery) unless another effect allows it.

**Why this priority**: Vehicles are a major card type appearing in multiple Standard-legal sets. Smuggler's Copter, Heart of Kiran, and Esika's Chariot are format staples. Without crewing, vehicles sit on the battlefield as non-creature artifacts that cannot attack or block.

**Independent Test**: Put a Vehicle with crew 3 on the battlefield. Tap two creatures with a combined power of 4. Verify the vehicle becomes an artifact creature until end of turn with its printed power and toughness. Verify it can now attack. At end of turn, verify it reverts to a non-creature artifact.

**Acceptance Scenarios**:

1. **Given** a Vehicle artifact is on the battlefield, **When** the player taps creatures with total power >= crew cost, **Then** the vehicle becomes an artifact creature until end of turn.
2. **Given** a crewed vehicle, **When** it attacks or blocks, **Then** combat proceeds normally using its printed power and toughness.
3. **Given** a vehicle, **When** the player taps creatures with total power < crew cost, **Then** the crew action is rejected.
4. **Given** a crewed vehicle, **When** the cleanup step occurs, **Then** the vehicle reverts to a non-creature artifact.
5. **Given** a vehicle on the battlefield, **When** legal actions are computed during the player's main phase, **Then** a "crew" action is available listing eligible creatures.

---

### User Story 17 - Morph and Megamorph (Priority: P1-HIGH)

Morph (CR 702.36) allows a player to cast a card face down as a 2/2 colorless creature for {3}. The player can turn it face up at any time by paying the morph cost (a special action that does not use the stack). Megamorph is identical but puts a +1/+1 counter on the creature when it turns face up. The `is_face_down` field on Permanent exists and `play_face_down`/`turn_face_up` are defined as SpecialActionRequest types, but no morph cost detection or face-up logic is implemented.

**Why this priority**: Morph is a supported mechanic with existing data model hooks that are unused. Several Commander-popular morph creatures (Kadena, Slinking Giant, Den Protector) rely on the morph/megamorph mechanic. Without implementation, face-down casting and revealing are non-functional.

**Independent Test**: Cast a creature with Morph {2}{G} face-down by paying {3}. Verify it enters the battlefield as a 2/2 colorless, nameless creature. Pay {2}{G} to turn it face up. Verify it becomes the actual creature with its printed characteristics.

**Acceptance Scenarios**:

1. **Given** a card with Morph in hand, **When** the player casts it face down for {3}, **Then** it enters the battlefield as a 2/2 colorless creature with no name, type, or abilities.
2. **Given** a face-down creature on the battlefield, **When** the player pays the morph cost, **Then** the creature turns face up and gains its printed characteristics (this is a special action, not using the stack).
3. **Given** a card with Megamorph, **When** it is turned face up, **Then** it gains its printed characteristics AND receives a +1/+1 counter.
4. **Given** a face-down creature, **When** it would be returned to hand or any non-battlefield zone, **Then** it is revealed to all players.
5. **Given** a face-down creature, **When** legal actions are computed for its controller, **Then** a "turn_face_up" action is available if the player can pay the morph cost.

---

### User Story 18 - Adventure Cards (Priority: P1-HIGH)

Adventure cards (CR 715) have a creature half and an Adventure spell half. The Adventure can be cast from hand; on resolution, the card is exiled (not put in the graveyard). From exile, the creature half can be cast. If the creature half is cast from hand (without the adventure), the adventure is not available. The `Card.faces` field can represent both halves.

**Why this priority**: Adventure cards are among the most powerful and played cards in Standard and Pioneer (Bonecrusher Giant, Brazen Borrower, Murderous Rider). Without adventure support, only the creature half is castable, losing the versatility that makes these cards valuable.

**Independent Test**: Cast the Adventure half of Bonecrusher Giant ("Stomp" — deal 2 damage to any target) from hand. Verify the card is exiled after resolution. Then cast the creature half from exile. Verify it enters the battlefield normally.

**Acceptance Scenarios**:

1. **Given** an adventure card in hand, **When** legal actions are computed, **Then** both the creature cast and the adventure cast are available as separate actions.
2. **Given** a player casts the adventure half from hand, **When** the adventure resolves, **Then** the card is exiled (not put in graveyard).
3. **Given** an adventure card in exile (after adventure resolved), **When** the player casts the creature half from exile, **Then** the creature enters the battlefield normally.
4. **Given** an adventure card in exile (after adventure resolved), **When** it enters the battlefield, **Then** it goes to the graveyard when it dies (not back to exile).
5. **Given** an adventure spell on the stack is countered, **When** it is countered, **Then** the card goes to the graveyard (not exile — exile only happens on successful resolution).

---

### User Story 19 - Persistent Mana Pools (Priority: P1-HIGH)

Some effects cause mana to not empty from a player's mana pool as steps and phases end (CR 106.4a). Examples: Omnath, Locus of Mana ("Green mana doesn't empty from your mana pool as steps and phases end"), Kruphix, God of Horizons ("unused mana becomes colorless"), and Upwelling ("mana pools don't empty as steps and phases end"). The `turn_manager.py` currently empties all mana pools on every step/phase transition with no exception handling.

**Why this priority**: Omnath and Kruphix are popular Commander generals whose entire identity depends on mana persistence. Without this, their signature abilities do nothing and stored mana is lost every step change.

**Independent Test**: Set a flag indicating green mana does not empty for a player. Add 5 green mana to the pool. Advance to the next phase. Verify the green mana remains while other colors empty.

**Acceptance Scenarios**:

1. **Given** a player has "green mana doesn't empty" active, **When** steps and phases end, **Then** green mana in that player's pool is preserved; other colors empty normally.
2. **Given** a player has "mana doesn't empty from your mana pool" active (all colors), **When** steps and phases end, **Then** no mana is removed from the pool.
3. **Given** a player has "unused mana becomes colorless" active, **When** steps and phases end, **Then** all colored mana is converted to colorless mana instead of being emptied.
4. **Given** no mana persistence effects are active, **When** steps and phases end, **Then** mana pools empty normally.
5. **Given** a mana persistence effect is removed mid-turn, **When** the next step transition occurs, **Then** mana empties normally for the affected colors.

---

### User Story 20 - Full Protection Enforcement (Priority: P1-HIGH)

Protection from [quality] (CR 702.16) provides four benefits, remembered by the mnemonic DEBT: (D) all Damage from sources with the quality is prevented, (E) cannot be Enchanted or Equipped by permanents with the quality, (B) cannot be Blocked by creatures with the quality, (C) cannot be Targeted by spells or abilities with the quality. Currently only color-based blocking prevention and damage prevention are partially implemented. Targeting enforcement (see US2), enchanting/equipping restrictions, and non-color protection (protection from creatures, protection from converted mana cost N+) are not enforced.

**Why this priority**: Protection is a core keyword appearing on hundreds of cards. Partial enforcement creates confusing game states where some aspects of protection work and others do not. Full DEBT enforcement is needed for rules correctness.

**Independent Test**: Give a creature protection from white. Verify: (a) a white creature cannot block it, (b) a white spell cannot target it, (c) a white Aura falls off if already attached, and (d) damage from white sources is prevented.

**Acceptance Scenarios**:

1. **Given** a creature has protection from white and a white Aura is attached to it, **When** SBAs are checked, **Then** the Aura is put into its owner's graveyard.
2. **Given** a creature has protection from white and a white Equipment is attached, **When** SBAs are checked, **Then** the Equipment becomes unattached (but stays on the battlefield).
3. **Given** a creature has protection from creatures, **When** a creature's activated ability targets it, **Then** the target is illegal.
4. **Given** a creature has protection from everything, **When** any source would deal damage to it, **Then** the damage is prevented.
5. **Given** a creature gains protection from a color after an Aura of that color is already attached, **When** SBAs are checked, **Then** the Aura falls off.

---

### User Story 21 - Split Second vs Activated Abilities (Priority: P1-HIGH)

Split second (CR 702.61) prevents players from casting spells and activating non-mana abilities while a spell with split second is on the stack. The current implementation in `stack.py` (`_has_split_second()`) blocks new spell casts but does NOT block activated abilities. Mana abilities are exempt from the split second restriction and should remain activatable (see US3).

**Why this priority**: Split second's entire purpose is to prevent responses. If activated abilities still work while split second is on the stack, the mechanic fails at its core function. Cards like Krosan Grip and Sudden Death rely on this restriction.

**Independent Test**: Put a spell with split second on the stack. Attempt to activate a non-mana activated ability. Verify the activation is rejected. Then attempt to activate a mana ability and verify it succeeds.

**Acceptance Scenarios**:

1. **Given** a spell with split second is on the stack, **When** a player attempts to activate a non-mana activated ability, **Then** the activation is rejected.
2. **Given** a spell with split second is on the stack, **When** a player attempts to activate a mana ability, **Then** the activation succeeds (mana abilities are exempt).
3. **Given** a spell with split second is on the stack, **When** a player attempts to cast any spell, **Then** the cast is rejected (existing behavior, confirmed).
4. **Given** a spell with split second is on the stack, **When** triggered abilities trigger, **Then** they are still placed on the stack (triggers are not affected by split second).
5. **Given** the split second spell resolves and leaves the stack, **When** a player attempts to activate abilities, **Then** all abilities are once again legal.

---

### User Story 22 - Type-Changing Layer Effects (Priority: P1-HIGH)

Layer 4 (CR 613.1d) handles type-changing effects. The current `layers.py` implementation only handles additive type changes ("is a [type] in addition to its other types"). Type removal ("loses all land types") and type overwrite ("is a Mountain" without "in addition to") are not supported. Blood Moon is the canonical example: "Nonbasic lands are Mountains" — this removes all existing land subtypes and abilities, replacing them with "Mountain" and the intrinsic "{T}: Add {R}" ability.

**Why this priority**: Blood Moon is a format-defining card in Modern and Legacy. Without type overwrite support, Blood Moon has no functional effect. Similarly, cards like Magus of the Moon, Imprisoned in the Moon, and Spreading Seas are non-functional.

**Independent Test**: Put Blood Moon on the battlefield. Verify that all nonbasic lands lose their printed land types and abilities, become Mountains, and can only tap for {R}.

**Acceptance Scenarios**:

1. **Given** Blood Moon is on the battlefield, **When** continuous effects are applied, **Then** all nonbasic lands have their subtypes replaced with "Mountain" and gain "{T}: Add {R}".
2. **Given** Blood Moon is on the battlefield and a nonbasic land had the ability "{T}: Add {U}", **When** the layer system resolves, **Then** the land loses "{T}: Add {U}" and only has "{T}: Add {R}".
3. **Given** a type-changing effect says "target land is an Island in addition to its other types", **When** applied, **Then** the land gains the Island subtype and "{T}: Add {U}" while keeping its existing types and abilities.
4. **Given** Blood Moon is on the battlefield and then removed, **When** continuous effects re-apply, **Then** nonbasic lands regain their original types and abilities.
5. **Given** multiple type-changing effects apply to the same permanent, **When** the layer system resolves, **Then** they apply in timestamp order within layer 4.

---

### User Story 23 - Snow Mana Tracking (Priority: P2-MEDIUM)

The `{S}` snow mana symbol is parsed in cost strings but `ManaPool` has no `snow` field. Snow mana (CR 107.4h) is mana produced by a snow permanent. A player can only pay `{S}` in a cost with mana produced by snow sources. Without tracking which mana in the pool is snow, `{S}` costs cannot be validated.

**Why this priority**: Snow is a complete mechanic with dedicated sets (Kaldheim, Ice Age, Coldsnap) but is lower priority than the mechanics above because it affects a narrower card pool. It is still needed for Kaldheim Standard and snow Commander decks.

**Independent Test**: Tap a Snow-Covered Forest to add {G} with the snow flag. Attempt to pay a cost containing {S}. Verify the snow-flagged mana satisfies the requirement. Attempt to pay {S} with non-snow mana and verify it fails.

**Acceptance Scenarios**:

1. **Given** a player taps a snow permanent to produce mana, **When** the mana is added to the pool, **Then** it is flagged as snow mana.
2. **Given** a cost contains `{S}`, **When** the player pays with snow-flagged mana, **Then** the cost is satisfied.
3. **Given** a cost contains `{S}`, **When** the player only has non-snow mana, **Then** the payment is rejected.
4. **Given** a player has both snow and non-snow green mana, **When** they pay `{G}{S}`, **Then** the `{S}` must be paid with snow mana specifically.

---

### User Story 24 - Trample Over Planeswalkers (Priority: P2-MEDIUM)

When a creature with trample attacks a planeswalker and is blocked, excess damage beyond lethal to all blockers tramples through to the defending planeswalker (CR 702.19c). If a creature with trample attacks a player and is blocked, excess damage goes to the player. The engine currently handles trample to players but not trample to planeswalkers.

**Why this priority**: Trample over planeswalkers is a niche interaction but affects competitive play in formats where planeswalkers are common attack targets. It is lower priority because the player-trample case (far more common) already works.

**Independent Test**: Attack a planeswalker with a 6/6 trampler. Block with a 2/2. Verify 2 damage is assigned to the blocker and 4 damage tramples through to the planeswalker (removing 4 loyalty).

**Acceptance Scenarios**:

1. **Given** a creature with trample attacks a planeswalker and is blocked by a creature, **When** combat damage is assigned, **Then** excess damage beyond lethal to blockers is dealt to the planeswalker.
2. **Given** a creature with trample attacks a planeswalker and is not blocked, **When** combat damage is dealt, **Then** all damage is dealt to the planeswalker.
3. **Given** a creature with trample attacks a player (not a planeswalker) and is blocked, **When** excess damage exists, **Then** it tramples through to the player (existing behavior, confirmed).
4. **Given** a creature without trample attacks a planeswalker and is blocked, **When** combat damage is assigned, **Then** no damage goes to the planeswalker.

---

### User Story 25 - Flanking (Priority: P3-LOW)

Flanking (CR 702.25) is a triggered ability: "Whenever a creature without flanking blocks this creature, the blocking creature gets -1/-1 until end of turn." Multiple instances of flanking trigger separately. This is relevant for older cards (Benalish Cavalry, Sidar Jabari) and casual/Commander formats.

**Why this priority**: Flanking is a narrow mechanic from a small number of old sets. Very few currently-played cards have flanking. However, it is simple to implement as a blocking trigger.

**Independent Test**: Declare a creature with flanking as an attacker. Block it with a creature without flanking. Verify the blocker gets -1/-1 until end of turn.

**Acceptance Scenarios**:

1. **Given** a creature with flanking is blocked by a creature without flanking, **When** blockers are declared, **Then** a trigger fires giving the blocker -1/-1 until end of turn.
2. **Given** a creature with two instances of flanking is blocked, **When** blockers are declared, **Then** two separate triggers fire, each giving -1/-1.
3. **Given** a creature with flanking is blocked by a creature that also has flanking, **When** blockers are declared, **Then** NO flanking trigger fires (flanking does not trigger against creatures with flanking).
4. **Given** flanking reduces a blocker's toughness to 0, **When** SBAs are checked, **Then** the blocker dies before combat damage.

---

### User Story 26 - Fading (Priority: P3-LOW)

Fading (CR 702.31) causes a permanent to enter with N fade counters. At the beginning of the controller's upkeep, remove a fade counter. If you cannot (because there are none), sacrifice the permanent. Fading is on older cards like Blastoderm and Parallax Wave.

**Why this priority**: Fading is a narrow mechanic from Nemesis block. Very few currently-played cards use it outside of Legacy/Vintage sideboards (Parallax Wave). Simple to implement as an upkeep trigger with counter manipulation.

**Independent Test**: Put a permanent with "Fading 3" on the battlefield with 3 fade counters. On upkeep, verify one fade counter is removed. After 3 upkeeps, verify the permanent is sacrificed when no counters remain.

**Acceptance Scenarios**:

1. **Given** a permanent with Fading enters the battlefield, **When** it enters, **Then** it has N fade counters (N from the fading keyword).
2. **Given** a permanent with fade counters, **When** the controller's upkeep begins, **Then** one fade counter is removed.
3. **Given** a permanent with Fading has 0 fade counters, **When** the controller's upkeep begins, **Then** the permanent is sacrificed.
4. **Given** a permanent with Fading and Proliferate adds a fade counter, **When** upkeep checks occur, **Then** the extra counter extends the permanent's lifetime by one turn.

---

### User Story 27 - Echo (Priority: P3-LOW)

Echo (CR 702.29) is a triggered ability: at the beginning of the upkeep after the permanent enters or after a previous echo trigger, its controller must pay the echo cost or sacrifice it. The echo cost can differ from the mana cost. Echo is on older cards like Avalanche Riders and Crater Hellion.

**Why this priority**: Echo is a narrow mechanic from Urza block and Time Spiral. Few currently-played cards use it. Simple to implement as an upkeep-triggered payment check.

**Independent Test**: Put a creature with "Echo {3}{R}" on the battlefield this turn. On the next upkeep, verify the controller is prompted to pay {3}{R}. If they pay, the creature stays. If they decline, it is sacrificed.

**Acceptance Scenarios**:

1. **Given** a permanent with Echo entered the battlefield this turn, **When** the controller's next upkeep begins, **Then** the controller must pay the echo cost or sacrifice it.
2. **Given** a permanent with Echo and the controller pays the echo cost, **When** the payment is accepted, **Then** the permanent stays and echo does not trigger again.
3. **Given** a permanent with Echo and the controller cannot or chooses not to pay, **When** the echo trigger resolves, **Then** the permanent is sacrificed.
4. **Given** a permanent with Echo that already paid its echo cost, **When** the next upkeep begins, **Then** echo does NOT trigger again.

---

### User Story 28 - P/T Switching (Layer 7d) (Priority: P3-LOW)

Layer 7d (CR 613.4d) handles effects that switch a creature's power and toughness. Cards like About Face, Inside Out, and Doran the Siege Tower apply P/T switching. The `Layer` enum in `layers.py` includes `SWITCH_PT` but the layer is never populated with effects. P/T switching must be applied last in layer 7, after all other P/T modifications.

**Why this priority**: P/T switching is a niche interaction used by a small number of cards. However, Doran the Siege Tower is a popular Commander and the layer is already enumerated — it just needs to be wired up.

**Independent Test**: Apply a P/T switch effect to a 2/5 creature. Verify it becomes 5/2. Then apply a +2/+0 effect (layer 7c) and a P/T switch (layer 7d). The +2/+0 makes it 4/5, then the switch makes it 5/4.

**Acceptance Scenarios**:

1. **Given** a creature is 2/5 and a P/T switch effect is applied, **When** the layer system resolves, **Then** the creature becomes 5/2.
2. **Given** a creature is 2/5, receives +2/+0 in layer 7c, then a P/T switch in layer 7d, **When** the layer system resolves, **Then** the creature is 5/4 (not 7/2).
3. **Given** two P/T switch effects on the same creature, **When** the layer system resolves, **Then** the switches cancel out (switched then switched back = original).
4. **Given** a creature's toughness is raised to avoid death, then a P/T switch is applied, **When** SBAs are checked, **Then** the new toughness (formerly power) is used for the toughness-0 check.

---

### User Story 29 - Foretell Mechanics (Priority: P2-MEDIUM)

Foretell (CR 702.142) allows a player to exile a card from hand face-down by paying {2} on their turn. On a later turn, the card can be cast for its foretell cost (printed on the card). The `foretold` field on Permanent and the `foretold_cards` list on PlayerState already exist but the foretell mechanics (exile action, later cast) are unimplemented.

**Why this priority**: Foretell is a complete mechanic from Kaldheim with several tournament-playable cards (Alrund's Epiphany, Saw It Coming, Behold the Multiverse). The data model hooks exist but no behavior is wired up.

**Independent Test**: On the player's turn, foretell a card from hand by paying {2}. Verify the card is exiled face-down and added to `foretold_cards`. On a later turn, cast the foretold card for its foretell cost. Verify it goes on the stack with the reduced cost.

**Acceptance Scenarios**:

1. **Given** a card with Foretell is in hand during the player's turn, **When** the player pays {2}, **Then** the card is exiled face-down and added to `foretold_cards`.
2. **Given** a foretold card in exile, **When** the player casts it on a later turn, **Then** the foretell cost is used instead of the regular mana cost.
3. **Given** a foretold card in exile, **When** the player casts it on the same turn it was foretold, **Then** the cast is rejected (must wait at least one turn).
4. **Given** it is not the player's turn, **When** the player attempts to foretell, **Then** the action is rejected (foretell is sorcery-speed and only on your turn).
5. **Given** a foretold card is cast from exile, **When** it resolves and would go to the graveyard, **Then** it goes to the graveyard normally (not back to exile).

---

### User Story 30 - Mutate (Priority: P2-MEDIUM)

Mutate (CR 702.139) allows a creature spell to be cast for its mutate cost targeting a non-Human creature the player controls. The mutating creature merges with the target, placed either on top or underneath. The merged permanent has all abilities of all cards in the pile. The top card determines name, power, toughness, type, etc. "Whenever this creature mutates" triggers fire each time a creature is placed on or under the pile. Mutate is from Ikoria.

**Why this priority**: Mutate is a complex mechanic from a single set but produced several Commander-popular cards (Brokkos, Apex of Forever; Snapdax; Vadrok). The `MutateEffect` placeholder exists but is unimplemented. Medium priority due to single-set scope.

**Independent Test**: Cast a creature with Mutate targeting a non-Human creature. Choose to place it on top. Verify the merged permanent has the top card's stats and name, but has abilities from all cards in the pile. Verify "whenever this creature mutates" triggers fire.

**Acceptance Scenarios**:

1. **Given** a creature with Mutate is cast targeting a non-Human creature the player controls, **When** it resolves, **Then** the two merge into a single permanent.
2. **Given** the mutating creature is placed on top, **When** the merge completes, **Then** the permanent's name, power, toughness, and types come from the top card, and it has all abilities from all cards in the pile.
3. **Given** a creature has "Whenever this creature mutates, draw a card", **When** a mutation occurs, **Then** the trigger fires.
4. **Given** a merged creature (pile of 3 cards) dies, **When** it goes to the graveyard, **Then** all cards in the pile go to the graveyard as separate cards.
5. **Given** the player attempts to mutate onto a Human creature, **When** the cast is attempted, **Then** it is rejected (mutate cannot target Humans).

# Feature Specification: Rules Engine Completeness

**Feature Branch**: `014-rules-engine-completeness`
**Created**: 2026-03-23
**Status**: Draft
**Input**: Improve the MTG rules engine to match Forge's implementation across all major systems.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - State-Based Actions Correctness (Priority: P1)

As a game runner, I need the engine to correctly apply all mandatory state-based actions (SBAs) so that games end correctly, permanents are destroyed at the right time, and planeswalkers behave properly.

**Why this priority**: SBAs are the foundation of correct MTG gameplay. Missing SBAs — especially the decking loss condition and planeswalker loyalty-zero destruction — cause games to continue past their correct endpoint or fail to destroy permanents, corrupting all downstream game state.

**Independent Test**: Can be tested with a deck-out scenario (empty library + draw) and a planeswalker taking enough damage to reach 0 loyalty; both should trigger game loss / permanent destruction without additional player input.

**Acceptance Scenarios**:

1. **Given** a player has an empty library and must draw a card, **When** the draw is attempted, **Then** that player immediately loses the game (SBA: draw from empty library).
2. **Given** a planeswalker permanent has 0 or fewer loyalty counters, **When** SBAs are checked, **Then** the planeswalker is put into its owner's graveyard.
3. **Given** a creature has damage marked equal to or greater than its toughness, **When** SBAs are checked, **Then** the creature is destroyed (existing behavior confirmed correct).
4. **Given** a creature has a deathtouch marker from combat damage, **When** SBAs are checked, **Then** the creature is destroyed regardless of toughness.
5. **Given** a player has 10 or more poison counters, **When** SBAs are checked, **Then** that player loses the game.

---

### User Story 2 - Triggered Ability Coverage (Priority: P2)

As a game runner, I need the engine to fire triggered abilities for common game events — specifically damage-based triggers ("whenever a creature deals damage") and end-of-step triggers ("at the beginning of your end step") — so that cards with these abilities function correctly.

**Why this priority**: A large fraction of MTG cards use these trigger patterns. Without them, staple cards like Blood Artist, Ajani's Pridemate, and any "at the beginning of your end step" card silently do nothing, making gameplay fundamentally incorrect.

**Independent Test**: Can be tested with a creature that has a "whenever this deals damage" triggered ability; dealing combat damage should enqueue the trigger and resolve it correctly on the stack.

**Acceptance Scenarios**:

1. **Given** a creature with "whenever this creature deals combat damage to a player", **When** combat damage is dealt, **Then** a trigger is enqueued on the pending triggers list for that ability.
2. **Given** a permanent with "at the beginning of your end step", **When** the end step begins, **Then** its trigger is enqueued for that controller.
3. **Given** a permanent with "at the beginning of your upkeep", **When** the upkeep step begins, **Then** its trigger is enqueued for that controller.
4. **Given** multiple triggered abilities from a single event, **When** triggers are placed on the stack, **Then** the active player's triggers are placed first, then the non-active player's (APNAP order, CR 603.3).

---

### User Story 3 - Mana Cost Enforcement (Priority: P3)

As a game runner, I need the engine to correctly validate hybrid mana costs and Phyrexian mana costs so that cards with these cost types can only be cast when the player can legally pay for them.

**Why this priority**: Hybrid and Phyrexian mana are common in modern sets. Without enforcement, the AI and human players can cast cards for free or with wrong mana, making the mana system meaningless for a large portion of the card pool.

**Independent Test**: Can be tested by attempting to cast a hybrid card ({G/W}) with only generic mana available — the cast should be rejected. Phyrexian mana ({G/P}) should be payable with 2 life as an alternative.

**Acceptance Scenarios**:

1. **Given** a card with hybrid cost {G/W}, **When** cast with neither green nor white mana, **Then** the cast is rejected as illegal.
2. **Given** a card with hybrid cost {G/W}, **When** cast with one green mana, **Then** the cast is accepted (green satisfies the hybrid pip).
3. **Given** a card with Phyrexian cost {G/P}, **When** a player pays 2 life instead of one green mana, **Then** the cast is accepted and the player loses 2 life.
4. **Given** a card with Phyrexian cost {G/P}, **When** a player has insufficient green mana and fewer than 2 life, **Then** the cast is rejected.

---

### User Story 4 - Damage Prevention Replacement Effects (Priority: P4)

As a game runner, I need the engine to apply damage prevention replacement effects (shields, protection, "prevent the next N damage") so that cards like Fog, damage prevention shields, and protection abilities function correctly.

**Why this priority**: Prevention effects are a major category of MTG interaction. Protection from color and "prevent all combat damage" effects (Fog) directly affect combat outcomes, and without them the engine produces wrong life total results.

**Independent Test**: Can be tested by having a creature with "protection from red" be targeted by a red spell that deals damage; the damage should be prevented and the creature should survive.

**Acceptance Scenarios**:

1. **Given** a permanent has accumulated damage prevention (N remaining), **When** damage is dealt to it, **Then** up to N damage is prevented and the counter is reduced accordingly.
2. **Given** a creature has protection from a color, **When** a spell of that color targets or deals damage to it, **Then** the damage is prevented and the targeting is illegal.
3. **Given** a "prevent all combat damage this turn" effect (e.g. Fog) is active, **When** combat damage would be dealt, **Then** all combat damage is prevented.
4. **Given** damage would be prevented by a replacement effect, **When** the prevention applies, **Then** the source does not gain lifelink life for prevented damage.

---

### User Story 5 - Full Layer System (Priority: P5)

As a game runner, I need the layer system to cover all 7 CR-613 layers — copy, control, text-changing, type, color, ability-adding/removing, and power/toughness — so that continuous effects interact correctly when multiple effects apply to the same permanent.

**Why this priority**: The existing layer system handles some P/T modifications but misses copy effects, control-changing effects, and ability-granting/removing effects. These are required to correctly handle cards like Mutavault, Control Magic, and Humility.

**Independent Test**: Can be tested by applying a control-changing effect (layer 2) and a P/T modification (layer 7) to the same creature; the effective controller and stats should reflect both effects applied in layer order.

**Acceptance Scenarios**:

1. **Given** a copy effect is applied to a permanent (layer 1), **When** the permanent's characteristics are computed, **Then** it has the copiable values of the source object, with other effects applied on top.
2. **Given** a control-changing effect applies (layer 2), **When** the permanent's controller is evaluated, **Then** the most recently applied control effect determines the controller (CR 613.7).
3. **Given** an effect adds an ability to a creature (layer 6), **When** the creature's abilities are evaluated, **Then** the granted ability is present and functional.
4. **Given** an effect removes an ability from a creature (e.g. Humility), **When** the creature's abilities are evaluated, **Then** the removed ability is absent.
5. **Given** multiple P/T-setting effects in layer 7b, **When** evaluated, **Then** the most recently applied setting effect wins (timestamp order, CR 613.7).

---

### User Story 6 - Attack and Block Constraints (Priority: P6)

As a game runner, I need the engine to enforce advanced attack and block constraints — including mandatory attack requirements, goad, Propaganda-style attack costs, and cannot-block restrictions — so that cards that modify combat participation work correctly.

**Why this priority**: Many common cards (Propaganda, Ghostly Prison, goad effects) change who must or can attack/block. Without enforcement, these cards have no effect and combat is incorrect for a significant portion of enchantment and control strategies.

**Independent Test**: Can be tested by applying a "must attack if able" effect to a creature and then checking that the engine correctly requires it to be declared as an attacker (or forces a pass if it cannot).

**Acceptance Scenarios**:

1. **Given** a permanent has an attack cost effect (Propaganda-style), **When** a creature is declared as an attacker**, **Then** the controller must pay the cost or the attack declaration is rejected.
2. **Given** a creature is goaded, **When** the declare attackers step arrives, **Then** the creature must attack a player other than the goad source's controller if able.
3. **Given** a creature has "must attack each combat if able", **When** the declare attackers step arrives and the creature is able to attack, **Then** failing to declare it as an attacker is an illegal action.
4. **Given** a creature has "can't block", **When** the declare blockers step arrives, **Then** that creature cannot be chosen as a blocker.
5. **Given** a creature has "can't be blocked by creatures with power 2 or less", **When** a blocker with power 1 attempts to block it, **Then** the block declaration is rejected.

---

### User Story 7 - Copy Effects on the Stack (Priority: P7)

As a game runner, I need the engine to correctly handle copy effects on the stack (e.g. Fork, Twincast, Isochron Scepter imprint) so that spells can be copied and resolved as separate instances with independently chosen targets.

**Why this priority**: Copy effects are a fundamental part of spellslinger decks and combo play. Without them, any card that copies spells silently does nothing or causes errors.

**Independent Test**: Can be tested by casting a burn spell and then applying a copy effect; the stack should contain two instances of the spell, each resolvable independently with optionally different targets.

**Acceptance Scenarios**:

1. **Given** a spell is on the stack and a copy effect is applied, **When** the copy is created, **Then** a new StackObject with `is_copy=True` is added to the stack with the same effects.
2. **Given** a copied spell is on the stack, **When** new targets are chosen for the copy, **Then** the copy resolves with the chosen targets, not the original's targets.
3. **Given** a copied spell resolves, **When** it is put into a graveyard, **Then** the copy ceases to exist (copies of spells don't go to graveyard, CR 706.10).
4. **Given** a phase-skipping effect is active, **When** the affected phase would normally begin, **Then** that phase and all its steps are skipped entirely.

---

### Edge Cases

- What happens when both SBA conditions apply simultaneously (e.g., 0 loyalty AND another SBA)? All applicable SBAs are applied simultaneously before any player gets priority.
- How does the engine handle a hybrid mana cost where both options are colored (e.g., {B/G})? Either color satisfies the pip; generic mana does not.
- What if damage prevention reduces damage to exactly 0? The damage event still occurs but deals 0 damage (no lifelink triggers from 0 damage).
- What happens when a goaded creature has no legal attack target other than the goad source's controller? It may attack any player or not attack.
- What if a copy effect targets a modal spell? The copy may choose new modes independently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The engine MUST detect when a player attempts to draw from an empty library and immediately apply a game-loss SBA for that player.
- **FR-002**: The engine MUST destroy planeswalker permanents with 0 or fewer loyalty counters during SBA checks.
- **FR-003**: The engine MUST fire "whenever this deals damage" triggered ability events after combat damage assignment.
- **FR-004**: The engine MUST fire "at the beginning of [step]" triggered ability events at the start of the matching step, for all permanents with such abilities.
- **FR-005**: The engine MUST validate hybrid mana pips ({A/B}) by accepting payment from either color but rejecting generic-only payment.
- **FR-006**: The engine MUST validate Phyrexian mana pips ({C/P}) by accepting either the colored mana or 2 life as payment.
- **FR-007**: The engine MUST apply damage prevention replacement effects before damage is marked, reducing or eliminating marked damage accordingly.
- **FR-008**: The layer system MUST apply all 7 CR-613 layers in order: copy (1), control (2), text (3), type (4), color (5), ability (6), P/T (7).
- **FR-009**: Layer 6 MUST support ability-granting and ability-removing effects, updating a permanent's effective keyword and activated/triggered ability list.
- **FR-010**: The engine MUST enforce "must attack" and "cannot block" constraints during the declare attackers and declare blockers steps respectively.
- **FR-011**: The engine MUST enforce Propaganda-style attack costs; a creature that would require an unpayable cost cannot legally be declared as an attacker.
- **FR-012**: The engine MUST support creating copies of spells on the stack as new StackObjects with `is_copy=True`, with independently assignable targets.

### Key Entities

- **PreventionEffect**: Represents an active damage prevention shield — source permanent, remaining prevention amount, targeting scope (specific permanent, all combat, etc.)
- **ContinuousEffect**: Represents a layer-system effect — source, affected permanent(s), layer, sub-layer, timestamp, effect type and parameters.
- **AttackConstraint**: Represents a constraint on attacking — type (must-attack, cannot-attack, cost-to-attack), affected creature or player, optional cost.
- **BlockConstraint**: Represents a constraint on blocking — type (cannot-block, can-only-block-X, requires-N-blockers), affected creature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A game where a player decks out ends with that player losing within the same turn the last draw occurs, with no manual intervention required.
- **SC-002**: Planeswalkers correctly die at 0 loyalty in 100% of test scenarios involving combat damage and burn spells targeting them.
- **SC-003**: Cards with "whenever this deals damage" triggers produce the correct number of trigger events in all tested combat scenarios.
- **SC-004**: Hybrid mana validation correctly accepts and rejects casting attempts in 100% of test cases covering all hybrid pip combinations.
- **SC-005**: Combat outcomes are correct in test scenarios involving Fog (damage prevention), protection from color, and partial prevention shields.
- **SC-006**: A permanent affected by both a control-change effect and a P/T effect reflects both in the correct layer order in all test scenarios.
- **SC-007**: Propaganda-style effects correctly block illegal attack declarations; creature attacks requiring an unpayable cost are never accepted.
- **SC-008**: A copied spell on the stack resolves independently of the original and does not appear in any graveyard afterward.
- **SC-009**: The existing rules engine test suite continues to pass at 100% after all changes (no regressions).
- **SC-010**: A full game between two AI players using a representative card pool completes without errors or stuck states in all tested scenarios.

## Assumptions

- The existing SBA check infrastructure (currently handling creature death by damage) will be extended rather than replaced.
- Trigger detection will be implemented as a scanning pass over all permanents' oracle text at the start of each step and after damage, using pattern matching consistent with the existing ability parser.
- Hybrid and Phyrexian mana parsing will extend the existing mana cost parser; no changes to the Card or ManaPool model shapes are assumed to be needed.
- Damage prevention effects will be stored as a list on GameState; applying them is a pre-damage hook.
- The layer system expansion will be backward-compatible with existing P/T modification logic.
- Phase-skipping (Story 7) is bundled with copy effects as both are stack/spell interaction features.
- Goad is a keyword action that may be tracked as a counter or flag on `Permanent`.

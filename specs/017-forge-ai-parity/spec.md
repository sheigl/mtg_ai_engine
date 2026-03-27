# Feature Specification: Forge AI Parity

**Feature Branch**: `017-forge-ai-parity`
**Created**: 2026-03-25
**Status**: Draft
**Input**: User description: "AI decision-making parity with Forge MTG engine — implement all 20 AI capabilities that Forge has but our engine lacks"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI Target Selection (Priority: P1)

When the AI casts removal, burn, or any targeted spell, it selects the best target from available options — not a random or auto-selected target. The choice reflects board context: removing the biggest threat, burning face for lethal, targeting the creature with the highest CMC.

**Why this priority**: Without target selection the AI frequently wastes removal on wrong targets or fails to take lethal burn shots. This is the most impactful single correctness gap vs Forge and affects every game.

**Independent Test**: Set up a board where opponent has a 1/1 and a 6/6; AI has a destroy-target-creature spell. Verify AI targets the 6/6.

**Acceptance Scenarios**:

1. **Given** an AI with a destroy-target-creature spell and an opponent board of a 2/2 and a 5/5, **When** the AI casts the spell, **Then** it targets the 5/5 (highest CMC threat).
2. **Given** an AI with a 3-damage burn spell and an opponent at exactly 3 life, **When** the AI takes priority, **Then** it targets the opponent player for lethal rather than any creature.
3. **Given** an AI with an Aura spell, **When** casting it, **Then** it attaches to its own highest-power creature.

---

### User Story 2 - AI Combat Decisions With Tricks (Priority: P1)

An AI holding an instant-speed pump spell or combat trick waits until the declare-blockers step to cast it — winning a trade it would have otherwise lost — rather than casting it as a sorcery in main phase.

**Why this priority**: Combat is the most frequent AI decision point. Correct instant-speed combat tricks are the difference between a competent and an exploitable AI.

**Independent Test**: Give AI a +3/+3 instant and a 2/2 creature attacking into a 4/4 blocker. Verify the AI casts the pump at declare-blockers timing to win the trade.

**Acceptance Scenarios**:

1. **Given** an AI attacking with a 2/2 and holding a +3/+3 instant, **When** the opponent declares a 4/4 blocker, **Then** the AI casts the pump to survive and kill the blocker.
2. **Given** an AI with no attackers in combat, **When** it has a pump instant in hand, **Then** it does not cast the pump as a sorcery in main phase (waits for combat relevance).
3. **Given** an AI holding a counterspell with open mana and no sorcery-speed plays scoring above threshold, **When** it takes its main phase, **Then** it passes priority to preserve mana for the opponent's turn.

---

### User Story 3 - Card Draw and Ramp Scoring (Priority: P2)

The heuristic player gives meaningful scores to card draw spells and mana ramp spells/dorks rather than treating them as near-zero value, so the AI prioritizes them at the correct points in the game.

**Why this priority**: Draw and ramp are foundational to every MTG strategy. An AI that doesn't value them loses by playing threats while ignoring the engine that enables threats.

**Independent Test**: Deck with only lands, Rampant Growth, and a large creature. Verify AI casts ramp turn 2 rather than passing.

**Acceptance Scenarios**:

1. **Given** an AI with a draw-two spell available and mana to cast it, **When** evaluating main-phase actions, **Then** the draw spell scores above passing priority.
2. **Given** an AI with a mana dork (Elvish Mystic) and a 5-drop in hand, **When** on turn 2, **Then** it casts the mana dork over passing.
3. **Given** an AI with a land-fetch ramp spell on turn 3 and a 3/3 creature as alternative, **When** it has a 5-drop in hand, **Then** it prefers the ramp spell.

---

### User Story 4 - Planeswalker Loyalty Ability Activation (Priority: P2)

When the AI controls a planeswalker, it activates a loyalty ability each turn — selecting the ability that best serves the board state rather than ignoring the planeswalker.

**Why this priority**: Planeswalkers are among the most powerful card types. An AI that ignores them on board is severely disadvantaged in any planeswalker game.

**Independent Test**: Give AI a planeswalker with a + ability and an empty hand. Verify AI activates the + ability each turn without crashing.

**Acceptance Scenarios**:

1. **Given** an AI controlling a planeswalker at base loyalty, **When** it takes its main phase with no higher-value plays, **Then** it activates the + loyalty ability.
2. **Given** an AI controlling a planeswalker with a − ability that removes a creature threat, **When** the opponent has a threatening attacker, **Then** the AI evaluates spending loyalty to remove the threat.
3. **Given** an AI planeswalker at sufficient loyalty for its ultimate, **When** the ultimate would win or drastically swing the game, **Then** the AI activates it.
4. **Given** an AI planeswalker with only a − ability available, **When** activating it would reduce loyalty to 0 or below, **Then** the AI does not activate it (avoids self-destruction unless game-winning).

---

### User Story 5 - Board Wipe Evaluation (Priority: P2)

The AI evaluates whether a mass-destruction spell is a net positive before casting it — comparing the CMC value of permanents destroyed on each side — and only casts it when the net result favors the AI.

**Why this priority**: Board wipes are high-impact but two-sided. An AI that casts Wrath when it has more creatures than the opponent is actively self-defeating.

**Independent Test**: AI has 3 creatures, opponent has 1. Verify AI does NOT cast Wrath of God. Add 3 more opponent creatures. Verify AI DOES cast it.

**Acceptance Scenarios**:

1. **Given** an AI with a board wipe and more friendly permanent CMC than opponent permanent CMC, **When** evaluating actions, **Then** the board wipe scores negative (not cast).
2. **Given** an AI with a board wipe and the opponent having 3× more creature CMC, **When** evaluating actions, **Then** the board wipe scores positive and is cast.
3. **Given** an AI with indestructible creatures and a Wrath effect, **When** the opponent has destroyable creatures, **Then** the AI correctly includes its indestructible creatures as "surviving" the wipe.

---

### User Story 6 - Mulligan Hand Evaluation (Priority: P2)

Before a game starts, the AI evaluates its opening hand and mulligans unplayable hands (flood or screw), accepts reasonable hands, and does not infinite-mulligan.

**Why this priority**: A bad opening hand dramatically reduces the AI's ability to play any real game. Mulligan decisions determine whether the deck strategy can execute at all.

**Independent Test**: Give AI a 7-land hand — verify mulligan. Give AI 2 lands + 5 on-curve spells — verify keep.

**Acceptance Scenarios**:

1. **Given** an AI opening hand with 0 lands, **When** mulligan decision is evaluated, **Then** the AI mulligans.
2. **Given** an AI opening hand with 7 lands, **When** mulligan decision is evaluated, **Then** the AI mulligans.
3. **Given** an AI opening hand with 2–4 lands and at least 2 spells castable in the first 3 turns, **When** mulligan decision is evaluated, **Then** the AI keeps.
4. **Given** an AI that has already mulliganed to 5 cards with at least 2 lands, **When** mulligan decision is evaluated, **Then** the AI keeps (no infinite mulligan below 5).

---

### User Story 7 - Sacrifice Target Selection (Priority: P3)

When a spell or ability requires the AI to sacrifice a permanent, it chooses the lowest-value target (preferring tokens, then lowest CMC) rather than failing or choosing randomly.

**Why this priority**: Sacrifice effects appear on many powerful cards. Without handling them those cards are unplayable or crash the game loop.

**Independent Test**: AI has a sacrifice-a-creature cost spell, owns a 1/1 and a 5/5. Verify it sacrifices the 1/1.

**Acceptance Scenarios**:

1. **Given** an AI casting a spell requiring sacrifice of a creature and holding a 1/1 and a 5/5, **When** the cost is paid, **Then** it sacrifices the 1/1.
2. **Given** a sacrifice-any-permanent cost with lands and creatures available, **When** the AI pays the cost, **Then** it sacrifices a land or token before a key threat.
3. **Given** an AI with no valid sacrifice targets, **When** a sacrifice cost is required, **Then** the action is not offered as legal.

---

### User Story 8 - Scry and Surveil Decisions (Priority: P3)

When the AI performs a Scry or Surveil effect, it makes an informed decision about which cards to keep on top of the library vs. send to the bottom or graveyard, based on castability and graveyard synergy.

**Why this priority**: Scry/Surveil on cantrips and cheap spells appear constantly. Random or wrong decisions compound over a game.

**Acceptance Scenarios**:

1. **Given** an AI Scrys 1 and the revealed card's CMC is castable within the next 2 turns, **When** making the keep/bottom decision, **Then** the AI keeps it on top.
2. **Given** an AI Scrys 1 and the revealed card is a 7-drop on turn 2, **When** making the keep/bottom decision, **Then** the AI bottoms it.
3. **Given** an AI Surveils 1 and the revealed card has flashback, **When** making the keep/graveyard decision, **Then** the AI sends it to the graveyard to enable future flashback.

---

### User Story 9 - Modal Spell Mode Selection (Priority: P3)

When the AI casts a modal spell, it selects the mode(s) that best match the current board state, not always the first mode or a random mode.

**Why this priority**: Modal spells are flexibility tools. An AI that always picks mode 1 wastes the card's potential in most board states.

**Acceptance Scenarios**:

1. **Given** an AI with a choose-one spell with a removal mode and a draw mode and an opponent creature on board, **When** the AI evaluates modes, **Then** it selects the removal mode.
2. **Given** the same spell with no opponent creatures present, **When** the AI evaluates modes, **Then** it selects the draw mode.
3. **Given** a choose-two spell, **When** the AI evaluates, **Then** it picks the two highest-scoring modes independently.

---

### User Story 10 - Equipment Attachment (Priority: P3)

When the AI controls equipment and has creatures, it activates the equip ability each turn to attach the equipment to its best creature, maximizing the equipment's offensive bonus.

**Acceptance Scenarios**:

1. **Given** an AI with equipment and two creatures (a 1/1 and a 4/4), **When** the AI takes its main phase with mana available, **Then** it equips the 4/4.
2. **Given** equipment already attached to a creature that has died, **When** the AI re-evaluates, **Then** it re-equips to the next best surviving creature.

---

### User Story 11 - Graveyard Zone Casting (Priority: P3)

The AI generates and evaluates legal actions for cards in its graveyard that have alternative casting mechanics (flashback, escape, unearth, disturb), treating them as additional resource options.

**Acceptance Scenarios**:

1. **Given** an AI with a flashback spell in its graveyard and mana to pay the flashback cost, **When** evaluating legal actions, **Then** the flashback cast is offered and scored.
2. **Given** an AI with an escape card and enough cards in its graveyard, **When** evaluating actions, **Then** the escape cast is offered and the graveyard cost is accounted for.

---

### User Story 12 - ETB and Dies Trigger Evaluation (Priority: P3)

The heuristic player adds bonus score to creatures based on their enters-the-battlefield or dies trigger effects, so creatures with strong ETBs score higher than vanilla creatures of the same CMC.

**Acceptance Scenarios**:

1. **Given** a 2/2 with "draw a card when it enters" and a 2/2 vanilla, **When** the AI scores casting each, **Then** the ETB creature scores at least 15 points higher.
2. **Given** a creature with "when this dies, create a 1/1 token," **When** the AI scores it, **Then** it receives a bonus for trade-willingness.

---

### User Story 13 - Cross-Turn Memory (Priority: P3)

The AI maintains memory across turns of revealed opponent cards and key game events, using that information to influence decisions (e.g., not casting a valuable spell into known countermagic).

**Acceptance Scenarios**:

1. **Given** the opponent reveals a counterspell from their hand, **When** the AI has open mana available to the opponent, **Then** the AI deprioritizes casting its highest-value spell into that window.
2. **Given** a permanent was bounced this turn, **When** the AI evaluates recasting it, **Then** it doesn't count the bounced permanent as "still in play" for board evaluation.

---

### User Story 14 - Lookahead Simulation (Priority: P3)

The AI simulates 1–2 turns ahead when evaluating high-impact action sequences (ramp into a threat, save removal for next turn's threat) rather than pure single-action greedy evaluation.

**Acceptance Scenarios**:

1. **Given** an AI that can cast ramp this turn and a 5-drop next turn, **When** scoring the ramp action, **Then** the lookahead simulation adds a bonus for enabling the 5-drop one turn earlier.
2. **Given** a lookahead simulation that would loop indefinitely, **When** the depth limit of 2 turns is reached, **Then** the simulation terminates and returns the partial result.

---

### User Story 15 - Control Gain and Life Gain Scoring (Priority: P3)

The AI correctly scores spells that steal opponent permanents or gain life, giving them meaningful heuristic values based on what is stolen and how urgent life gain is.

**Acceptance Scenarios**:

1. **Given** an AI with a control-stealing spell and an opponent 5/5 on board, **When** the AI scores the spell, **Then** it scores at least CMC × 15 (stealing a 5-drop = 75+ points).
2. **Given** an AI at 4 life with a life-gain spell available, **When** the AI evaluates actions, **Then** the life gain spell receives a 2× bonus multiplier due to low life threshold.

---

### User Story 16 - Holistic Board Position Evaluation (Priority: P3)

The heuristic player computes a board position score before and after each candidate action, using the delta to rank actions rather than scoring each action in isolation.

**Acceptance Scenarios**:

1. **Given** two actions with identical CMC but one improves the AI's board position delta more, **When** the AI ranks them, **Then** it selects the action with the higher board-position delta.
2. **Given** an AI with a large hand and high life total, **When** computing board position, **Then** hand size and life are both included in the score (not just permanents).

---

### User Story 17 - AI Personality and Difficulty Profiles (Priority: P3)

The AI's behavior is governed by a configurable personality profile that controls aggression, risk tolerance, counter thresholds, trade willingness, and other strategic tendencies. Different profiles produce observably different play styles without changing core rules correctness.

**Why this priority**: A single fixed AI is predictable and exploitable. Personality profiles allow difficulty tuning, varied AI opponents, and deck-archetype-aware behavior without code changes.

**Acceptance Scenarios**:

1. **Given** an AI with an aggressive profile, **When** evaluating attacks, **Then** it accepts trades it would decline under a conservative profile (higher CHANCE_TO_ATTACK_INTO_TRADE value).
2. **Given** an AI with a counter-heavy profile (ALWAYS_COUNTER_REMOVAL_SPELLS = true), **When** the opponent casts a removal spell, **Then** the AI counters it even if CMC < default threshold.
3. **Given** an AI with a conservative profile and open mana, **When** the opponent casts a CMC 1 cantrip, **Then** the AI does not counter it (CHANCE_TO_COUNTER_CMC_1 = 0%).
4. **Given** two AI players with different profiles playing the same deck, **When** observed over 10 games, **Then** their attack frequency and counter rates differ measurably.

---

### User Story 18 - Alternative Casting Costs (Priority: P3)

The AI recognizes and utilizes alternative casting cost mechanics — Convoke (tap creatures to reduce cost), Delve (exile graveyard cards to reduce cost), and Emerge (sacrifice a creature to reduce cost) — enabling it to cast cards it would otherwise be unable to afford.

**Why this priority**: Convoke, Delve, and Emerge appear on many high-impact cards. An AI that cannot use these mechanics effectively cannot play a large class of cards in its deck.

**Acceptance Scenarios**:

1. **Given** an AI with a Convoke spell and multiple untapped creatures but insufficient mana to cast normally, **When** evaluating legal actions, **Then** the Convoke cast is offered and the AI taps creatures to pay part of the cost.
2. **Given** an AI with a Delve spell and cards in its graveyard, **When** evaluating legal actions, **Then** the Delve cast is offered and the AI exiles graveyard cards to reduce the generic mana cost.
3. **Given** an AI with an Emerge spell and a sacrifice target, **When** the sacrificed creature's CMC reduces the Emerge cost to affordable, **Then** the AI evaluates sacrificing to enable the cast and scores it against keeping the sacrificed creature.

---

### User Story 19 - Token Generation Spell Scoring (Priority: P3)

Spells that create creature tokens (without being creatures themselves) receive meaningful heuristic scores based on the number, power/toughness, and keywords of the tokens created. The AI does not treat token producers as near-zero value.

**Why this priority**: Token producers are a major spell category. Treating them as zero value causes the AI to never cast them, wasting a core deck strategy.

**Acceptance Scenarios**:

1. **Given** a spell that creates two 2/2 tokens, **When** the AI scores it, **Then** it scores comparable to casting two 2/2 creatures.
2. **Given** a spell that creates a single 1/1 flier token, **When** the AI scores it, **Then** the flying keyword on the token contributes to the score.
3. **Given** an AI with a token producer and a same-CMC vanilla creature, **When** the token producer creates more total power/toughness, **Then** the token producer scores higher.

---

### User Story 20 - Multiplayer Attack Direction (Priority: P3)

In games with more than two players, the AI evaluates which opponent to attack each combat — targeting the opponent most likely to receive unblocked damage, the most threatening opponent on board, or the opponent closest to elimination — rather than always attacking the same player.

**Why this priority**: Commander and other multiplayer formats involve 3–4 players. Attacking the wrong opponent wastes damage and ignores the biggest threat.

**Acceptance Scenarios**:

1. **Given** an AI in a 4-player game where one opponent is at 3 life, **When** the AI has an unblocked attacker, **Then** it attacks the low-life opponent to eliminate them.
2. **Given** an AI in a 4-player game where all opponents are at full health but one has a dominant board, **When** the AI evaluates attack direction, **Then** it targets the opponent with the highest permanent CMC total (biggest threat).
3. **Given** an AI with flying attackers in a multiplayer game, **When** multiple opponents have no flying blockers, **Then** the AI attacks the opponent with the least blockers available for the most guaranteed damage.

---

### User Story 21 - Transform and Meld Card Evaluation (Priority: P3)

The AI evaluates double-faced cards (DFCs) and meld cards by their transformed or melded face — not just their front face — so that the value of transformation is factored into whether to cast and how to protect the card.

**Why this priority**: DFCs are common in modern Magic. An AI that values a Werewolf only by its front face misses that it transforms into a much larger creature under the right conditions.

**Acceptance Scenarios**:

1. **Given** a DFC creature whose back face is significantly more powerful, **When** the AI scores casting it, **Then** the score includes a bonus representing the transform potential.
2. **Given** a meld pair where both halves are in the AI's hand/board and the meld is achievable, **When** evaluating board actions, **Then** the AI accounts for the meld bonus when protecting both pieces.
3. **Given** a DFC with a condition for transforming (e.g., no spells cast this turn), **When** the AI evaluates its turn, **Then** it considers whether passing on spell-casting enables the transform.

---

### User Story 22 - Fog and Defensive Spell Recognition (Priority: P3)

The AI recognizes Fog-effect spells (prevent all combat damage this turn) and evaluates them defensively — holding them for the opponent's attack step when the AI would otherwise take lethal or severe damage — rather than wasting them in its own main phase.

**Why this priority**: Fog effects are tempo-neutral if cast at the wrong time. An AI that casts Fog proactively wastes a card; one that holds it correctly survives a lethal attack.

**Acceptance Scenarios**:

1. **Given** an AI holding a Fog effect and the opponent attacking with lethal damage, **When** the opponent's attack step begins, **Then** the AI casts the Fog to prevent the damage.
2. **Given** an AI holding a Fog effect but taking non-lethal damage, **When** the AI evaluates whether to Fog, **Then** it holds the spell (non-lethal damage does not trigger Fog use).
3. **Given** an AI with a Fog held from a prior turn and sufficient mana, **When** the opponent has no attackers, **Then** the AI does not cast the Fog wastefully.

---

### User Story 23 - Artifact and Enchantment Removal Prioritization (Priority: P3)

The AI actively evaluates and prioritizes using artifact and enchantment removal when the opponent controls threatening non-creature permanents (equipment, enchantments that grant repeated advantage, mana artifacts), rather than ignoring them.

**Why this priority**: Artifacts and enchantments that generate ongoing value compound over time. An AI that ignores them loses to slow, grinding permanent-based strategies.

**Acceptance Scenarios**:

1. **Given** the opponent controls a mana-producing artifact and the AI has a destroy-artifact spell, **When** evaluating actions, **Then** the removal scores positively (artifact CMC × 10) and is cast.
2. **Given** the opponent controls an equipment attached to their best creature, **When** the AI has artifact destruction, **Then** the AI scores destroying it at least as high as removing the creature it's attached to.
3. **Given** the opponent controls an enchantment that draws cards each turn, **When** the AI has enchantment removal, **Then** the removal scores with urgency proportional to how many turns the enchantment has been active.

---

### User Story 24 - Next-Turn Attack Prediction (Priority: P3)

The AI predicts what the opponent will be able to attack with on the next turn — accounting for untapping, summoning sickness wearing off, and known hand contents — and uses this prediction to inform blocking, developing, and removal decisions this turn.

**Why this priority**: Forge's AiAttackController explicitly calculates next-turn attack potential. An AI that doesn't predict incoming attacks overextends into bad blocks and misses defensive development opportunities.

**Acceptance Scenarios**:

1. **Given** the opponent has three creatures that will untap next turn and the AI is at 9 life, **When** the AI evaluates developing vs. holding up blockers this turn, **Then** it accounts for the incoming 9+ damage and prioritizes a blocker or removal.
2. **Given** the opponent has a creature with haste just entered the battlefield, **When** the AI evaluates the incoming attack threat for this turn, **Then** it correctly includes the haste creature (no summoning sickness) in the threat calculation.
3. **Given** the AI knows from revealed hand information that the opponent holds a pump spell, **When** predicting opponent attack damage, **Then** the AI adds the pump's power bonus to the predicted incoming damage.

---

### User Story 25 - Animate Land and Artifact Scoring (Priority: P3)

The AI evaluates spells and abilities that animate lands or artifacts into creatures (e.g., Nissa, Who Shakes the World; Ensoul Artifact), scoring them based on the power/toughness and keywords of the resulting animated creature.

**Why this priority**: Forge's AnimateAi (27KB) handles this class of effects. Animate effects are powerful tempo plays that the AI otherwise scores as zero or ignores.

**Acceptance Scenarios**:

1. **Given** an AI with an effect that animates a land into a 3/3, **When** scoring the animate action, **Then** it scores at least as high as casting a 3/3 creature with no keywords.
2. **Given** an AI with an effect that animates an artifact into a creature with flying, **When** scoring the animate action, **Then** the flying keyword contributes a bonus as it would for a cast creature.
3. **Given** an AI that has already animated a permanent this turn, **When** re-evaluating animate actions, **Then** ANIMATED_THIS_TURN memory prevents double-scoring the same permanent.

---

### User Story 26 - Library Search and Tutor Scoring (Priority: P3)

The AI evaluates spells that search the library for a card (tutors), scoring them based on the best card they can find given the current game state — not treating them as zero-value utility spells.

**Why this priority**: Forge's DigAi handles library search. Tutors are among the most powerful spells in Magic; an AI that scores them at zero will never cast them, losing a critical resource.

**Acceptance Scenarios**:

1. **Given** an AI with a tutor that finds any creature and a 6-drop bomb creature in its deck, **When** scoring the tutor, **Then** it scores based on the value of the best card it can find (not zero).
2. **Given** an AI with a tutor and a dominant board position, **When** evaluating the tutor, **Then** it fetches the card that best advances its winning line (a finisher, not a land when it has enough mana).
3. **Given** an AI at low life with a tutor that can find removal, **When** evaluating the tutor, **Then** it fetches removal or a blocker rather than an offensive card.

---

### User Story 27 - Fight Mechanic Scoring (Priority: P3)

The AI evaluates fight effects (each creature deals damage equal to its power to the other) as a form of targeted removal, selecting the best pairing of friendly fighter vs. opponent target to maximize the net board outcome.

**Why this priority**: Forge's FightAi handles fight mechanics. Fight is a common removal tool in green; treating it as zero causes the AI to never use it despite it often being excellent removal.

**Acceptance Scenarios**:

1. **Given** an AI with a fight spell and a 5/5 friendly creature vs. an opponent's 3/3, **When** scoring the fight, **Then** it scores positively (kills opponent creature while friendly survives).
2. **Given** an AI with a fight spell and only a 1/1 friendly creature vs. a 5/5 opponent, **When** scoring the fight, **Then** it scores negatively (friendly creature dies, opponent survives).
3. **Given** multiple opponent creatures, **When** the AI selects a fight target, **Then** it selects the opponent creature where the AI's fighter kills the target and survives, prioritizing highest-CMC kill.

---

### User Story 28 - Goad Tactical Evaluation (Priority: P3)

The AI evaluates goad effects (target creature must attack each turn if able and cannot attack the goading player), using them tactically to force opponent creatures into bad attacks or redirect threats away from the AI.

**Why this priority**: Forge's GoadAi handles goad. Goad is common in Commander and enables the AI to protect itself by redirecting opponent attackers.

**Acceptance Scenarios**:

1. **Given** an AI with a goad effect and an opponent with a threatening creature, **When** the AI has other opponents present (multiplayer), **Then** it goads the most threatening creature to redirect it.
2. **Given** a goaded creature that must attack, **When** the AI evaluates its blockers, **Then** it accounts for the goaded creature attacking a different player (not itself).
3. **Given** an AI with a goad effect in a two-player game, **When** evaluating the goad, **Then** it scores the goad as forcing the creature to attack into whatever blockers the AI prepares.

---

### User Story 29 - Structured Keyword Mechanics: Connive, Explore, Mutate (Priority: P3)

The AI makes informed decisions for three structured keyword mechanics that require choosing between options: Connive (draw then discard for a +1/+1 counter), Explore (reveal top card; if land put it in play, otherwise put it in hand optionally), and Mutate (merge onto a target creature, choosing the best base).

**Why this priority**: Forge has dedicated AI classes for each (ChoomConniveAi, ExploreAi, MutateAi). Without handling them the AI makes random or default choices that waste the mechanic's potential.

**Acceptance Scenarios**:

1. **Given** a creature with Connive triggers, **When** the AI must discard a card, **Then** it discards the highest-CMC card that is not castable this turn or a redundant land when ahead on mana.
2. **Given** an Explore trigger revealing a land, **When** the AI has fewer lands than needed for its curve, **Then** it puts the land onto the battlefield.
3. **Given** an Explore trigger revealing a non-land card, **When** the AI is ahead on lands, **Then** it puts the revealed card in hand (keeping library option secondary).
4. **Given** a Mutate spell and multiple friendly creatures, **When** the AI evaluates mutate targets, **Then** it mutates onto the creature that maximizes the combined resulting power/toughness and keyword set.

---

### User Story 30 - Remove From Combat Effects (Priority: P3)

The AI evaluates and uses effects that remove creatures from combat (e.g., "tap target attacking creature," "remove target blocker from combat") defensively when being attacked, and offensively to clear a blocker before damage.

**Why this priority**: Forge's RemoveFromCombatAi handles this class. Without it the AI ignores a useful category of combat-manipulation cards.

**Acceptance Scenarios**:

1. **Given** an AI being attacked by a 6/6 with no blockers and a "tap target attacker" instant available, **When** the attack step begins, **Then** the AI taps the 6/6 to prevent lethal damage.
2. **Given** an AI attacking whose creature is blocked, and the AI has a "remove target blocker from combat" instant, **When** the blocker is declared, **Then** the AI evaluates removing it if the attacker getting through deals lethal or significant damage.

---

### User Story 31 - Cascade Trigger Decisions (Priority: P3)

When a cascade spell resolves and cascades into a random card from the library, the AI evaluates that card and decides whether to cast it for free, choosing targets and modes as appropriate.

**Why this priority**: Cascade appears on many powerful spells. An AI that cannot evaluate and resolve the cascaded card correctly wastes the cascade trigger, which is often the primary value of the spell.

**Acceptance Scenarios**:

1. **Given** a cascade trigger that reveals a creature spell, **When** casting the creature for free, **Then** the AI casts it and selects any required targets using the same target-selection heuristics as normal casting.
2. **Given** a cascade trigger that reveals a modal spell, **When** casting it for free, **Then** the AI selects the best mode for the current board state.
3. **Given** a cascade trigger that reveals a land (not castable), **When** evaluating, **Then** the AI correctly skips lands and continues cascading to the next valid spell.

---

### User Story 32 - Delayed Trigger Handling (Priority: P3)

The AI correctly handles delayed triggered abilities — effects that are created now but trigger at a future point in the game (e.g., "at the beginning of your next upkeep, draw a card") — accounting for their pending value when making decisions.

**Why this priority**: Delayed triggers from enchantments, sagas, and spell effects are common. An AI that ignores them misvalues the cards that create them.

**Acceptance Scenarios**:

1. **Given** an AI casting a spell that creates a delayed trigger granting a card draw next upkeep, **When** scoring the spell, **Then** the spell's score includes the +15 draw bonus for the delayed trigger.
2. **Given** a delayed damage trigger that will fire at the opponent's next upkeep, **When** the trigger resolves, **Then** the AI selects the best target for the damage using the same burn targeting heuristics.
3. **Given** multiple delayed triggers pending, **When** they all fire in the same upkeep, **Then** the AI handles each in sequence without interference.

---

### User Story 33 - Life Payment Cost Evaluation (Priority: P3)

The AI evaluates spells and abilities with life-payment costs (Phyrexian mana: pay 2 life instead of 1 colored mana; or fixed life costs like "pay 4 life") and decides when paying life is an acceptable cost given the AI's current life total and game state.

**Why this priority**: Forge's AiCostDecision handles life-payment cost acceptance. Phyrexian mana and fixed life costs appear on many powerful cards; an AI that always or never pays life makes incorrect plays.

**Acceptance Scenarios**:

1. **Given** an AI with a Phyrexian mana spell and sufficient colored mana, **When** the AI is above 10 life, **Then** it pays colored mana instead of life to conserve life total.
2. **Given** an AI with a Phyrexian mana spell and no colored mana of the required color, **When** the AI is above 5 life, **Then** it pays 2 life to cast the spell rather than not casting it.
3. **Given** an AI at 3 life with a Phyrexian mana spell, **When** paying 2 life would put it at 1, **Then** the AI does not pay life unless the spell's effect wins the game.
4. **Given** a spell with a fixed "pay 4 life" cost and the AI at 20 life, **When** the spell would remove the opponent's most threatening permanent, **Then** the AI accepts the life payment.

---

### User Story 34 - Stack-Aware Ability Activation and Spell Copying (Priority: P3)

Beyond countering, the AI activates abilities and casts spells in direct response to items on the stack — such as pumping a creature in response to targeted removal on it, or copying a powerful opponent spell for its own benefit.

**Why this priority**: Forge's stack-aware activation system goes beyond counters. Responding to removal with pumping (to make the creature survive) and copying high-value opponent spells are core MTG skills.

**Acceptance Scenarios**:

1. **Given** an opponent targeting one of the AI's creatures with removal and the AI holding an instant that gives the creature +2/+2, **When** the removal is placed on the stack, **Then** the AI evaluates whether the pump makes the creature survive the removal and casts it if so.
2. **Given** an opponent casting a high-CMC spell and the AI controlling a copy effect (Fork, Reverberate), **When** the opponent's spell is on the stack, **Then** the AI evaluates copying it for its own benefit and does so if the copy's score exceeds the mana investment.
3. **Given** an opponent casting an aura targeting one of the AI's creatures and the AI holding a hexproof-granting instant, **When** the aura is on the stack, **Then** the AI casts hexproof in response to counter the aura's effect.

---

### User Story 35 - Make-Opponent-Lose-Life Scoring (Priority: P3)

The AI correctly scores spells that make the opponent lose life directly (as distinct from dealing damage) — such as "Target opponent loses 3 life" — treating them as burn-equivalent for the purpose of lethal calculation and face pressure.

**Why this priority**: Forge's LifeLoseAi handles this category. Without it, "lose 3 life" effects score zero despite being functionally identical to 3 damage for game-ending purposes.

**Acceptance Scenarios**:

1. **Given** an AI with a "target opponent loses 3 life" spell and the opponent at 3 life, **When** evaluating the action, **Then** the AI targets that opponent and the spell scores as lethal.
2. **Given** the same spell with the opponent at 10 life, **When** evaluating, **Then** it scores as (3 / 10) × 40 face-pressure score — same formula as burn.
3. **Given** the AI choosing between a "lose 3 life" spell and a 3-damage spell, **When** the effect is otherwise identical, **Then** both score equally (lose-life is treated as damage for heuristic purposes).

---

### User Story 36 - Safe Block Evaluation (Priority: P3)

When assigning blockers, the AI evaluates whether each proposed block is "safe" — i.e., the blocker survives after damage — and factors this into its blocking decisions, preferring blocks where the blocker kills the attacker and survives over pure chump-blocks when both options prevent damage.

**Why this priority**: Forge's AiBlockController (70KB) explicitly tracks which blocks are "safe" (blocker doesn't die). An AI that always chump-blocks wastes creatures when a favorable trade was available.

**Acceptance Scenarios**:

1. **Given** an AI with a 3/3 blocker and an opponent 2/2 attacker, **When** the AI evaluates blocking, **Then** it identifies this as a "safe block" (3/3 kills 2/2 and survives) and blocks favorably.
2. **Given** an AI with a 1/1 and a 3/3 blocker vs. a 4/4 attacker, **When** evaluating, **Then** it identifies neither block as "safe" (both blockers die) but still evaluates the net CMC trade-off.
3. **Given** an AI with a blocker where the block is not safe but is still the best available trade, **When** the CMC of the attacker exceeds the CMC of the blocker, **Then** the AI blocks anyway (favorable CMC trade).

---

### Edge Cases

- What if a board wipe would kill the AI's own commander? AI weighs commander-tax cost of recasting before scoring the wipe positively.
- What if all sacrifice targets are equally valued? AI picks deterministically (lowest index) to avoid non-determinism.
- What if the AI has a counterspell but the opponent's spell is CMC 1? AI applies configurable CMC threshold (default: only counter CMC ≥ 2) to avoid wasting counters on cantrips.
- What if lookahead simulation reveals a line requiring 3+ sequential actions? Simulation depth is capped at 2 turns; deeper lines are not simulated.
- What if a planeswalker's − ability would reduce loyalty to 0 or below? AI avoids activating it unless the effect is game-winning (opponent at ≤ 1 life).
- What if a modal spell has no applicable mode for the current board state? AI does not cast it — no valid mode equals no valid action.
- What if the AI has 0 creatures when an equip ability is available? Skip equip activation — no valid target.
- What if graveyard casting requires exiling cards as additional cost (escape)? AI validates it has sufficient graveyard cards before generating the action.
- What if Convoke would require tapping a creature the AI needs to attack with? AI evaluates the trade-off between casting the Convoke spell and preserving the attacker.
- What if a DFC's back face requires a condition that cannot be met this game? AI scores the DFC only by its front face (no transform bonus applied).
- What if the AI holds a Fog effect but has no life pressure for multiple turns? AI eventually casts it proactively at end of opponent's turn when it has no better use.
- What if a personality profile has conflicting directives (e.g., aggressive AND always counter)? Profile properties are evaluated independently; no conflict resolution needed.
- What if a meld pair requires one half to be on the battlefield before casting the other? AI tracks which halves it controls and factors the meld bonus only when both are accessible.
- What if the AI is in a multiplayer game with no clearly dominant opponent? AI defaults to attacking the opponent with the lowest life total.
- What if next-turn prediction includes opponent cards that are face-down or unknown? Unknown cards are ignored in prediction; only known threats are counted.
- What if a tutor can find any card type but the AI has no high-value card of that type in its deck? Score is capped at the average CMC of the fetchable card type.
- What if a fight effect would kill both creatures? AI evaluates it as a favorable outcome only if the opponent's creature CMC ≥ the AI's creature CMC.
- What if Connive triggers and the AI has no cards to discard? Connive without a valid discard does not apply the +1/+1 counter; AI must track this edge case.
- What if a cascade chain cascades into another cascade spell? AI resolves each cascade independently to the same depth; no infinite loops.
- What if paying Phyrexian mana would put the AI exactly at 0 life? AI does not pay the life cost regardless of spell value.
- What if a copy effect targets a spell the AI cannot legally copy (split second, etc.)? The copy action is not generated.
- What if Mutate has no valid base creature? Mutate action is not generated as legal.
- What if a delayed trigger has no valid target when it fires? AI passes the trigger with no selection (target disappears before trigger resolves).
- What if goad is used in a two-player game? AI evaluates goad as forcing the creature to attack directly into the AI's prepared blockers.
- What if a remove-from-combat effect targets a creature with vigilance? Effect still works; vigilance does not protect against removal from combat.
- What if the same permanent is both ANIMATED_THIS_TURN and would be targeted by the AI's own removal? AI avoids targeting its own animated permanents with its own removal.
- What if sideboarding is requested? Sideboarding is out of scope for this feature — no sideboard infrastructure exists in the engine.
- What if VoteAi (Council's Dilemma) cards are played? Voting is out of scope for this feature — these cards are too rare and require opponent vote modeling.
- What if energy counter cards are played? Energy counter tracking is out of scope for this feature.
- What if a card requires devotion-based scoring? Devotion/Converge color synergies are out of scope for this feature — they require color-density tracking beyond current board evaluation.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Target Selection
- **FR-001**: The AI MUST select spell and ability targets based on board-state heuristics, not auto-selection by the engine.
- **FR-002**: For destruction/exile removal, the AI MUST prefer the highest-CMC valid opponent target.
- **FR-003**: For burn spells, the AI MUST target the opponent player if the damage equals or exceeds their life total (lethal-first rule).
- **FR-004**: For buff/Aura spells, the AI MUST target its own highest-power creature.
- **FR-005**: For control-stealing spells, the AI MUST target the highest-CMC opponent permanent.

#### Modal Spell Evaluation
- **FR-006**: The AI MUST evaluate each available mode of a modal spell independently and select the mode(s) with the highest combined score.
- **FR-007**: Mode scores MUST use the same heuristics as equivalent non-modal effects (removal score, draw score, etc.).
- **FR-008**: If no mode applies to the current board state (e.g., removal mode with no targets), the AI MUST skip that mode and consider only valid modes.

#### Planeswalker Loyalty Abilities
- **FR-009**: The AI MUST activate exactly one loyalty ability per planeswalker per turn during its main phase.
- **FR-010**: The AI MUST prefer + abilities when building toward an ultimate; prefer − abilities when they remove a threat or are game-winning.
- **FR-011**: The AI MUST NOT activate a − ability that would reduce loyalty to 0 or below, unless the resulting effect ends the game.

#### Equipment Attachment
- **FR-012**: The AI MUST evaluate equip activation as a scoreable action and activate it when mana is available and a valid creature target exists.
- **FR-013**: The AI MUST equip to the creature that gains the highest net power/toughness benefit from the equipment's bonuses.

#### Instant-Speed Holding (Counterspells and Combat Tricks)
- **FR-014**: The AI MUST model "hold up mana" as a valid strategy: passing its main phase with open mana to respond on the opponent's turn.
- **FR-015**: The AI MUST counter opponent spells at or above a configurable CMC threshold (default: CMC ≥ 2) when a counterspell and sufficient mana are available.
- **FR-016**: The AI MUST cast instant pump spells at declare-blockers timing when the pump would save a friendly creature or kill an attacker.
- **FR-017**: The AI MUST NOT cast combat trick instants as sorceries in main phase when a combat window is available this turn.

#### Sacrifice Decisions
- **FR-018**: When a spell or ability requires sacrificing a permanent, the AI MUST choose the valid target with the lowest CMC.
- **FR-019**: Tokens MUST be preferred as sacrifice targets over non-token permanents of equal or higher CMC.
- **FR-020**: If no valid sacrifice target exists, the action requiring the sacrifice MUST NOT be presented as legal.

#### Scry and Surveil
- **FR-021**: For Scry N, the AI MUST keep cards on top whose CMC is castable within the next 2 turns and bottom all others.
- **FR-022**: For Surveil N, the AI MUST send cards with flashback, escape, or unearth to the graveyard to enable future graveyard casting; apply Scry logic to all other cards.

#### Card Draw Scoring
- **FR-023**: Spells that draw cards MUST score a base value of 15 per card drawn in the heuristic evaluator.
- **FR-024**: Cantrips (draw 1 as a bonus effect on another spell) MUST add at least 15 points on top of the spell's primary effect score.

#### Ramp Scoring
- **FR-025**: Spells that produce or fetch additional lands MUST score based on mana acceleration: (turns_of_mana_acceleration × 20) points.
- **FR-026**: Mana-producing creatures (mana dorks) MUST receive a ramp bonus of 15 per mana produced per activation, in addition to their base creature score.

#### Board Wipe Evaluation
- **FR-027**: Before scoring a mass-destruction effect positively, the AI MUST compare opponent permanent CMC total destroyed vs own permanent CMC total destroyed.
- **FR-028**: A board wipe MUST score negatively (not cast) when friendly permanents destroyed CMC ≥ opponent permanents destroyed CMC.
- **FR-029**: The AI MUST exclude indestructible permanents from the "destroyed" count when evaluating board wipes.

#### Mulligan Decisions
- **FR-030**: The AI MUST mulligan any opening hand with 0 lands or 7 lands.
- **FR-031**: The AI MUST mulligan any opening hand where no spell is castable within the first 4 turns given the lands present.
- **FR-032**: The AI MUST NOT mulligan below 5 cards (accept any 5-card hand with ≥ 1 land).

#### Mana Holding for Phase 2
- **FR-033**: If the AI has no main-phase-1 actions scoring above a "hold" threshold, it MUST pass to combat/main-2 rather than making a low-value play.
- **FR-034**: After combat, the AI MUST re-evaluate all hand cards for main-phase-2 plays.

#### Graveyard Zone Casting
- **FR-035**: The AI MUST generate legal actions for cards in the graveyard with flashback, escape, unearth, or disturb keywords.
- **FR-036**: Graveyard casts MUST be scored using the same heuristics as hand casts, with a +10 bonus for the "free resource" advantage.
- **FR-037**: Escape casts MUST only be generated if the AI's graveyard contains at least the required number of cards for the exile cost.

#### ETB and Dies Trigger Evaluation
- **FR-038**: When scoring a creature spell, the AI MUST add bonus points for detectable ETB effects: +15 per card drawn on ETB, +10 per damage dealt on ETB, +15 per token created on ETB.
- **FR-039**: Creatures with "when this dies" effects that produce tokens or draw cards MUST receive a +10 trade-willingness bonus.

#### Cross-Turn Game State Memory
- **FR-040**: The AI MUST maintain a per-game memory structure tracking: cards revealed from the opponent's hand and permanents bounced this turn.
- **FR-041**: Revealed opponent counterspells MUST reduce the AI's willingness to cast its highest-value spell into the opponent's open mana window (score penalty of −20 on top targets).

#### Lookahead Simulation
- **FR-042**: The AI MUST simulate its own next turn to evaluate whether the current action enables a higher-value play one turn ahead.
- **FR-043**: Lookahead MUST be bounded to depth 2 (current turn + 1 future turn) to prevent performance degradation.
- **FR-044**: A positive lookahead result MUST add a sequence bonus (up to +30) to the score of the leading action that enables it.

#### Control Gain and Life Gain
- **FR-045**: Control-stealing spells MUST score the stolen permanent's CMC × 15.
- **FR-046**: Life gain spells MUST score based on urgency: when the AI is at ≤ 5 life, life gain score receives a 2× multiplier.

#### Board Position Holistic Evaluation
- **FR-047**: The heuristic player MUST compute a board position delta for each candidate action (before-state vs after-state) and use the delta to rank actions.
- **FR-048**: Board position MUST include: (sum of friendly permanent CMC on battlefield) + (hand_size × 5) + (life_total × 0.5) − (opponent permanent CMC) − (opponent hand_size × 5).

#### AI Personality and Difficulty Profiles
- **FR-049**: The AI MUST support a named personality profile that configures all behavioral probability and boolean properties, bound per AI player instance (not global).
- **FR-050**: The personality profile MUST support the following boolean flags: ALWAYS_COUNTER_REMOVAL_SPELLS, ALWAYS_COUNTER_OTHER_COUNTERSPELLS, ALWAYS_COUNTER_DAMAGE_SPELLS, ALWAYS_COUNTER_PUMP_SPELLS, ALWAYS_COUNTER_AURAS, ACTIVELY_DESTROY_ARTIFACTS_AND_ENCHANTMENTS, ACTIVELY_DESTROY_IMMEDIATELY_UNBLOCKABLE, ATTACK_INTO_TRADE_WHEN_TAPPED_OUT, TRY_TO_AVOID_ATTACKING_INTO_CERTAIN_BLOCK, ENABLE_RANDOM_FAVORABLE_TRADES_ON_BLOCK, RANDOMLY_TRADE_EVEN_WHEN_HAVE_LESS_CREATURES.
- **FR-051**: The personality profile MUST support probability overrides (0.0–1.0) for: CHANCE_TO_ATTACK_INTO_TRADE (default 0.4), CHANCE_TO_HOLD_COMBAT_TRICKS (default 0.3), CHANCE_TO_TRADE_TO_SAVE_PLANESWALKER (default 0.7), CHANCE_TO_ATKTRADE_WHEN_OPP_HAS_MANA (default 0.3), CHANCE_DECREASE_TO_TRADE_VS_EMBALM (default 0.5), TOKEN_GENERATION_CHANCE (default 0.8), CHANCE_TO_COUNTER_CMC_1 (default 0.5), CHANCE_TO_COUNTER_CMC_2 (default 0.75), CHANCE_TO_COUNTER_CMC_3_PLUS (default 1.0).
- **FR-052**: The personality profile MUST support the HOLD_LAND_DROP_FOR_MAIN2_IF_UNUSED flag: when enabled, the AI holds its land drop in main phase 1 if it has no main-phase-1 plays and re-evaluates the land drop in main phase 2.
- **FR-053**: The personality profile MUST support equipment movement logic: when a creature with attached equipment dies, the profile flag RE_EQUIP_ON_CREATURE_DEATH controls whether the AI actively re-equips to the next best creature that same turn.
- **FR-054**: The AI MUST ship with at least two named profiles: "default" (balanced, all probabilities at default values) and "aggro" (CHANCE_TO_ATTACK_INTO_TRADE = 0.8, ATTACK_INTO_TRADE_WHEN_TAPPED_OUT = true, lower counter thresholds).

#### Alternative Casting Costs
- **FR-055**: The AI MUST generate Convoke cast actions when it has untapped creatures and insufficient mana to cast normally, tapping creatures to cover the generic and colored mana cost.
- **FR-056**: The AI MUST evaluate the trade-off of tapping creatures for Convoke vs. using those creatures to attack or block; Convoke is preferred when the spell's score exceeds the attacking value of the tapped creatures.
- **FR-057**: The AI MUST generate Delve cast actions when it has cards in the graveyard and an insufficient mana pool, exiling graveyard cards to cover generic mana costs.
- **FR-058**: The AI MUST generate Emerge cast actions when it controls a valid sacrifice target whose CMC reduces the Emerge cost to affordable, and the Emerge spell's score exceeds the sacrificed creature's score.
- **FR-059**: The AI MUST generate life-payment cast actions for Phyrexian mana spells when: the AI has no valid colored mana source AND the AI's current life total is above a configurable threshold (default: 5 life remaining after payment).
- **FR-060**: The AI MUST NOT pay life for Phyrexian mana when the AI has sufficient colored mana to pay normally — life is preserved unless there is no other way to cast the spell.
- **FR-061**: Alternative cost actions MUST be scored using the same heuristics as normal casts of the resulting spell.

#### Token Generation Spell Scoring
- **FR-062**: Standalone token-producing spells (instants, sorceries, enchantments that create tokens but are not creatures themselves) MUST score based on the total power × 8 + total toughness × 4 of all tokens created.
- **FR-063**: Flying tokens MUST receive the same evasion bonus in token scoring as flying creatures receive in creature scoring (+power × 8.0).
- **FR-064**: Token spells that create multiple tokens MUST score the sum of all token values. The TOKEN_GENERATION_CHANCE personality property (default 0.8) applies a probability multiplier to this score.

#### Multiplayer Attack Direction
- **FR-065**: In games with more than two players, the AI MUST evaluate all opponents as potential attack targets and select the direction that maximizes expected damage dealt or eliminates a player.
- **FR-066**: The AI MUST prioritize attacking an opponent who would be eliminated by the attack (life total ≤ total attacking power) over attacking a stronger opponent.
- **FR-067**: When no lethal attack is available, the AI MUST attack the opponent with the highest permanent CMC total on board (the biggest threat).

#### Transform and Meld Card Evaluation
- **FR-068**: DFC creatures MUST score their front face plus a transform bonus: (back_face_power − front_face_power) × 10 + (back_face_toughness − front_face_toughness) × 5, floored at 0.
- **FR-069**: The AI MUST factor transform conditions into the bonus: if the transform condition cannot be met within 3 turns given the current game state, the transform bonus is 0.
- **FR-070**: Meld cards MUST score an additional meld bonus of (melded_CMC × 12) when the AI controls both halves and the meld is achievable this game.

#### Fog and Defensive Spell Recognition
- **FR-071**: The AI MUST recognize Fog-effect spells (prevent all combat damage this turn) and flag them as "hold for opponent's attack step" rather than scoring them for main-phase casting.
- **FR-072**: The AI MUST cast a held Fog effect during the opponent's attack step if and only if the incoming combat damage would reduce the AI's life total to ≤ 0 or below a configurable threshold (default: 5).
- **FR-073**: Fog effects MUST be tracked in the AI's cross-turn memory as CHOSEN_FOG_EFFECT so the AI does not evaluate casting additional spells when holding a Fog response.

#### Artifact and Enchantment Removal Prioritization
- **FR-074**: The AI MUST score artifact and enchantment removal spells based on the target's CMC: target_CMC × 10, with a +15 bonus if the target generates repeated value per turn (e.g., draws a card, produces mana).
- **FR-075**: Equipment attached to an opponent's creature MUST score as both an equipment removal AND a de-buff to the attached creature (stacking bonus of +equipment_CMC × 5).
- **FR-076**: The AI MUST actively evaluate destroying unblockable-granting artifacts and enchantments with urgency (score × 1.5 multiplier) as they directly threaten the AI's ability to block.

#### Next-Turn Attack Prediction
- **FR-077**: At the end of each turn, the AI MUST compute a predicted incoming damage value: sum of opponent creatures' power that will untap and have no summoning sickness next turn, minus the AI's available blockers' toughness.
- **FR-078**: The predicted incoming damage MUST influence current-turn decisions: if predicted damage ≥ current life total, the AI prioritizes removing a threat or developing a blocker over offensive plays.
- **FR-079**: Known opponent hand contents (from revealed cards in AIMemory) MUST be added to the attack prediction when those cards include pump spells or haste creatures.

#### Cross-Turn Memory (Full AIMemory Specification)
- **FR-080**: AIMemory MUST track all of the following named categories per player per game: REVEALED_CARDS (opponent hand contents learned through effects), BOUNCED_THIS_TURN (permanents returned to hand this turn), ATTACHED_THIS_TURN (equipment attached this turn), ANIMATED_THIS_TURN (permanents animated into creatures this turn), CHOSEN_FOG_EFFECT (fog held for defensive use), TRICK_ATTACKERS (attackers designated as trick bait — attack to provoke block then use instant trick), MANDATORY_ATTACKERS (creatures forced to attack by goad or other effects), HELD_MANA_SOURCES_FOR_MAIN2 (mana sources held back from main phase 1), HELD_MANA_SOURCES_FOR_DECLBLK (mana sources held for the declare blockers window).
- **FR-081**: ATTACHED_THIS_TURN, ANIMATED_THIS_TURN, BOUNCED_THIS_TURN, TRICK_ATTACKERS, and HELD_MANA_SOURCES categories MUST be cleared at the start of each of the AI's turns.
- **FR-082**: MANDATORY_ATTACKERS MUST be updated when goad or similar effects are applied and cleared when those effects end.
- **FR-083**: The AI MUST use TRICK_ATTACKERS to designate some attackers as trick bait when it holds a combat-pump instant: these attackers attack specifically to provoke a block, allowing the AI to cast the trick during the declare blockers step.
- **FR-084**: HELD_MANA_SOURCES_FOR_DECLBLK MUST prevent the AI from tapping designated mana sources for main-phase plays when it intends to hold them for combat-step instant responses.

#### Animate Land and Artifact Scoring
- **FR-085**: Spells and abilities that animate a land or artifact into a creature MUST score based on the animated creature's resulting power × 8 + toughness × 4 plus applicable keyword bonuses.
- **FR-086**: The AI MUST record animated permanents in ANIMATED_THIS_TURN memory and must not re-animate the same permanent twice per turn.

#### Library Search and Tutor Scoring
- **FR-087**: Spells that search the library for a specific card type MUST score based on the CMC of the highest-value card in the AI's deck matching the search criteria, scaled by (best_card_CMC × 10).
- **FR-088**: When multiple cards match search criteria, the AI MUST select the card that best addresses the current game state: removal when under threat, ramp when behind on mana, finisher when ahead.

#### Fight Mechanic Scoring
- **FR-089**: Fight spells MUST score based on the outcome of the fight: +attacker_CMC × 10 if the opponent creature dies and the AI's creature survives; 0 if it's a mutual kill; −AI_creature_CMC × 8 if only the AI's creature dies.
- **FR-090**: When selecting the fight pairing, the AI MUST choose the opponent creature where the AI's fighter survives and kills the target, preferring highest-CMC targets.

#### Goad Evaluation
- **FR-091**: Goad effects MUST score based on the CMC of the goaded creature × 8, with an additional multiplier in multiplayer (×1.5) since the goaded creature must attack another player.
- **FR-092**: The AI MUST record goaded opponent creatures in MANDATORY_ATTACKERS and account for them not being available to block.

#### Connive, Explore, and Mutate Evaluation
- **FR-093**: For Connive, the AI MUST discard the card in hand with the lowest current-turn utility: highest CMC card that cannot be cast this turn, or a redundant land when ahead on mana.
- **FR-094**: For Explore, the AI MUST put a revealed land onto the battlefield when it has fewer lands than needed for its next 2 turns of curve, and put the revealed non-land card in hand otherwise.
- **FR-095**: For Mutate, the AI MUST select the base creature that maximizes the resulting merged creature's power + toughness + keyword count after applying the mutating card's stats.

#### Remove From Combat Scoring
- **FR-096**: Spells and abilities that remove an opponent's attacking creature from combat MUST score as (attacker_power × 6) when the AI would otherwise take that damage unblocked, or (attacker_CMC × 8) when tapping an attacker the AI cannot block.
- **FR-097**: Spells that remove a blocking creature from combat MUST score as (blocked_attacker_power × 5) representing the damage the AI's attacker now deals unblocked.

#### Cascade Trigger Decisions
- **FR-098**: When a cascade trigger fires and a valid spell is revealed, the AI MUST evaluate casting that spell using the same heuristics as casting from hand, and cast it if the score is positive.
- **FR-099**: If the cascaded card is a land or has CMC higher than the cascade threshold, the AI MUST skip it per the cascade rules and continue cascading.

#### Delayed Trigger Handling
- **FR-100**: When a spell creates a delayed trigger, the AI MUST include the trigger's future value in the spell's score at cast time (e.g., +15 for a "draw a card next upkeep" delayed trigger).
- **FR-101**: When a delayed trigger fires and requires a target selection, the AI MUST select targets using the same heuristics as immediate effect targeting.

#### Stack-Aware Ability Activation and Spell Copying
- **FR-102**: When an opponent targets one of the AI's permanents with a removal spell, the AI MUST evaluate activating protective instant-speed abilities (hexproof, indestructible, pump to survive) in response, and do so if the protective effect's score exceeds the mana cost.
- **FR-103**: The AI MUST evaluate copy effects targeting opponent spells on the stack: the copy scores as (copied_spell_score × 0.9) since copying is slightly less efficient than casting originally.

#### Make-Opponent-Lose-Life Scoring
- **FR-104**: Spells with "target opponent loses N life" effects MUST be scored identically to burn spells dealing N damage: lethal-first targeting of opponent player, otherwise face pressure = (N / opponent_life) × 40.

#### Safe Block Evaluation
- **FR-105**: The AI MUST classify each proposed block as "safe" (blocker survives after combat damage), "trade" (both die), or "chump" (only blocker dies) before making the final blocking assignment.
- **FR-106**: Safe blocks MUST be preferred over trades, and trades preferred over chump blocks, all else equal.
- **FR-107**: The AI MUST still assign chump blocks when incoming damage is lethal and no safe or trade blocks are available.

### Key Entities

- **AIMemory**: Per-game, per-player structure with named categories: REVEALED_CARDS, BOUNCED_THIS_TURN, ATTACHED_THIS_TURN, ANIMATED_THIS_TURN, CHOSEN_FOG_EFFECT, TRICK_ATTACKERS, MANDATORY_ATTACKERS, HELD_MANA_SOURCES_FOR_MAIN2, HELD_MANA_SOURCES_FOR_DECLBLK; persists across turns within a single game session.
- **BoardScore**: Numeric value representing a player's overall game position; computed before and after each candidate action for delta-based ranking.
- **ActionCandidate**: A legal action paired with its computed heuristic score, optional lookahead bonus, selected targets/modes, and classification (safe/trade/chump for blocks).
- **ModeEvaluation**: Score computed for a single mode of a modal spell; used to select the optimal mode(s) before generating the final action.
- **LookaheadState**: Lightweight game state snapshot used during 1-turn lookahead simulation; discarded after scoring completes.
- **AiPersonalityProfile**: Named configuration object containing all tunable behavior probability and boolean properties; bound per AI player instance.
- **AttackPrediction**: Computed estimate of incoming damage from the opponent next turn; derived from opponent untapped creatures, known hand contents, and summoning sickness state.
- **TransformBonus**: Computed delta score added to a DFC card's base score representing the value uplift of its back face under achievable conditions.
- **BlockClassification**: Enum (SAFE / TRADE / CHUMP) assigned to each proposed block before final blocker assignment.
- **CascadeResolution**: Temporary evaluation context created when a cascade trigger fires; holds the cascaded card and its computed action score.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The AI correctly selects the highest-CMC opponent target for removal spells in 100% of deterministic unit test cases.
- **SC-002**: The AI targets the opponent player for lethal burn in 100% of cases where damage ≥ opponent life total.
- **SC-003**: The AI activates a planeswalker loyalty ability on every turn it controls a planeswalker and has priority in main phase (0% skipped turns).
- **SC-004**: Board wipe evaluation produces a net-negative score (spell not cast) when AI-controlled permanent CMC destroyed ≥ opponent CMC destroyed, in 100% of unit test cases.
- **SC-005**: Card draw spells score above "pass priority" in 100% of board states where the AI can legally cast them.
- **SC-006**: Ramp spells score at least as high as a vanilla 2/2 of equal CMC during the first 4 turns of a game, in 100% of test cases.
- **SC-007**: Sacrifice decisions select the lowest-CMC valid target in 100% of deterministic test cases.
- **SC-008**: The AI correctly mulligans 0-land and 7-land hands in 100% of test cases and keeps 2–4 land + on-curve hands in 100% of test cases.
- **SC-009**: All 376 existing tests continue to pass after implementation (zero regressions).
- **SC-010**: AI turn decision time remains under 500ms per action on a standard 6-land / 4-permanent board state (including lookahead simulation).
- **SC-011**: In a simulated series of AI vs AI games with counterspell-capable decks, the AI correctly holds up mana and counters opponent spells above the CMC threshold in at least 90% of eligible opportunities.
- **SC-012**: Two AI instances with different personality profiles (default vs. aggro) produce measurably different attack rates (≥ 15% difference in attacks-per-turn) over a 10-game series.
- **SC-013**: The AI generates and evaluates Convoke, Delve, and Emerge cast actions in 100% of board states where the alternative cost is achievable.
- **SC-014**: Token-producing spells score above zero (above "pass priority") in 100% of board states where the AI can legally cast them.
- **SC-015**: In a 4-player game, the AI attacks the lowest-life opponent when a lethal attack exists in 100% of test cases.
- **SC-016**: DFC creatures score higher than their vanilla front-face stats alone in 100% of cases where the back face is meaningfully more powerful.
- **SC-017**: The AI correctly casts held Fog effects to prevent lethal combat damage in 100% of deterministic test cases.
- **SC-018**: Artifact and enchantment removal scores above zero in 100% of board states where a threatening opponent artifact or enchantment is present.
- **SC-019**: Attack prediction correctly identifies that the AI is at risk of lethal next turn (predicted damage ≥ life total) in 100% of deterministic test cases, causing the AI to prioritize defense.
- **SC-020**: Fight spells score positively (and are cast) in 100% of board states where the AI's fighter kills the opponent's creature and survives.
- **SC-021**: Tutor spells score above "pass priority" in 100% of board states where the deck contains a card matching the search criteria.
- **SC-022**: Connive discard selections choose the lowest-utility card (highest uncastable CMC) in 100% of deterministic test cases.
- **SC-023**: Cascade triggers correctly evaluate and cast the cascaded spell (if score > 0) in 100% of cascade resolution test cases.
- **SC-024**: The AI classifies blocks as SAFE/TRADE/CHUMP correctly and prefers SAFE > TRADE > CHUMP in 100% of deterministic blocking test cases.
- **SC-025**: Life-payment (Phyrexian mana) decisions correctly pay life when no colored mana is available and AI life > threshold, and correctly decline when AI life ≤ threshold, in 100% of test cases.
- **SC-026**: Personality profile boolean flags (e.g., ALWAYS_COUNTER_REMOVAL_SPELLS) override threshold-based decisions in 100% of applicable situations.
- **SC-027**: MANDATORY_ATTACKERS memory correctly tracks goaded creatures and prevents them from being counted as available blockers in 100% of test cases.

## Explicitly Out of Scope

The following Forge AI capabilities are **not included** in this feature due to missing infrastructure, extreme rarity, or format unsuitability:

- **Sideboarding** — No sideboard zone exists in the engine. Requires separate infrastructure work.
- **VoteAi / Council's Dilemma** — Voting mechanics require opponent vote modeling and are too rare to justify inclusion.
- **Energy counters** — Energy-based decks require a dedicated energy tracking system not currently in the engine.
- **Devotion / Converge color-density synergies** — Narrow card synergies requiring color-density tracking beyond the current board model.
- **Planechase format (planar die rolling)** — Planechase is not a supported format in this engine.
- **SpecialCardAi (named-card custom logic)** — Custom AI logic for specific named cards cannot be generalized in a spec; handled card by card as needed.
- **Mana cheat detection** — An internal engine security concern, not an AI decision.
- **PoisonAi** — Poison counters are tracked by the engine SBA system; AI decision-making beyond attacking does not differ for poison strategies.

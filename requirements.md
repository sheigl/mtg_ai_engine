# Requirements: MTG Rules Engine

## 1. Game Management

### 1.1 Game Lifecycle
- REQ-G01: `POST /game` creates a new game, accepts two player configs
  (deck lists as card name arrays), returns a `game_id` and initial
  game state
- REQ-G02: `GET /game/{game_id}` returns the full current game state
  as a JSON object
- REQ-G03: `DELETE /game/{game_id}` ends and archives a game,
  triggering data export
- REQ-G04: Each game is assigned a random seed at creation; the same
  seed + same action sequence must reproduce the identical game
- REQ-G05: Game state includes: turn number, active player, phase,
  step, priority holder, stack contents, all zones for both players
  (hand, library, graveyard, exile, battlefield, command zone),
  all permanent states, life totals, and all counters

### 1.2 Zones
- REQ-G06: Engine tracks the following zones per player: library,
  hand, graveyard, exile; shared zones: stack, battlefield
- REQ-G07: Zone changes are atomic — a card cannot exist in two zones
  simultaneously
- REQ-G08: Library order is tracked and preserved; cards drawn always
  come from the top

---

## 2. Turn Structure

- REQ-T01: Full turn structure is enforced in order: Beginning Phase
  (Untap, Upkeep, Draw), Pre-combat Main Phase, Combat Phase (Beginning
  of Combat, Declare Attackers, Declare Blockers, Combat Damage, End of
  Combat), Post-combat Main Phase, Ending Phase (End, Cleanup)
- REQ-T02: `POST /game/{game_id}/pass` advances priority to the next
  player or advances the phase/step when both players pass in sequence
- REQ-T03: Untap step does not use the stack; permanents controlled by
  the active player untap unless an effect prevents it
- REQ-T04: Active player draws one card at the start of their Draw step
  (except the first player on their first turn in a two-player game)
- REQ-T05: Cleanup step discards to hand size (7), removes damage from
  creatures, ends "until end of turn" effects

---

## 3. Actions

### 3.1 Playing Lands
- REQ-A01: `POST /game/{game_id}/play-land` accepts `card_id`; engine
  validates it is a land, it is the player's turn, main phase, stack is
  empty, and the player has not already played a land this turn
- REQ-A02: Playing a land does not use the stack; it moves directly
  from hand to battlefield

### 3.2 Casting Spells
- REQ-A03: `POST /game/{game_id}/cast` accepts `card_id`,
  `mana_payment` (map of mana spent), and `targets` (array of target
  ids); engine validates legality of the cast including mana cost,
  timing restrictions, and target validity
- REQ-A04: Casting a spell moves it to the stack; it does not resolve
  until all players pass priority in succession
- REQ-A05: Alternative costs (flashback, overload, kicker, etc.) are
  accepted via an `alternative_cost` field; engine validates the
  alternative cost is applicable

### 3.3 Activated Abilities
- REQ-A06: `POST /game/{game_id}/activate` accepts `permanent_id` and
  `ability_index`; engine validates cost payment and timing restrictions
- REQ-A07: Mana abilities resolve immediately without using the stack

### 3.4 Triggered Abilities
- REQ-A08: Engine automatically detects and generates triggered ability
  objects when trigger conditions are met
- REQ-A09: `GET /game/{game_id}/pending-triggers` returns triggers
  waiting to be put on the stack by their controller
- REQ-A10: `POST /game/{game_id}/put-trigger` puts a pending trigger
  on the stack; player may choose order when multiple triggers are
  controlled by the same player

### 3.5 Combat
- REQ-A11: `POST /game/{game_id}/declare-attackers` accepts array of
  `{attacker_id, defending_player_or_planeswalker_id}`; engine validates
  attack legality (summoning sickness, tapped status, etc.)
- REQ-A12: `POST /game/{game_id}/declare-blockers` accepts array of
  `{blocker_id, attacker_id}`; engine validates blocking legality
- REQ-A13: When multiple creatures block a single attacker, the
  attacking player must order blockers: `POST /game/{game_id}/order-blockers`
- REQ-A14: First strike and double strike damage are handled as two
  separate combat damage steps where applicable
- REQ-A15: `POST /game/{game_id}/assign-combat-damage` accepts damage
  assignments; engine validates minimum lethal damage assignment rules

### 3.6 Special Actions
- REQ-A16: `POST /game/{game_id}/special-action` handles: playing a
  face-down card as a 2/2, turning a morph face up, suspending a card,
  and other actions that do not use the stack

---

## 4. Stack and Priority

- REQ-S01: Priority is granted to the active player after each spell or
  ability is placed on the stack, and at the start of each step/phase
- REQ-S02: The top of the stack resolves only when all players pass
  priority in succession with the stack non-empty, or when the stack is
  empty and priority is passed
- REQ-S03: Split-second spells prevent any player from casting spells
  or activating non-mana abilities while they are on the stack
- REQ-S04: The engine correctly models the full APNAP (Active Player,
  Non-Active Player) ordering for simultaneous triggers
- REQ-S05: `GET /game/{game_id}/legal-actions` returns the complete
  set of legal actions for the priority holder at any moment

---

## 5. Rules Engine — Comprehensive Rules Coverage

### 5.1 State-Based Actions
- REQ-R01: State-based actions (SBAs) are checked and applied
  continuously before any player receives priority:
    - Creatures with toughness ≤ 0 are put into the graveyard
    - Creatures with lethal damage are destroyed (unless indestructible)
    - Players with 0 or less life lose the game
    - Players who must draw from an empty library lose the game
    - Tokens in any zone other than the battlefield cease to exist
    - Auras not attached to a legal permanent are put into the graveyard
    - Equipment attached to an illegal permanent becomes unattached
    - Planeswalkers with 0 loyalty counters are put into the graveyard
    - A player who has 10 or more poison counters loses the game
    - Legendary rule (player chooses which to keep)
    - World rule (only most recent world enchantment remains)

### 5.2 Layer System (CR 613)
- REQ-R02: Continuous effects are applied in the correct layer order:
    - Layer 1: Copy effects
    - Layer 2: Control-changing effects
    - Layer 3: Text-changing effects
    - Layer 4: Type-changing effects
    - Layer 5: Color-changing effects
    - Layer 6: Ability-adding/removing effects
    - Layer 7: Power/toughness effects (7a dependency, 7b set,
      7c modify, 7d switch)
- REQ-R03: Dependency between effects within a layer is computed
  correctly (an effect that depends on another applies after it)
- REQ-R04: Timestamp ordering is used when no dependency exists

### 5.3 Replacement Effects
- REQ-R04: Replacement effects modify events before they occur; the
  engine intercepts the relevant event and applies all applicable
  replacement effects
- REQ-R05: When multiple replacement effects apply to the same event,
  the affected player (or controller of the affected object) chooses
  the order of application
- REQ-R06: Self-replacement effects (e.g. a permanent replacing its
  own entering the battlefield) are correctly identified and applied

### 5.4 Damage
- REQ-R07: Damage to creatures uses a damage-marked system; creatures
  are destroyed by SBA when marked damage ≥ toughness
- REQ-R08: Damage to players reduces life total
- REQ-R09: Trample damage: excess damage beyond lethal to blockers
  is assigned to the defending player
- REQ-R10: Deathtouch: any amount of damage from a deathtouch source
  is considered lethal for SBA purposes
- REQ-R11: Lifelink: damage dealt by a lifelink creature causes its
  controller to gain that much life (as a replacement effect in
  damage-dealing)
- REQ-R12: Infect: damage to creatures is dealt as -1/-1 counters;
  damage to players is dealt as poison counters

### 5.5 Counters
- REQ-R13: Counter types are tracked as key-value pairs on permanents
  and players; engine supports all named counter types (+1/+1, -1/-1,
  loyalty, poison, charge, etc.)
- REQ-R14: +1/+1 and -1/-1 counters annihilate each other as an SBA

### 5.6 Copy Effects
- REQ-R15: Copying a spell or permanent copies the copiable values
  (name, mana cost, type line, oracle text, p/t if creature) but not
  choices made on the original, counters, or damage
- REQ-R16: A token created as a copy of a permanent copies the
  permanent's current copiable values at the time the token is created

### 5.7 Token Creation
- REQ-R17: Token creation instantiates a permanent with specified
  characteristics; tokens that leave the battlefield cease to exist

### 5.8 Targeting
- REQ-R18: Targets are validated at the time of casting/activation and
  again at resolution; if no targets remain legal at resolution the
  spell or ability is countered
- REQ-R19: Protection, shroud, and hexproof are correctly enforced
  during target validation

### 5.9 Keywords (full list)
- REQ-R20: The following keyword abilities are fully implemented:
  deathtouch, defender, double strike, enchant, equip, first strike,
  flash, flying, haste, hexproof, indestructible, intimidate, landwalk
  variants, lifelink, protection, reach, shroud, trample, vigilance,
  banding, flanking, provoke, bushido, soulshift, ninjutsu, haunt,
  convoke, dredge, transmute, bloodthirst, graft, recover, ripple,
  split second, suspend, vanishing, absorb, aura swap, delve, fortify,
  frenzy, gravestorm, poisonous, transfigure, champion, changeling,
  evoke, hideaway, prowl, reinforce, conspire, persist, wither,
  retrace, devour, exalted, unearth, cascade, annihilator, level up,
  rebound, totem armor, infect, battle cry, living weapon, undying,
  miracle, soulbond, overload, scavenge, unleash, cipher, evolve,
  extort, fuse, bestow, tribute, dethrone, hidden agenda, outlast,
  prowess, dash, exploit, menace, renown, awaken, devoid, ingest,
  myriad, surge, skulk, emerge, escalate, meld, crew, fabricate,
  partner, undaunted, improvise, aftermath, embalm, eternalize, afflict,
  ascend, assist, jump-start, mentor, riot, spectacle, escape,
  companion, mutate, encore, boast, foretell, demonstrate, daybound,
  nightbound, disturb, dungeon, ward, blitz, casualty, connive,
  domain, enlist, read ahead, reconfigure, training, cleave, compleated,
  prototype, unearth, backup, bargain, disguise, cloak, plot, suspect,
  manifest dread, saddle, gift

---

## 6. REST API Specification

### 6.1 Endpoints

```
POST   /game                              Create new game
GET    /game/{game_id}                    Get full game state
DELETE /game/{game_id}                    End game + export data

POST   /game/{game_id}/pass              Pass priority
POST   /game/{game_id}/play-land         Play a land
POST   /game/{game_id}/cast              Cast a spell
POST   /game/{game_id}/activate          Activate an ability
POST   /game/{game_id}/put-trigger       Put pending trigger on stack
POST   /game/{game_id}/special-action    Perform a special action

POST   /game/{game_id}/declare-attackers Declare attackers
POST   /game/{game_id}/declare-blockers  Declare blockers
POST   /game/{game_id}/order-blockers    Order multiple blockers
POST   /game/{game_id}/assign-combat-damage Assign combat damage

GET    /game/{game_id}/legal-actions     Get all legal actions
GET    /game/{game_id}/pending-triggers  Get triggers awaiting stack
GET    /game/{game_id}/stack             Get current stack contents

POST   /game/{game_id}/choice            Submit a player choice
                                         (modal, target order, etc.)

GET    /export/{game_id}/snapshots        Export game state snapshots
GET    /export/{game_id}/transcript       Export play-by-play transcript
GET    /export/{game_id}/rules-qa         Export rules Q&A pairs
GET    /export/{game_id}/outcome          Export win/loss outcome record
```

### 6.2 Response Conventions
- REQ-API01: All responses are JSON
- REQ-API02: Successful responses return HTTP 200 with a `data` key
- REQ-API03: Illegal actions return HTTP 422 with an `error` key
  containing a human-readable rules explanation and a machine-readable
  `error_code`
- REQ-API04: Unknown game IDs return HTTP 404
- REQ-API05: All game state objects include a `state_hash` field for
  deduplication

### 6.3 Legal Actions Response Schema
```json
{
  "priority_player": "player_1",
  "phase": "main_phase_1",
  "legal_actions": [
    {
      "action_type": "cast",
      "card_id": "abc123",
      "card_name": "Lightning Bolt",
      "valid_targets": ["player_2", "creature_id_456"],
      "mana_options": [{"R": 1}]
    },
    {
      "action_type": "pass",
      "description": "Pass priority"
    }
  ]
}
```

---

## 7. Training Data Export

### 7.1 Game State Snapshots
- REQ-D01: A snapshot is recorded at every point priority is granted
- REQ-D02: Each snapshot contains: full serialized game state,
  the legal actions available, and the action that was subsequently taken
- REQ-D03: Schema:
```json
{
  "game_id": "string",
  "snapshot_id": "string",
  "turn": "int",
  "phase": "string",
  "game_state": { ...full state object... },
  "legal_actions": [ ...action objects... ],
  "action_taken": { ...action object... },
  "action_taken_by": "player_1 | player_2"
}
```

### 7.2 Play-by-Play Transcript
- REQ-D04: One transcript per game, containing every action taken,
  every triggered ability that fired, every SBA applied, and every
  resolution event — in order
- REQ-D05: Each transcript entry includes: sequence number, event type,
  natural language description, and structured event data
- REQ-D06: Transcript is suitable for conversion into a Q&A training
  pair by a downstream generator

### 7.3 Rules Q&A Pairs
- REQ-D07: During play, when a complex rules interaction occurs
  (layer resolution, replacement effect choice, damage assignment,
  SBA application), the engine generates a Q&A record
- REQ-D08: Q&A schema:
```json
{
  "question": "string (natural language rules question)",
  "answer": "string (correct ruling with rule citation)",
  "game_id": "string",
  "turn": "int",
  "trigger_event": "string (what caused this Q&A to be generated)",
  "cards_involved": ["card names"],
  "rules_cited": ["CR rule numbers e.g. 613.1a"]
}
```
- REQ-D09: Q&A questions are templated from the actual game context
  (real card names, real board state), not generic

### 7.4 Win/Loss Outcome
- REQ-D10: One outcome record per game:
```json
{
  "game_id": "string",
  "winner": "player_1 | player_2 | draw",
  "win_condition": "life | mill | poison | concede | timeout",
  "total_turns": "int",
  "player_1_deck": ["card names"],
  "player_2_deck": ["card names"],
  "player_1_final_life": "int",
  "player_2_final_life": "int",
  "snapshot_count": "int",
  "transcript_length": "int"
}
```

---

## 8. Card Resolution

- REQ-C01: Card abilities are parsed from Scryfall oracle text into
  structured effect objects at game start (or on cache hit)
- REQ-C02: The ability parser handles: triggered abilities ("when",
  "whenever", "at"), activated abilities ("{cost}: effect"), static
  abilities (continuous effects), and spell effects
- REQ-C03: Cards not parseable by the ability parser are flagged with
  `parse_status: "unsupported"` and raise a non-fatal warning; the game
  continues without that card's ability
- REQ-C04: Scryfall responses are cached locally (SQLite or JSON file)
  to avoid repeated API calls for the same card
- REQ-C05: Engine supports double-faced cards, adventure cards,
  split cards, and modal double-faced cards as distinct card types with
  correct rules handling for each

---

## 9. Performance and Reliability

- REQ-P01: `GET /game/{game_id}/legal-actions` must respond in under
  200ms for any legal game state on the target hardware
- REQ-P02: Engine must handle at least 10 concurrent games without
  state bleed between games
- REQ-P03: All game state is stored in memory during play; a completed
  game is persisted to MongoDB before the DELETE response is returned
- REQ-P04: If a game action causes an unhandled exception, the engine
  returns HTTP 500 with the error details and preserves the game state
  at the last valid checkpoint
- REQ-P05: Engine supports a `dry_run` flag on action endpoints that
  validates legality and returns the projected next state without
  committing the action

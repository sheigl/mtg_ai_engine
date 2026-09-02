# Sprint B: High-Value Keywords Batch 2

## Overview
Implement high-value keyword abilities that are critical for Commander gameplay and common in competitive formats. This sprint covers Partner/Partner With (essential for Commander), existing modules with stub `apply()` methods (Ward, Scry, Equip), death-triggered keywords (Persist, Undying — if not already merged via Sprint A), and a large batch of additional high-value keywords.

**Note**: If Persist and/or Undying are successfully merged in Sprint A from the `sprint2/litellm-codebot` branch, stories SB-05/SB-06 become review-and-stabilize tasks rather than new implementations.

---

## User Stories

### SB-01: Partner / Partner With (CR 702.49)

**User Story**
As a Commander player, I want to be able to choose two commanders with Partner or Partner With abilities so that I can play Commander decks that require partner pairs.

**Context**
Partner is one of the most iconic Commander mechanics. CR 702.49 defines:
- **Partner**: "You may have two commanders if both have partner." Both start in the command zone.
- **Partner with [card name]**: Asymmetric pairing — only specific cards can be paired together.

The engine already has basic commander support (CMD-01): tax, damage tracking, zone replacement. However, it does not support choosing two commanders or validating Partner/Partner With compatibility.

**Acceptance Criteria**
- [ ] `mtg_engine/engine/formats/commander.py` gains `validate_partner(commanders)` function that checks:
  - [ ] Both commanders have "partner" keyword → valid pair
  - [ ] One commander has "partner with X" and the other's name matches X → valid pair
  - [ ] Neither has partner → single commander mode (existing behavior)
  - [ ] Mismatched "partner with" names → violation
- [ ] `GameState` gains support for two commanders per player (`commander_names: list[str]`)
- [ ] Commander tax tracking works independently per partner (each partner tracks its own cast count in `commander_cast_counts`)
- [ ] Commander damage tracking works independently per partner permanent ID (existing `commander_damage` dict already supports this)
- [ ] Deck validation enforces: if using partners, both commanders must be declared at game creation
- [ ] Game creation API accepts `"commanders": ["Card A", "Card B"]` for a player
- [ ] >= 6 tests covering: valid partner pair, valid partner-with pair, invalid mismatch, single commander still works, independent tax per partner, independent damage tracking

**Dependencies**: None (builds on existing CMD-01 infrastructure)

**Priority: High** — Critical for Commander format completeness

**Estimated Effort**: 3-4 hours

---

### SB-02: Ward `apply()` Implementation (CR 702.145)

**User Story**
As a player, I want Ward to trigger when my permanents are targeted by an opponent's spell or ability so that the targeting player must pay the Ward cost or have their spell countered.

**Context**
`mtg_engine/ability/keywords/ward.py` exists with detection/parsing (`has_ward()`, `from_oracle_text()`, `parse_ward_cost()`) but the `apply()` method is a stub that returns `game_state` unchanged. Ward needs to:
1. Trigger when a permanent with Ward becomes the target of an opponent's spell/ability
2. Counter that spell/ability unless its controller pays the Ward cost

**Acceptance Criteria**
- [ ] `Ward.apply(game_state, targeted_perm, source_controller)` implements full Ward logic:
  - [ ] Detects when a permanent with Ward is targeted by another player's spell/ability
  - [ ] For human players: queues `pending_ward_choice` on GameState with ward cost and target info
  - [ ] For AI players: auto-resolves — pays Ward cost if mana is available, otherwise lets the targeting spell counter
- [ ] Ward triggers via the existing trigger system (`check_becomes_target_triggers`) rather than requiring a new trigger category
- [ ] `GameState` gains `pending_ward_choice: Optional[dict] = None` field
- [ ] Legal actions include `ward_pay` and `ward_counter` when pending Ward choice is active for the priority holder
- [ ] Pure transform: returns new GameState via `model_copy(update={...})`
- [ ] >= 5 tests covering: ward triggers on targeting, human queues choice, AI pays when affordable, AI doesn't pay when unaffordable, pure transform

**Dependencies**: None (uses existing trigger system)

**Priority: High** — Ward is very common in modern sets

**Estimated Effort**: 2-3 hours

---

### SB-03: Scry `apply()` Implementation (CR 701.20)

**User Story**
As a player, I want scry effects to actually manipulate my library so that cards with scry abilities work during gameplay.

**Context**
`mtg_engine/ability/keywords/scry.py` exists with detection/parsing (`has_scry()`, `from_oracle_text()`, `parse_scry_value()`) but the `apply()` method is a stub. Scry N means: look at top N cards of library, put any number on bottom in any order, rest on top in any order.

**Acceptance Criteria**
- [ ] `Scry.apply(game_state, controller)` implements full scry logic:
  - [ ] For human players: queues `pending_scry_choice` with the N revealed cards for manual ordering
  - [ ] For AI players: auto-resolves using a heuristic (e.g., put lands on bottom when mana is sufficient, keep creatures/spells on top)
- [ ] `GameState` gains `pending_scry_choice: Optional[dict] = None` field containing revealed cards and player
- [ ] Legal actions include scry ordering choices (`scry_top`, `scry_bottom`) for each revealed card
- [ ] Library manipulation is atomic — cards are removed from library top, then placed back in chosen order
- [ ] Pure transform: returns new GameState via `model_copy(update={...})`
- [ ] >= 5 tests covering: scry 1, scry 2+, human queues choice, AI auto-resolves, pure transform

**Dependencies**: None (uses existing library manipulation in zones.py)

**Priority: High** — Scry is extremely common across all formats

**Estimated Effort**: 2-3 hours

---

### SB-04: Equip Activation Flow

**User Story**
As a player, I want to activate Equipment's equip ability during my main phase so that I can attach equipment to creatures.

**Context**
`mtg_engine/ability/keywords/equip.py` exists with detection/parsing (`has_equip()`, `from_oracle_text()`, `parse_equip_cost()`) but the `apply()` method is a stub. Equip is an activated ability that:
1. Can only be activated during sorcery timing (main phase, stack empty)
2. Targets a creature you control
3. Pays the equip cost
4. Detaches from current creature (if attached) and attaches to new target

The engine already has `activate` endpoint in the API but needs Equip-specific logic for validation and attachment.

**Acceptance Criteria**
- [ ] Equip activation is recognized as an activated ability in `_compute_legal_actions()`:
  - [ ] Only available during sorcery timing (main phase, stack empty)
  - [ ] Shows valid target creatures on battlefield controlled by the equipment's controller
- [ ] `Equip.apply(game_state, equipment_perm, target_creature_perm)` implements:
  - [ ] Mana payment from equip cost via existing mana pool deduction
  - [ ] Detach equipment from current creature (if any) — update `attached_to` field
  - [ ] Attach to new target creature — set `attached_to = target_perm.id`
  - [ ] Apply continuous effect: copy P/T bonuses from Equipment to attached creature via layer system
- [ ] Equipment's static ability ("+1/+1" etc.) is applied as a continuous effect on the attached creature
- [ ] Pure transform: returns new GameState via `model_copy(update={...})`
- [ ] >= 5 tests covering: equip activation legal action, equip to unattached creature, re-equip to different creature, mana payment, sorcery timing enforcement

**Dependencies**: None (uses existing activated ability infrastructure)

**Priority: High** — Equipment is fundamental to many archetypes

**Estimated Effort**: 3-4 hours

---

### SB-05: Persist Implementation (CR 702.86)

**User Story**
As a player, I want creatures with Persist to return from the graveyard as zombie tokens so that I can reuse my creatures after they die.

**Context**
Persist is a death-triggered keyword: "When this permanent dies, if it had no -1/-1 counters on it, return to battlefield under owner's control with a -1/-1 counter." May already exist from Sprint A merge — if so, this story becomes review-and-stabilize.

**Acceptance Criteria**
- [ ] `mtg_engine/ability/keywords/persist.py` exists with:
  - [ ] `has_persist()` detection method
  - [ ] `from_oracle_text()` parser
  - [ ] `apply(game_state, dead_perm)` that returns creature token to battlefield with -1/-1 counter
- [ ] Persist fires via death trigger system (`DEATH_TRIGGER_PATTERNS` in triggers.py)
- [ ] Only triggers if the dying permanent had NO -1/-1 counters at time of death
- [ ] Returned token is a copy of original (same name, P/T, keywords) with one -1/-1 counter
- [ ] Token obeys CR 704.5d: ceases to exist if it leaves battlefield again
- [ ] Pure transform: returns new GameState via `model_copy(update={...})`
- [ ] >= 4 tests covering: persist fires when no -1/-1 counters, persist does NOT fire with existing counter, token returned correctly, token dies permanently on second death

**Dependencies**: SB-01 (if Sprint A merge doesn't include Persist)

**Priority: Medium** — Common in EDH but less critical than Partner/Ward

**Estimated Effort**: 2-3 hours

---

### SB-06: Undying Implementation (CR 702.88)

**User Story**
As a player, I want creatures with Undying to return from the graveyard with +1/+1 counters so that my small creatures become threats after dying.

**Context**
Undying is a death-triggered keyword: "When this permanent dies, if it had no +1/+1 counters on it, return to battlefield under owner's control with N +1/+1 counters where N equals its power." May already exist from Sprint A merge — if so, this story becomes review-and-stabilize.

**Acceptance Criteria**
- [ ] `mtg_engine/ability/keywords/undying.py` exists with:
  - [ ] `has_undying()` detection method
  - [ ] `from_oracle_text()` parser
  - [ ] `apply(game_state, dead_perm)` that returns creature token to battlefield with N +1/+1 counters (N = original power)
- [ ] Undying fires via death trigger system (`DEATH_TRIGGER_PATTERNS` in triggers.py)
- [ ] Only triggers if the dying permanent had NO +1/+1 counters at time of death
- [ ] Returned token has power equal to original creature's power, with that many +1/+1 counters
- [ ] Pure transform: returns new GameState via `model_copy(update={...})`
- [ ] >= 4 tests covering: undying fires when no +1/+1 counters, undying does NOT fire with existing counter, correct number of counters returned, token created correctly

**Dependencies**: SB-01 (if Sprint A merge doesn't include Undying)

**Priority: Medium** — Common in EDH but less critical than Partner/Ward

**Estimated Effort**: 2-3 hours

---

### SB-07: Additional High-Value Keywords Batch

**User Story**
As a player, I want common MTG keywords to be implemented so that cards with these abilities work correctly during gameplay.

**Context**
The following keywords are frequently encountered in Commander and competitive formats but do not yet have dedicated modules. Each follows the same pattern as existing keyword modules: detection from oracle text + `apply()` implementing the mechanical effect.

**Keywords to implement**:

| Keyword | CR Reference | Type | Complexity |
|---------|-------------|------|------------|
| Affinity | 702.41 | Static cost reduction | Low |
| Amplify | 702.53 | ETB triggered ability | Medium |
| Bestow | 702.69 | Alternative casting / enchantment | High |
| Bloodthirst | 702.31 | Death-triggered on spell resolution | Medium |
| Champion | 702.28 | Activated ability, control change | Medium |
| Devour | 702.66 | Sacrifice creatures on cast | Medium |
| Entwine | 702.63 | Modal spell cost modification | Low-Medium |
| Exploit | 702.109 | Sacrifice creature on ETB | Medium |
| Fabricate | 702.78 | Choice: counters or tokens | Medium |
| Fading | 702.30 | Counter-based tap at upkeep | Medium |
| Graft | 702.57 | ETB counter placement on other permanents | Low-Medium |
| Mentor | 702.80 | Death trigger: put +1/+1 counters | Low |
| Outlast | 702.83 | Activated ability: put +1/+1 counter | Low |
| Rampage | 702.43 | Blocked-triggered counters and damage | Medium |
| Recover | 702.75 | Graveyard triggered ability | Medium |
| Renown | 702.81 | One-shot ETB trigger with ongoing effect | Low-Medium |
| Retrace | 702.48 | Graveyard casting cost reduction | Low |
| Riot | 702.135 | Conditional P/T boost on ETB | Low |
| Soulbond | 702.90 | Mandatory equipment attachment | Medium |
| Soulshift | 702.76 | Death trigger: return spirit from graveyard | Low-Medium |
| Splice | 702.46 | Put onto spell from hand for cost | High |
| Strive | 702.133 | Modal spell with scaling modes | Medium |
| Training | 702.128 | Tap creature to give +1/+1 counter | Low-Medium |
| Undaunted | 702.129 | Multiplayer cost reduction | Low (multiplayer-dependent) |

**Acceptance Criteria**
- [ ] Each keyword has a dedicated module in `mtg_engine/ability/keywords/{name}.py` with:
  - [ ] Detection method (`has_{keyword}()`)
  - [ ] Oracle text parser (`from_oracle_text()`, `parse_{keyword}_value()`)
  - [ ] `apply(game_state, ...)` implementing the mechanical effect via pure transform
- [ ] Keywords that trigger on game events are wired into the appropriate trigger check function in `triggers.py`
- [ ] Keywords that modify casting costs are integrated into the mana payment flow in `stack.py`
- [ ] Each keyword has >= 3 tests covering: detection, apply logic, edge cases
- [ ] All new keywords follow project coding standards (pure transforms, type hints, logging)

**Dependencies**: SB-01 through SB-06 (establish patterns for new keywords)

**Priority: Medium** — Important for completeness but individually lower impact than Partner/Ward/Scry

**Estimated Effort**: 24-36 hours (30 keywords × ~45 min each, with higher complexity for Bestow and Splice)

---

## Sprint B Dependencies Map

```
SB-01 (Partner) ────────────────┐
                                │
SB-02 (Ward)                    │
                                ├──→ SB-07 (Additional Keywords Batch)
SB-03 (Scry)                    │
                                │
SB-04 (Equip)                   │
                                │
SB-05 (Persist) ────────────────┘  (if not merged in Sprint A)
SB-06 (Undying) ─────────────────┘  (if not merged in Sprint A)
```

## Sprint B Summary

| # | Story | Priority | Effort | Dependencies |
|---|-------|----------|--------|--------------|
| SB-01 | Partner / Partner With | High | 3-4h | none |
| SB-02 | Ward apply() | High | 2-3h | none |
| SB-03 | Scry apply() | High | 2-3h | none |
| SB-04 | Equip activation flow | High | 3-4h | none |
| SB-05 | Persist | Medium | 2-3h | Sprint A (if not merged) |
| SB-06 | Undying | Medium | 2-3h | Sprint A (if not merged) |
| SB-07 | Additional keywords batch | Medium | 24-36h | SB-01..SB-06 |

**Total estimated effort**: 38-53 hours

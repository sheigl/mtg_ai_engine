# Sprint C: Missing Triggers, TODO Fixes, and Edge Cases

## Overview
Address incomplete trigger categories, fix documented TODOs in the codebase (checkland/fetchland ETB handling, recent_games stats placeholder, loyalty ability stub), and close out known gaps identified in the 038-gap-analysis. This sprint is about filling holes rather than building large new features.

---

## User Stories

### SC-01: Implement Missing Trigger Categories

**User Story**
As a player or card effect resolver, I want all trigger categories to fire correctly so that cards referencing these game events work as intended.

**Context**
The `mtg_engine/engine/triggers.py` module has 31 trigger check functions covering most common game events. However, the following trigger categories are missing entirely and need new check functions:

| Missing Trigger | CR Reference | Description |
|-----------------|-------------|-------------|
| abandoned | — | A player abandons a game object (e.g., planeswalker loyalty in some contexts) |
| flipped_coin | 704.5j | A coin flip result is used for an effect |
| ring_tempts_you | Un-sets / Commander Nights | Ring artifact tempts controller each upkeep |
| rolled_die | 704.5k | A die roll result is used for an effect |
| voted | — | Voting mechanic (rare, e.g., "vote" cards) |
| class_level_gained | D&D Adventures | Player gains a level in a character class |
| committed_crime | D&D Adventures | Player commits a crime action |
| mutates | 702.149 | A spell with Mutate resolves on top of/below another creature |

**Acceptance Criteria**
- [ ] Each missing trigger category has a corresponding `check_{trigger}_triggers(gs) -> GameState` function in `triggers.py`:
  - [ ] `check_abandoned_triggers(gs)` — fires "whenever {player} abandons {object}" triggers
  - [ ] `check_flipped_coin_triggers(gs, player_name, result)` — fires "whenever you flip a coin and it comes up heads/tails" triggers
  - [ ] `check_ring_tempts_you_triggers(gs)` — fires ring temptation triggers during upkeep
  - [ ] `check_rolled_die_triggers(gs, player_name, value)` — fires "whenever you roll a die" triggers
  - [ ] `check_voted_triggers(gs)` — fires voting-related triggers
  - [ ] `check_class_level_gained_triggers(gs)` — fires D&D level-up triggers
  - [ ] `check_committed_crime_triggers(gs)` — fires crime triggers
  - [ ] `check_mutates_triggers(gs)` — fires "whenever this creature mutates" triggers (CR 702.149)
- [ ] Each function follows the existing pattern: collect matching pending triggers → fire via stack resolution → return new GameState via `model_copy(update={"pending_triggers": ...})`
- [ ] Mutate trigger is wired into spell resolution in `stack.py` for mutate-compatible spells
- [ ] Coin flip and die roll triggers accept parameters (result/value) so cards can distinguish heads/tails or specific values
- [ ] >= 2 tests per new trigger function covering: fires when condition met, does not fire when condition unmet

**Dependencies**: None

**Priority: Medium** — Most are rare triggers; Mutate is the most impactful for modern Commander

**Estimated Effort**: 4-6 hours

---

### SC-02: Fix Checkland and Fetchland ETB Handling (game.py:2397)

**User Story**
As a player, I want checklands and fetchlands to present proper ETB choices so that these common lands work correctly during gameplay.

**Context**
`mtg_engine/api/routers/game.py` line 2397 has a TODO comment for checkland/fetchland ETB handling in `_compute_legal_actions()` (ref re-verified 2026-08-20; was 2354 pre-Sprint-7 insertions). The engine already supports shockland ETB choices (`etb_pay` / `etb_tapped`) but checklands and fetchlands have different mechanics:

- **Checkland** (e.g., "Tapestry of the Ages"): Enters tapped unless you control an Island or a Mountain. No player choice — purely conditional based on battlefield state.
- **Fetchland** (e.g., "Steam Vents" is actually a shockland; true fetchland: "Bloodstained Mire"): Sacrifice this land, search for a basic land, put onto battlefield, exile this land. Requires player to choose which basic land type to search for.

The existing `_detect_etb_choice()` in `zones.py` already classifies checklands and fetchlands via regex but the API layer doesn't expose proper legal actions or choice handlers.

**Acceptance Criteria**
- [ ] Checkland ETB: No player choice needed — engine auto-resolves by checking if controller has required land type on battlefield:
  - [ ] If condition met → enters untapped (set `perm.tapped = False`)
  - [ ] If condition not met → enters tapped (leave `perm.tapped = True`)
- [ ] Fetchland ETB: Player must choose a basic land type to search for:
  - [ ] Legal actions include `fetch_plains`, `fetch_island`, `fetch_swamp`, `fetch_mountain`, `fetch_forest` when pending fetchland choice is active
  - [ ] Choice handler in `/choice` endpoint resolves the fetch: exiles the land, searches local card data for matching basic land, puts onto battlefield
  - [ ] For AI player: auto-resolves using heuristic (e.g., choose land type matching most-needed mana color)
- [ ] `GameState.pending_etb_choice` is properly cleared after both checkland and fetchland resolve
- [ ] >= 4 tests covering: checkland enters untapped when condition met, checkland enters tapped when unmet, fetchland presents choice, fetchland resolves with chosen land type

**Dependencies**: None (builds on existing ETB infrastructure)

**Priority: High** — These are among the most common lands in Commander and Modern/Pioneer formats

**Estimated Effort**: 2-3 hours

---

### SC-03: Fix `recent_games` Stats Placeholder (player_stats.py:65)

**User Story**
As a player viewing my stats, I want to see my recent game history so that I can track my performance over time.

**Context**
`mtg_engine/api/routers/player_stats.py` line 65 has a TODO for `recent_games` — the field exists in the response model but returns an empty list. The MongoDB player stats collection stores win/loss records and ELO ratings, but does not yet store individual game results with timestamps and outcomes.

**Acceptance Criteria**
- [ ] PlayerStats model gains `recent_games: list[RecentGame]` field where `RecentGame` contains:
  - [ ] `game_id`: str — reference to the completed game
  - [ ] `opponent_name`: str — name of the opposing player
  - [ ] `result`: "win" | "loss" — outcome from this player's perspective
  - [ ] `timestamp`: float — when the game completed
  - [ ] `format`: str — game format (commander, standard, etc.)
- [ ] `update_stats_for_game_completion()` appends a new `RecentGame` entry to the winning and losing player's stats on each game completion
- [ ] Recent games list is capped at a configurable maximum (e.g., 20 most recent) to prevent unbounded growth
- [ ] `GET /stats/player/{name}` returns populated `recent_games` in the response
- [ ] >= 3 tests covering: recent game added on completion, list capped at max size, oldest entry removed when cap exceeded

**Dependencies**: None (builds on existing APP-06 stats infrastructure)

**Priority: Medium** — Nice-to-have for player experience; doesn't affect gameplay

**Estimated Effort**: 1-2 hours

---

### SC-04: Implement Loyalty Ability Activation

**User Story**
As a player, I want to activate loyalty abilities on my Planeswalkers so that planeswalker cards are functional during gameplay.

**Context**
Planeswalkers have loyalty abilities (CR 702.91) — activated abilities with `[+N]` or `[-N]` costs that modify the planeswalker's loyalty counter. The engine has a placeholder for loyalty ability handling but no actual implementation. Key mechanics:
- Can only activate one loyalty ability per planeswalker per turn
- Can only activate during sorcery timing (your main phase, stack empty)
- `[+N]` abilities add N loyalty counters; `[-N]` abilities remove N loyalty counters
- Planeswalker with 0 loyalty is put into graveyard as a state-based action

**Acceptance Criteria**
- [ ] Loyalty ability detection: parse `[+2]: Draw a card.` and `[-3]: Destroy target creature.` from oracle text
- [ ] `_compute_legal_actions()` includes loyalty ability activations when:
  - [ ] It's the controller's main phase with stack empty (sorcery timing)
  - [ ] The planeswalker has enough loyalty to pay negative costs
  - [ ] No other loyalty ability has been activated on this planeswalker this turn
- [ ] Loyalty ability activation handler in `/choice` endpoint:
  - [ ] Adds/removes appropriate number of loyalty counters via `add_counter(gs, perm_id, "loyalty", N)` or `remove_counter()`
  - [ ] Pushes the ability's effect text onto the stack for resolution
  - [ ] Marks the planeswalker as having used a loyalty ability this turn to prevent double-activation
- [ ] State-based action: planeswalker with 0 or fewer loyalty counters is moved to graveyard
- [ ] Planeswalker combat damage rules (CR 702.91a): opponent may target your planeswalker as though it were a creature during combat declaration
- [ ] >= 5 tests covering: positive loyalty ability, negative loyalty ability, cannot activate if insufficient loyalty, cannot activate twice per turn, 0 loyalty → graveyard

**Dependencies**: None (uses existing activated ability and counter infrastructure)

**Priority: High** — Planeswalkers are essential to many archetypes across all formats

**Estimated Effort**: 3-4 hours

---

### SC-05: Fix Known ETB Detection Regex Gaps

**User Story**
As a player, I want fetchland and snow dual land ETB choices to be correctly detected so that these lands present proper choices.

**Context**
The `tests/engine/test_etb_detection.py` file has 5 xfail tests for known regex issues:
- Fetchland detection fails for some oracle text patterns (e.g., "Bloodstained Mire" variant wordings)
- Snow dual land detection fails for newer snow land printings with slightly different wording

**Acceptance Criteria**
- [ ] `_detect_etb_choice()` in `zones.py` correctly detects all known fetchland variants:
  - [ ] "Search your library for a {type} card, reveal it, put it into your hand, then shuffle. Exile this land."
  - [ ] Variants with "put it onto the battlefield" instead of "put it into your hand" (double-fetched lands)
- [ ] `_detect_etb_choice()` correctly detects snow dual lands:
  - [ ] "As {name} enters, put a +1/+1 counter on target creature you control or prevent all damage that would be dealt to target creature you control this turn."
  - [ ] Variants with different effect text (e.g., "draw a card" instead of counters)
- [ ] All previously xfail tests in `test_etb_detection.py` now pass (convert from `@pytest.mark.xfail` to regular tests)
- [ ] >= 2 additional test cases per land type covering edge-case oracle text variations

**Dependencies**: SC-02 (shares the same ETB detection code path)

**Priority: Medium** — Improves reliability of existing ETB system

**Estimated Effort**: 1-2 hours

---

## Sprint C Dependencies Map

```
SC-01 (Missing Triggers) ────────────── independent
SC-02 (Checkland/Fetchland) ───┬─────── independent
                               │
SC-03 (recent_games stats)     │       independent
                               │
SC-04 (Loyalty Abilities)      │       independent
                               │
SC-05 (ETB Regex Fixes) ←──────┘    depends on SC-02 code path
```

## Sprint C Summary

| # | Story | Priority | Effort | Dependencies |
|---|-------|----------|--------|--------------|
| SC-01 | Missing trigger categories | Medium | 4-6h | none |
| SC-02 | Checkland/fetchland ETB fix | High | 2-3h | none |
| SC-03 | recent_games stats placeholder | Medium | 1-2h | none |
| SC-04 | Loyalty ability activation | High | 3-4h | none |
| SC-05 | ETB detection regex fixes | Medium | 1-2h | SC-02 |

**Total estimated effort**: 11-17 hours

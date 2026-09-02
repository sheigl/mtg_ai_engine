# Story: Wire 13 Dead-Code Trigger Check Functions into Engine Flow

## User Story
As an MTG engine developer, I want the 13 trigger check functions that already exist in triggers.py to be wired into their respective engine event flows, so that cards with these triggered abilities fire correctly instead of silently no-op'ing — turning dead code into working functionality.

## Context
The gap analysis (FORGE-GAP-ANALYSIS.md) revealed that ~13 trigger categories have regex patterns AND check functions in triggers.py, but are NOT called from anywhere in the engine's event flow. This is free functionality: the detection logic and PendingTrigger queuing code already exists, it just needs call sites wired into the appropriate engine modules.

### Comprehensive Rules Grounding
Each trigger type corresponds to a specific game event defined in the MTG Comprehensive Rules (CR):

| # | Trigger | CR Reference | Game Event | Example Card |
|---|---------|-------------|------------|--------------|
| 1 | **sacrifice** | [CR 701.19](https://mtg.fandom.com/wiki/Sacrifice) — "To sacrifice a permanent, its controller moves it from the battlefield directly to its owner's graveyard." | Permanent sacrificed | Zulaport Cutthroat ("whenever ~ attacks, sacrificing target creature") |
| 2 | **life_gain_lost** | [CR 701.12](https://mtg.fandom.com/wiki/Gain_Life) — "To gain life, add the indicated amount to your current life total." / [CR 701.13](https://mtg.fandom.com/wiki/Lose_Life) — "To lose life, subtract the indicated amount from your current life total." | Life gained or lost | Geth's Grimoire ("whenever a player gains or loses life") |
| 3 | **fight** | [CR 701.6](https://mtg.fandom.com/wiki/Fight) — "When creatures fight, each deals damage equal to its power to the other." | Creatures fight | Duress ("target creature fights target creature") |
| 4 | **transformed** | [CR 711.3](https://mtg.fandom.com/wiki/MDFC) — "A player may transform a permanent they control any time they have priority when that permanent is on the battlefield." | Permanent transforms (MDFC) | The Walking Ballista → The Siege-Gang Commander |
| 5 | **tutor (search library)** | [CR 400.8](https://mtg.fandom.com/wiki/Search) — "If an effect instructs a player to search for something in a hidden zone, that player looks at all cards in that zone." / [CR 400.9](https://mtg.fandom.com/wiki/Shuffle) — "Whenever a player searches a library, they shuffle it after finishing the search." | Library searched | Brainstorm ("search your library for a card") |
| 6 | **becomes_target** | [CR 109.3](https://mtg.fandom.com/wiki/Target) — "To target means to identify a legal object or player as the recipient of an action." | Permanent becomes a target | Spell Pierce ("whenever a spell targets you or a permanent you control") |
| 7 | **attach** | [CR 702.5](https://mtg.fandom.com/wiki/Equip) — "To attach Equipment to a creature, activate its equip ability." / [CR 702.54a](https://mtg.fandom.com/wiki/Fortify) — "Fortify is an activated mana cost that attaches Fortification to target land you control." | Aura/Equipment attaches | Sword of the Paruns ("whenever ~ becomes attached") |
| 8 | **mana_spent** | [CR 118.9](https://mtg.fandom.com/wiki/Mana_Pool) — "Spending mana means removing that mana from a player's pool as part of paying costs." | Mana spent from pool | Arcane Signet ("whenever you spend {W} or {U}") |
| 9 | **draw** | [CR 701.16](https://mtg.fandom.com/wiki/Draw_Card) — "To draw a card, a player reveals the top card of their library and puts it into their hand." | Card drawn | Drawn from a spell effect |
| 10 | **discard** | [CR 701.18](https://mtg.fandom.com/wiki/Discard) — "To discard a card, move it from its owner's hand to that player's graveyard." | Card discarded | Discard pile triggers |
| 11 | **token_created** | [CR 110.5](https://mtg.fandom.com/wiki/Token) — "A token is a marker used to represent any permanent on the battlefield that isn't represented by a card." / [CR 110.6](https://mtg.fandom.com/wiki/Token#Rules) — "Tokens follow the rules for permanents." | Token created on battlefield | Cloudgoat Ranger ("create a 1/1 white Bird creature token") |
| 12 | **counter_placed** | [CR 122.1](https://mtg.fandom.com/wiki/Counter) — "A counter is a marker placed on an object or player that modifies its characteristics and/or interacts with a number of abilities." | Counter placed/removed | +1/+1 counter triggers |
| 13 | **mana_production** | [CR 502.4](https://mtg.fandom.com/wiki/Tap) — "During the declare attackers step, the active player taps creatures that are attacking." / Mana abilities add mana to pool | Mana added to pool | Land tap for mana triggers |

The 13 dead-code triggers:
1. **sacrifice** (CR 701.19) — `check_sacrifice_triggers(gs, perm_ids, controller)` — needs call in zones.py when permanent sacrificed
2. **life_gain_lost** (CR 701.12/701.13) — `check_life_gain_lost_triggers(gs, player_name, amount)` — needs call in stack.py `_gain_life()` / `_lose_life()`
3. **fight** (CR 701.6) — `check_fight_triggers(gs, fighter_ids)` — needs call in stack.py `_apply_fight()`
4. **transformed** (CR 711.3) — `check_transformed_triggers(gs, perm_id)` — needs call in zones.py `_transform_mdfc()`
5. **tutor (search library)** (CR 400.8/400.9) — `check_tutor_triggers(gs, player_name)` — needs call wherever library search happens (stack.py effect patterns)
6. **becomes_target** (CR 109.3) — `check_becomes_target_triggers(gs, target_perm_id, source_controller)` — needs call in stack.py target validation
7. **attach** (CR 702.5/702.54a) — `check_attach_triggers(gs, aura_perm_id, attached_to_perm_id)` — needs call when equip/fortify attaches
8. **mana_spent** (CR 118.9) — `check_mana_spent_triggers(gs, player_name, mana_paid)` — needs call in mana.py payment flow
9. **draw** (CR 701.16) — `check_draw_triggers(gs, player_name, count)` — needs call in zones.py `draw_card()`
10. **discard** (CR 701.18) — `check_discard_triggers(gs, player_name, cards)` — needs call wherever discard happens (stack.py cycling, etc.)
11. **token_created** (CR 110.5/110.6) — `check_token_triggers(gs, controller, token_type)` — needs call in stack.py `_create_token_with_pt_and_keywords()`
12. **counter_placed** (CR 122.1) — `check_counter_triggers(gs, perm_id, counter_type, amount)` — needs call when counters placed/removed (stack.py effect patterns)
13. **mana_production** (CR 502.4) — `check_mana_production_triggers(gs, player_name, mana_added)` — needs call in mana.py tap-for-mana flow

## Acceptance Criteria

### Sacrifice Trigger Wiring (CR 701.19)
- [x] Call `check_sacrifice_triggers()` from zones.py's sacrifice path (when a permanent moves to graveyard via sacrifice action per CR 701.19)
- [x] Pass sacrificed perm IDs and controller name to the check function
- [x] Verify existing tests in `tests/engine/test_b1_missing_triggers.py` for sacrifice pass

### Life Gain/Lost Trigger Wiring
- [x] Call `check_life_gain_lost_triggers()` from stack.py's `_gain_life()` helper function
- [x] Call `check_life_gain_lost_triggers()` from stack.py's `_lose_life()` helper function
- [x] Pass player name and amount to the check function

### Fight Trigger Wiring
- [x] Call `check_fight_triggers()` from stack.py's `_apply_fight()` after damage is dealt
- [x] Pass both fighter perm IDs to the check function

### Transformed Trigger Wiring
- [x] Call `check_transformed_triggers()` from zones.py's `_transform_mdfc()` after permanent flips sides
- [x] Pass transformed perm ID to the check function

### Tutor (Search Library) Trigger Wiring
- [x] Call `check_tutor_triggers()` from stack.py wherever library search effects resolve (tutor patterns in `_apply_single_effect_text()`)
- [x] Also call from transmute resolution, delve graveyard search, and any other library search path

### Becomes Target Trigger Wiring
- [x] Call `check_becomes_target_triggers()` from stack.py's target validation flow when a spell/ability targets a permanent
- [x] Pass target perm ID and source controller to the check function

### Attach Trigger Wiring
- [x] Call `check_attach_triggers()` from equip resolution when equipment attaches to creature
- [x] Also call from fortify resolution (when that keyword is implemented)

### Mana Spent Trigger Wiring
- [x] Call `check_mana_spent_triggers()` from mana.py's `pay_cost()` function after mana is deducted from pool
- [x] Pass player name and mana symbols paid to the check function

### Draw Trigger Wiring
- [x] Call `check_draw_triggers()` from zones.py's `draw_card()` function after card moves from library to hand
- [x] Pass player name and draw count to the check function

### Discard Trigger Wiring
- [x] Call `check_discard_triggers()` from wherever cards are discarded (cycling, madness, forage, etc.)
- [x] Pass player name and discarded cards list to the check function

### Token Trigger Wiring
- [x] Call `check_token_triggers()` from stack.py's `_create_token_with_pt_and_keywords()` after token is created
- [x] Pass controller name and token type to the check function

### Counter Trigger Wiring
- [x] Call `check_counter_triggers()` from stack.py wherever counters are placed or removed via effect resolution
- [x] Pass perm ID, counter type, and amount to the check function

### Mana Production Trigger Wiring
- [x] Call `check_mana_production_triggers()` from mana.py's tap-for-mana flow after mana is added to pool
- [x] Pass player name and mana symbols produced to the check function

### Cross-cutting requirements
- [x] All wiring follows pure transform pattern: capture return value from check functions (`gs = check_xxx_triggers(gs, ...)`)
- [x] Full test suite passes: 2792+ regression tests, 0 failures (3 skipped + 13 xfailed expected)
- [x] Each wired trigger has at least 1 integration test verifying the trigger fires in its natural context (not just regex matching)

## Dependencies
- None (uses existing check functions; only adds call sites)

## Priority: High

## Estimated Effort: M (13 wiring points × ~0.2 day each = 2.5 days, plus tests)

## Notes
- **Sacrifice detection**: The key challenge is distinguishing sacrifice from other death events in zones.py. Reference how `_queue_death_triggers()` already handles this — the zone change event includes a `reason` field that can be "sacrifice", "destroy", etc. Add a parallel call to `check_sacrifice_triggers()` when reason="sacrifice".
- **Becomes target integration**: This requires hooking into the targeting validation flow in stack.py. When `_validate_targets()` checks if a target is valid, also check for "becomes target" triggers and queue them. The trigger should fire BEFORE the spell resolves (during target selection).
- **Mana spent vs mana production**: These are distinct events — mana_spent fires when mana leaves the pool (paying costs), mana_production fires when mana enters the pool (tapping lands). Both need separate wiring points in mana.py.
- **Counter trigger complexity**: Counters can be placed/removed from many different sources (effect resolution, ETB effects, combat damage with infect/deathtouch, etc.). The call site should be centralized — consider adding a helper function `_place_counter(gs, perm_id, counter_type, amount)` that both places the counter AND fires triggers.
- **Token trigger scope**: Only fire for actual token creation (not for cards entering as permanents). Check `is_token` flag on the created permanent before calling `check_token_triggers()`.

## Verification (Pipeline, 2026-08-19)

Status: **COMPLETE — all acceptance criteria met; Code Review approved (round 2); Test passed (round 2).**

- Regression baseline after fix: **2798 passed / 0 failed / 3 skipped / 13 xfailed** (skip+xfail set byte-identical to pre-existing ETB known-gap baseline).
- Targeted suites: test_trigger_wiring_integration.py 15/15 (NEW, natural-context), test_b1_missing_triggers.py 29/29, test_triggers_expanded.py 33/33, test_new_trigger_types.py 15/15, test_mana_trigger.py 12/12, test_scryfall.py 4/4 (now hermetic).
- scryfall hermeticity verified: in-test monkeypatch of `ScryfallClient._api_get` (canned payload); `tests/conftest.py` and `mtg_engine/card_data/scryfall.py` unchanged; proven with broken-proxy run.
- All 15 natural-context integration tests confirmed to drive real engine entry points with meaningful state + trigger assertions.

### Known Gaps (non-blocking → follow-up backlog 7-17; code refs re-verified 2026-08-20 post-7-3)
1. **CR 903.9 commander replacement bypass**: `_sacrifice_permanent` (zones.py:826) sends a commander straight to graveyard; old Emerge path offered command-zone redirect. Sacrificed commanders (Emerge/Fading) can no longer go to command zone. Suggested: add CR 903.9 redirect branch to `_sacrifice_permanent` (human pending-choice vs AI auto-redirect) or document as accepted gap.
2. **Unattach path latent**: `check_attach_triggers(attach_event="unattach")` has no call site. When wiring, capture the aura's controller BEFORE it leaves the battlefield — the `attached_controller` lookup (triggers.py:1125) would otherwise return "" and the "you control" filter could never match.
3. **Multi-token creation under-fires**: `check_token_triggers` called once after the token-creation loop (stack.py:1341/2097/2133, effects/base.py:288, loyalty.py:235). CR 110.6 expects one "token created" trigger per token. Fix: fire per-token.
4. **Missing negative unit test**: no test pins "a creature you control is sacrificed" NOT firing when an *opponent's* creature is sacrificed (sac.controller ≠ watcher.controller). Positive + any-player cases are covered.
5. **Coverage gaps (integration)**: the cycling API endpoint route (game.py:968) and the Fading counter-removed upkeep route (turn_manager.py:~207-232) have no natural-context tests (underlying discard/draw helpers are covered, but not those exact routes).

### Deferred (pre-existing, out of 7-2 scope)
- Saga sacrifice dead scheduled trigger `sacrifice_saga:{perm.id}` (turn_manager.py:279) — no resolver exists.
- `mana_spent` does not fire for non-cast payments (kicker/buyback/replicate/activated abilities).
- Cycling endpoint does not deduct the cycle cost from the mana pool (pre-existing, documented game.py ~1001).
- `pending_triggers` list is a shallow copy under `model_copy` (established pattern; deep-copy pass is a future task).

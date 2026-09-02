# mtg_ai_engine Architecture Details

## Core Engine Modules
- `mtg_engine/engine/zones.py` — Zone management, `put_permanent_onto_battlefield`, `_detect_etb_choice`, `_resolve_etb_choice_with_ai`, `draw_card()` (pure transform), `_sacrifice_permanent()` (centralized helper with trigger wiring)
- `mtg_engine/engine/stack.py` — Spell resolution, effect application, trigger dispatch (`resolve_top()`), pure transform helpers (`_update_player_life`, `_update_battlefield`, etc.), `_apply_equip()`, `_draw_cards()` (pure transform)
- `mtg_engine/engine/triggers.py` — Trigger queuing system, zone-change listeners, `_queue_death_triggers()` for afterlife/undying/persist
- `mtg_engine/engine/turn_manager.py` — Phase/step advancement, upkeep/end-step hooks (suspend time counters, evoke sacrifice)
- `mtg_engine/engine/combat/core.py` — Combat declaration and damage assignment
- `mtg_engine/models/game.py` — Pydantic models: GameState, Card, Permanent, PlayerState, StackObject, PendingTrigger, etc.
- `mtg_engine/api/routers/game.py` — FastAPI endpoints: game lifecycle, actions, choices, legal actions

## Pure Transform Rules (Enforced 2026-07-24)

### Critical: All engine functions MUST return new GameState via model_copy
- **NEVER mutate** `player.library`, `player.hand`, `player.graveyard`, `game_state.battlefield` directly
- Use slice-based extraction for list operations: `card = player.library[0]; new_lib = list(player.library[1:])`
- **ALWAYS capture return values**: `gs = draw_card(gs, player)` — ignoring returns discards all changes
- Functions that call other pure transforms must propagate the returned GameState up the chain

### Common Anti-Patterns (Fixed)
1. `player.library.pop(0)` → mutates original list; use slice instead
2. `_execute_loyalty_effect(gs, ...)` returning `None` → discards all nested changes; must return `GameState`
3. Stale player references in tests: `alice = gs.players[0]; gs = foo(gs); assert alice.hand` → check `gs.players[0].hand` instead

## Keyword Module Architecture (Sprint 7 P0)

### Directory Structure
```
mtg_engine/ability/keywords/
├── base.py              # KeywordAbility ABC + PassiveKeyword, TriggeredKeyword, CostKeyword subclasses
├── afterlife.py         # AfterlifeKeyword — death trigger resolution
├── undying.py           # UndyingKeyword — death trigger resolution  
├── persist.py           # PersistKeyword — death trigger resolution
├── evoke.py             # EvokeKeyword — ETB sacrifice queue/resolve
├── morph.py             # MorphKeyword — face-up turn logic
├── suspend.py           # SuspendKeyword — time counter management
├── fortify.py           # Fortify(CostKeyword) — CR 702.54a Fortification attach
└── ... (other keywords)
```

### Keyword Module Patterns

#### Triggered Keywords (Afterlife, Undying, Persist)
- **Queuing**: Handled by `triggers.py:_queue_death_triggers()` via zone-change listeners. Creates `PendingTrigger` objects using keyword module's `create_trigger()` method.
- **Stack dispatch**: `stack.py:resolve_top()` checks `stack_obj.trigger_type` and delegates to keyword module's `resolve_trigger(gs, stack_obj)` function.
- **Resolution**: Keyword module's `resolve_trigger()` performs the effect (token creation, graveyard→battlefield return). Pure transform via `model_copy`.

```python
# Pattern: Triggered keyword resolution in stack.py
trigger_type = getattr(stack_obj, "trigger_type", None)
if trigger_type == "afterlife":
    from mtg_engine.ability.keywords.afterlife import resolve_trigger as _resolve_afterlife
    return _resolve_afterlife(game_state, stack_obj)

# Pattern: Module-level convenience function in afterlife.py
def resolve_trigger(game_state: GameState, stack_obj: StackObject) -> GameState:
    trigger_data = getattr(stack_obj, "trigger_data", {}) or {}
    count = trigger_data.get("count", 1)
    kw = AfterlifeKeyword(count=count)
    return kw.resolve_trigger(game_state, stack_obj.controller, count)
```

#### Queue/Resolve Keywords (Evoke)
- **Queue**: Called from `stack.py` after ETB placement when spell was cast via alternative cost. Sets `GameState.pending_<keyword>_sacrifice`.
- **Resolve**: Called from `turn_manager.py` at end step. Executes the effect and clears pending state.
- **Module-level wrappers** in both keyword module AND engine wrapper file for backward compatibility.

```python
# Pattern: Evoke queue/resolve in keyword module
def apply(self, game_state, permanent=None, mode="queue", **kwargs) -> GameState:
    if mode == "queue":
        return self._queue_sacrifice(game_state, permanent, kwargs)
    elif mode == "resolve":
        return self._resolve_sacrifice(game_state)

# Pattern: Engine wrapper file (engine/evoke.py) — thin delegate
def queue_evoke_sacrifice(gs, perm_id, player_name, card_name) -> GameState:
    from mtg_engine.ability.keywords.evoke import queue_sacrifice as _qs
    return _qs(gs, perm_id, player_name, card_name)
```

#### Player Action Keywords (Morph)
- **Action**: Called from API router when player chooses to turn face-down creature face up.
- **No stack involvement**: Doesn't use the stack; instant speed action.
- **Mana payment**: Deducts from controller's mana pool as part of the action.

```python
# Pattern: Morph face-up in keyword module
def turn_face_up(self, game_state, permanent_id, mana_payment=None) -> GameState:
    perm = find_permanent(game_state, permanent_id)
    if not perm.is_face_down: return game_state  # No-op
    cost = parse_morph_cost(perm.card.oracle_text or "")
    player = get_player(game_state, perm.controller)
    new_pool = pay_cost(player.mana_pool, cost, payment)
    new_perm = perm.model_copy(update={"is_face_down": False})
    battlefield = [p if p.id != permanent_id else new_perm for p in gs.battlefield]
    return game_state.model_copy(update={...})
```

#### Cost Keywords (Fortify, CR 702.54a)
- **Parser**: `ability_parser.py` `_FORTIFY_RE` matches `Fortify {cost} (...)` segments → `ActivatedAbility(cost=..., effect="Attach this Fortification to target land you control", timing_restriction="(Fortify only as a sorcery...)")`. **Regex pitfall**: the brace group must be `((?:\{[^{}]*\}\s*)+)` — putting the opening `\{` outside the repeated group captures only the first `{X}` chunk (multi-symbol costs like `{2}{G}` would truncate). `_FORTIFY_RE` lives at `ability_parser.py:144` (branch at :516, before the keyword fall-through); `_TIMING_RE` was extended with `fortify` at :136 so "(Fortify only as a sorcery.)" is stripped and the clause parses as an ActivatedAbility rather than a bogus KeywordAbility.
- **Attach**: `stack.py:_apply_fortify(gs, fortification_id, land_id)` — pure transform; sets `attached_to` on the Fortification, appends to host's `attachments`, fires `check_attach_triggers` (exactly-once per attach).
- **SBA**: `sba.py` `check_and_apply_sbas` — a Fortification whose `attached_to` target is missing or no longer a land detaches (stays on battlefield, CR 301.7); clears stale `attachments`; emits `fortification_detach` event. Complements `zones.py` cleanup (which handles the attached permanent leaving, not the host). QA added a TEST-ONLY coverage file `tests/engine/test_fortify_sba_host_becomes_nonland.py` exercising the branch where the host survives but becomes non-land (`sba.py:309-315`); production untouched.
- **API**: `/activate` Fortify branch (after regen block, non-mana path) — client passes explicit `mana_payment` dict (e.g. `{"C": 3}` or `{"G": 1, "C": 2}`); endpoint's shared cost machinery pays it BEFORE the branch. Target validation (land type, controller, not-self) lives in the branch. `_compute_legal_actions` offers `activate` with `valid_targets=[land perm ids]`.
- **Land rule**: Fortifications are lands — `Fortify.is_land_card(card)` (type_line check) is used in `play_land` and land-play legal actions, so one-land-per-turn applies.
- **AI**: `resolve_fortify_with_ai(gs, perm_id)` auto-attaches to first valid land if cost affordable.

#### Upkeep Keywords (Suspend)
- **Time counter removal**: Called from `turn_manager.py` at beginning of upkeep. Decrements counters, marks ready cards.
- **Auto-cast**: Stays in turn_manager.py — calls `cast_spell()` for ready cards. This is a general engine operation.

```python
# Pattern: Suspend time counter management in keyword module
def remove_time_counter(self, game_state, player_name) -> GameState:
    player = get_player(game_state, player_name)
    new_suspended = []
    ready_cards = []
    for card in player.suspended_cards:
        status = card.parse_status or ""
        if status.startswith("suspended:"):
            remaining = int(status.split(":")[1]) - 1
            if remaining <= 0:
                ready_cards.append(card.model_copy(update={"parse_status": "suspend_ready"}))
            else:
                new_suspended.append(card.model_copy(update={"parse_status": f"suspended:{remaining}"}))
    # Update player state...
    return game_state.model_copy(update={...})

# Pattern: Turn manager upkeep — calls keyword module + handles auto-cast
gs = suspend.remove_time_counter(gs, active_player)
for card in get_ready_cards(gs, active_player):
    gs = cast_spell(gs, active_player, card.id, from_suspended=True)
```

## Key Patterns for ETB Choices
- Detection: `_detect_etb_choice(oracle_text: str) -> ETBChoice | None` uses regex to classify 4 land types
- AI Resolution: `_resolve_etb_choice_with_ai(gs, player, choice, perm_id, name) -> (gs, should_be_tapped)`
- Human Path: `put_permanent_onto_battlefield` sets `game_state.pending_etb_choice` and `tapped=True`
- API Resolution: `choice_id="etb_pay"` subtracts life and sets `perm.tapped=False`; `choice_id="etb_tapped"` clears pending choice

## Key Patterns for Commander Zone Replacement (CMD-01)
- Detection: `move_card_to_zone` checks `_is_commander(card.name, player)` before applying CR 903.9
- Human Path: Sets `game_state.pending_commander_zone_choice`; AI auto-redirects to command zone
- API Resolution: `choice_id="commander_zone_replace"` or `choice_id="commander_zone_stay"`

## Key Patterns for Monarch (MON-01)
- Game Initialization: `game_manager.py` sets `monarch=active_player` for commander/conspiracy formats
- Combat Hook: `combat/core.py` calls `check_combat_damage_monarch(gs, target_player, attacker_controller)`
- End Step Hook: `turn_manager.py` calls `handle_end_step_draw(gs)` at end step

## Key Patterns for Toxic (KW-06)
- Combat Hook: `combat/core.py assign_combat_damage()` "Target is a player" branch calls module-level `apply_toxic(gs, source, player.name)` gated on `_has_keyword(source, "toxic") and assign.damage > 0` (fires once per damage assignment, regardless of amount — CR 702.134a)
- Pure transform: `ToxicKeyword.apply_toxic()` (and the module-level `apply_toxic()` in `ability/keywords/toxic.py`) rebuild the players list via `player.model_copy(update={"poison_counters": ...})`; no-op paths (unknown player, value <= 0) return the SAME object
- Loss at 10+ poison counters (CR 704.5c) is NOT in toxic.py — it is the EXISTING SBA check in `engine/sba.py _check_once()` (`p.poison_counters >= 10 → has_lost = True`)
- Non-combat damage (stack.py `_deal_damage`) does NOT call apply_toxic — only the combat damage flow does
- `ToxicKeyword.apply()` remains a thin no-op (real logic lives in `apply_toxic`, driven by combat)

## Key Patterns for Ward (CR 702.145a)
- **Two firing paths**: (1) SPELL path — `stack.py cast_spell` becomes-target loop calls `apply_ward(gs, target_perm, target=stack_obj, caster_name)` (stack exists; the AI-counter path removes the StackObject + graves the source card); (2) ABILITY path — `api/routers/game.py /activate` calls `apply_ward_to_ability(gs, target_perm, caster_name=priority_holder)` after tap+mana cost payment (activated abilities resolve inline with NO StackObject, so the resolver cannot touch the stack).
- **Ability-path outcome contract**: `apply_ward_to_ability` returns `tuple[GameState, str]` with `"proceed"` / `"countered"` / `"deferred"`; the ROUTER decides (skip effect / defer effect / apply effect) — no-op guards return the SAME state object (Q4).
- **Deferred activation**: for a human targeter the pending dict is tagged `targeting_type="ability"` + `targeting_spell_id=""` + deferred keys (`permanent_id`, `ability_index`, `targets`, `mana_payment`, `ability_text`); `ward_pay` re-drives the effect through the shared `_apply_activated_ability_effect()` helper (reconstructed `ActivateRequest`); `ward_counter` just clears the pending choice (nothing was ever on the stack). Spell-path pending dicts have no `targeting_type` key (or `"spell"`) and keep the old behavior.
- **Shared effect helper**: `_apply_activated_ability_effect(gs, perm, ability, req, player)` in `game.py` holds the CR 605 mana / T128 regen / Fortify handler block used by both the `/activate` proceed path and `ward_pay` — single source of truth for what an activated ability does once Ward is satisfied.
- **Activation cost is consumed regardless**: tap + mana are paid BEFORE Ward fires ("as an additional cost to activate"); a countered ability still costs.
- **Detection**: `Ward.has_ward(keyword_list)` on the target permanent (keyword list, not oracle text — no "award"/"reward" false positives); cost from `Ward.parse_ward_cost(oracle_text)`.
- **Payment**: the TARGETER (ability controller) pays from their own pool (CR 702.145a), same as the spell path; self-targeting never triggers Ward (CR 702.145b); no `pass` is ever offered as a legal action for a pending ward.
- **No model change**: `pending_ward_payment: Optional[dict]` (models/game.py:363) is extended in place with the ability keys.

## Key Patterns for Venture/Dungeon (VEN-01)
- Engine: `engine/dungeon.py` — `venture()`, `start_dungeon()`, `_apply_room_effect()`
- Stack Integration: "venture into the dungeon" regex in effect resolution patterns
- Initiative Hook: `engine/initiative.py` calls `venture(gs, player_name, dungeon_name="Undercity")`

## Trigger System Architecture

### Trigger Queuing Flow
1. **Event occurs** in engine code (e.g., permanent dies, player gains life)
2. **Check function called**: `check_<type>_triggers(gs, ...)` iterates battlefield permanents looking for matching trigger abilities
3. **Regex pattern match**: Each check function uses regex to find relevant oracle text patterns
4. **Controller filtering**: Guards ensure "you" patterns only fire for the correct player
5. **Self-referential guards**: "Whenever this creature..." only fires for the specific permanent
6. **PendingTrigger created**: For each matching ability, a `PendingTrigger` is appended to `game_state.pending_triggers`
7. **Pure transform returned**: New GameState via `model_copy(update={"pending_triggers": [...]})`

### Trigger Check Functions (triggers.py:500-2082 — 25 total)
The 15 listed below were the 7-2 wiring backlog (13) plus the 7-3 additions (countered, investigated); all are now wired into the engine event flow. All 25 check functions are pure transforms (line ranges re-verified 2026-08-20 post-7-3):

| Function | Line Range | Regex Pattern | Controller Filter | Self-Ref Guard |
|---|---|---|---|---|
| `check_sacrifice_triggers` | ~706-823 | "whenever.*sacrificed" / "whenever you sacrifice" | Yes (index 0) | Yes ("this creature") |
| `check_life_gain_lost_triggers` | ~824-875 | "whenever you gain/lose life" / "whenever [player] gains/loses life" | Yes (index 0) | Gain/Loss filter by amount sign |
| `check_fight_triggers` | ~876-914 | "whenever.*fights" / "whenever this creature fights" | Yes | Yes ("this creature") |
| `check_transformed_triggers` | ~953-991 | "whenever.*transforms" / "whenever this transforms" | Yes | Yes ("this") |
| `check_tutor_triggers` | ~992-1029 | "whenever you search" / "whenever [player] searches" | Yes | N/A |
| `check_becomes_target_triggers` | ~1030-1091 | "whenever.*becomes the target" / "whenever this becomes" | Yes (target_perm_id filter) | Yes ("this"/"~"), controller check for broad patterns |
| `check_attach_triggers` | ~1092-1186 | "whenever.*becomes attached" / "whenever this becomes attached"; also fires on `attach_event="unattach"` (see 7-17) | Yes (attach self-guard; unattach "you control") | Yes ("this") |
| `check_mana_spent_triggers` | ~1259-1298 | "whenever you spend mana" / "whenever [player] spends" | Yes | N/A |
| `check_draw_triggers` | ~1299-1336 | "whenever you draw a card" / "whenever [player] draws" | Yes | N/A |
| `check_discard_triggers` | ~1337-1374 | "whenever you discard" / "whenever [player] discards" | Yes | N/A |
| `check_token_triggers` | ~1375-1412 | "whenever a token enters" / "whenever you create a token" | Yes | N/A |
| `check_counter_triggers` | ~1413-1477 | "whenever.*counter is placed on" / "whenever a counter is placed on this" | Yes | Yes ("this") |
| `check_countered_triggers` | ~1478-1547 | "whenever this is countered" / "a spell you control is countered" / "a spell is countered" | Yes (idx1 explicit you-control) | Yes (idx0 name-guard: countered spell name == perm card name) |
| `check_investigated_triggers` | ~1548-1611 | "whenever you investigate" / "a player investigate(s)" (action-based only; token-ETB phrasings are owned by `check_token_triggers`) | Yes (index 0) | N/A (action-based) |
| `check_mana_production_triggers` | ~1657-1736 | "whenever [land] produces mana" / "whenever you produce {X}" | N/A (source-based) | N/A |

> Note: the `check_countered_triggers` "you control" variant sits at pattern index 1 (not 0), so it is filtered explicitly (`perm.controller != countered.controller`) rather than via `_is_you_pattern` (which is index-0 keyed).

### Trigger Wiring Map (post-7-2/7-3; all lines verified 2026-08-20)
Call sites use function-local aliased imports (`from mtg_engine.engine.triggers import check_X_triggers as _check_X`), so grep the **import line** to locate a wiring site.

#### stack.py — Primary Hub (18 import sites: 16 wired in 7-2 + 2 in 7-3)
- `cast_spell()` (def 114): mana_spent (import 227, after `pay_cost()` with `if mana_payment:` guard) + becomes_target (import 341, after target validation)
- `resolve_top()` (def 578): attach (import 689, after aura attaches)
- `_draw_cards()` (def 1196): draw (import 1234)
- `_create_tokens()` (def 1312): token (import 1341)
- `_investigate()` (def 1346): investigated (import 1385) — see 7-3 section below
- `_gain_life()` (def 1391) / `_lose_life()` (def 1406): life_gain_lost (imports 1401 / 1416)
- `_discard_cards()` (def 1421): discard (import 1440)
- `_tutor()` (def 1445) / `_tutor_to_top()` (def 1473): tutor (imports 1468 / 1492)
- `_apply_fight()` (def 1514): fight (import 1560)
- `_apply_equip()` (def 1565): attach (import 1599)
- `_add_counters()` (def 1615) / `_place_counter_on_permanent()` (def 1639): counter placed (imports 1634 / 1662)
- `_counter_spell()` (def 1800): countered (import 1815, 7-3)
- `_create_token_with_keywords()` (def 2074): token (import 2097)
- `_create_token_with_pt_and_keywords()` (def 2102): token (import 2133)

#### Other engine files
- zones.py: `draw_card()` (def 774) draw (import 821); `_sacrifice_permanent()` (def 826) sacrifice (import 908, CR 704.5d token guard); unattach call site in `move_permanent_to_zone` — fires `check_attach_triggers(..., attach_event="unattach", attached_controller=controller)` BEFORE the aura is removed when an attached permanent leaves the battlefield; controller captured pre-removal (`zones.py:225`) so "you control" trigger fires for the aura's ORIGINAL controller
- mana.py: `resolve_land_mana_ability()` (def 457) mana_production (import 534); `resolve_mana_ability()` (def 749) NOT wired (known limitation)
- daynight.py: transformed on both day/night transition paths (imports 38 / 51); `_transform_daybound_permanents()` def 58
- turn_manager.py: day_night_change (import 161, call 162); counter removed on Fading (import 224); sacrifice on Fading (import 230)
- combat/core.py: damage (import 608, call 609); events.py: phase (import 482, call 483) + damage (import 491, call 503) legacy path
- ability/effects/base.py (import 288) + ability/loyalty.py (import 235): token (2 of the 5 token sites)
- api/routers/game.py: discard on cycling route (import 1010), cycle (import 1020, call 1021), proliferated (import 1121, call 1143), sacrifice on API sacrifice action (imports 735, call 736)
- ability/keywords/evoke.py: sacrifice via centralized helper (import 184)

#### Sprint 7 P0 (7-3) — Countered + Investigated
- **Countered (CR 701.5)**: `stack.py:_counter_spell()` (~line 1800) — fires `check_countered_triggers` AFTER the `uncounterable` guard and BEFORE the spell is removed from the stack (so self-referential triggers can read the source card). A counter does NOT emit a zone-change event, so the trigger cannot double-fire.
- **Investigated (CR 701.32) + investigate action**: `stack.py:_investigate()` (1346-1388) — performs the investigate action (inspect top of library: land→reveal & move to hand; non-land→bottom of library), creates a 1/1 red Goblin "investigate" token, then fires `check_investigated_triggers` (1385-1386). Invoked via the `\binvestigate\b` pattern in BOTH `_apply_single_effect_text()` (pattern 966-967, triggered-ability effects) and `_apply_spell_effect()` (pattern 1144-1145, main spell resolution; parenthetical reminder text is stripped first at 1005-1013 per CR 201.8 so reminder text cannot shadow the match).
- **Token color identity**: `_create_token_with_pt_and_keywords()` gained an optional `colors` param (backward compatible) so the investigate token carries `["R"]`.

### Sacrifice Paths (post-7-2; centralized helper `zones._sacrifice_permanent`, def 826)
1. **Evoke**: `ability/keywords/evoke.py` routes through the helper (import 184)
2. **Fading upkeep**: `turn_manager.py` (import 230; block ~207-232; counter-removed trigger fires first at import 224)
3. **API sacrifice action (Emerge)**: `api/routers/game.py` (import 735, call 736)
4. **SBA legend rule — NOT routed** (`sba.py:237-249`): own event + removal, no sacrifice trigger fires (known limitation)
5. **Saga final chapter — DEAD scheduled trigger** (`turn_manager.py:272-282`): schedules a `sacrifice_saga:{id}` delayed trigger (line 279) but no consumer performs the sacrifice — deferred, see pipeline `status.md` Known Gaps

> **Commander on sacrifice (CR 903.9)**: When the sacrificed permanent is a commander (via CMD-01 helpers), the human path queues `pending_commander_zone_choice` (`intended_destination="graveyard"`) and does NOT complete the move until the player chooses replace/redirect-to-command-zone; the AI path auto-redirs to the command zone via `_cmd_move_to_command_zone`. This mirrors the CMD-01 commander-zone replacement pattern. For a human commander, `check_sacrifice_triggers` is deferred until the choice resolves (the CR 903.9 replacement isn't final yet). Only a handful of MTG cards pair sacrifice-with-graveyard with a commander.

### Token Creation Functions in stack.py
Only 3 of ~24 token functions actually create tokens (the rest are stubs that log "TODO" or return early):
- `_create_tokens()` (def 1312) — Basic token creation
- `_create_token_with_keywords()` (def 2074) — Token with keyword abilities
- `_create_token_with_pt_and_keywords()` (def 2102) — Token with P/T and keywords (+ optional `colors` param added in 7-3)

All 5 token-creation sites fire `check_token_triggers` (wired 7-2; per-token firing for CR 110.6 added in story 7-17): the 3 in stack.py above + `ability/effects/base.py` (import 288) + `ability/loyalty.py` (import 235). In the loop-based sites (`_create_tokens`, `CreateTokenEffect.resolve`) the trigger is fired INSIDE the token loop, so a "whenever you create a token" ability emits exactly one trigger PER token created.

### Mana Spent Trigger Scoping
**Wired (7-2)**: `stack.py:227` — `cast_spell()` main path after `pay_cost()` (guarded by `if mana_payment:`; 0-cost casts suppressed).
**NOT fired for non-cast payments** (known limitation, deferred): morph face-up (`morph.py` `turn_face_up`, def 109 method / 204 module-level) and kicker/buyback/replicate/activated-cost payments.

**API router call sites that must NOT fire triggers**:
- All `can_pay_cost()` calls in legal actions computation (checking affordability, not actual spending)
- These are read-only queries with no GameState mutation

## Known Gaps (Documented in Code)
- `_compute_legal_actions` only fully implements shockland ETB choices. Checkland/fetchland/snow_dual have TODO comments.
- Snow dual AI heuristic subtracts life instead of snow mana (placeholder).
- Fetchland AI heuristic does not actually exile land from graveyard.

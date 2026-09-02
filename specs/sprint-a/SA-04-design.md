# Design: SA-04 — Wire 17 Merged Keywords into Stack Resolution + Legal Actions

## Overview
Implement real `apply()` logic for 17 keyword modules that currently have detection/parsing but stub no-ops. Split into two batches: Batch 1 covers the 5 highest-impact keywords with full integration; Batch 2 covers the remaining 12 with simpler implementations.

## User Story Reference
SA-04: Wire 17 merged keywords (commit 7363140) into the game engine.

## Architecture Decisions

1. **Reuse existing patterns**: Follow the established KW-16..30 pattern (Kicker, Flashback, Escape, Dash, Ninjutsu) — pending choice fields on GameState for human players, auto-resolve for AI, pure `model_copy` transforms.
2. **Wire into existing hooks where possible**: Persist/Undying/Afterlife hook into the death trigger system already in `triggers.py`. Morph reuses the existing `pending_morph_payment` field and `as_face_down=True` cast path. Suspend reuses the existing `suspended_cards` list and upkeep decrement in `turn_manager.py`.
3. **Two-batch approach**: Batch 1 (top 5) gets full legal actions + choice handlers + AI auto-resolution. Batch 2 (remaining 12) gets working `apply()` methods that integrate into the stack/ETB/death/activated-ability systems with minimal API surface.
4. **No new GameState fields for Batch 2 keywords that reuse existing infrastructure**: Bloodthirst (ETB counters), Sunburst (ETB counters), Replicate/Buyback (already have StackObject fields), Surge (cost modification).

---

## Priority Order: Top 5 Keywords (Batch 1)

### Rationale for Priority Selection

| # | Keyword | CR | Game Impact | Why Prioritize |
|---|---------|-----|-------------|----------------|
| 1 | **Persist** | 702.61 | Extremely High | Defines Modern Jund/Abzan archetypes. Kitchen Finks, Geralf's Messenger, persist combos. `create_trigger()` already implemented — just needs wiring. |
| 2 | **Undying** | 702.51 | Extremely High | Defines Green aggressive strategies. Young Wolf, Strangleroot Geist, Mikaeus combos. Mirror of Persist — same wiring needed. |
| 3 | **Morph** | 702.36 | High | Defines entire blocks (Khans of Tarkir, Onslaught). Already partially wired (face-down casting). Needs turn-face-up + AI heuristic. |
| 4 | **Evoke** | 702.45 | High | Defines Modern elementals cycle (Fury, Solitude, Grief, Subtlety). Requires ETB trigger + sacrifice choice. |
| 5 | **Suspend** | 702.65 | High | Common in Legacy/Vintage (Ancestral Vision, Living End). Already partially wired (special action + upkeep). Needs completion. |

---

## Batch 1: Top 5 Keywords — Detailed Design

---

### 1. Persist (CR 702.61)

**CR Reference**: "When a creature with persist dies, if it had no -1/-1 counters on it, return it to the battlefield under its owner's control with a -1/-1 counter on it."

**Current State**: `PersistKeyword.create_trigger()` is fully implemented with counter check logic. `apply()` is a no-op. No wiring into death hooks.

#### GameState Field
**Reuse existing**: `pending_triggers: list[PendingTrigger]` — no new field needed. Persist creates a `PendingTrigger` via `create_trigger()` which already exists.

#### Stack.py Integration
**File**: `mtg_engine/engine/zones.py` — `move_permanent_to_zone()` function
**Hook Point**: When a permanent moves from `battlefield` to `graveyard`, scan its keywords for "persist" and call `PersistKeyword.create_trigger()`.
**Pattern**: 
```python
# Inside move_permanent_to_zone, after determining to_zone == "graveyard":
if to_zone == "graveyard":
    from mtg_engine.ability.keywords.persist import PersistKeyword
    persist_kw = PersistKeyword()
    if persist_kw.from_oracle_text(permanent.card.oracle_text or ""):
        trigger = persist_kw.create_trigger(game_state, permanent, permanent, to_zone)
        if trigger:
            game_state = game_state.model_copy(
                update={"pending_triggers": game_state.pending_triggers + [trigger]}
            )
```

**File**: `mtg_engine/engine/triggers.py` — trigger resolution
**Hook Point**: When a `persist` trigger resolves (via `put_trigger` endpoint), apply the effect.
**Pattern**: In `_apply_triggered_effect()` or `_apply_single_effect_text()`, add a pattern for persist trigger_type:
```python
if trigger.trigger_type == "persist":
    # Return the card to battlefield with a -1/-1 counter
    gs = _return_with_counter(gs, trigger, counter_type="-1/-1", count=1)
```

**New helper function** in `stack.py`:
```python
def _return_with_counter(game_state, trigger, counter_type, count):
    """Return a card from graveyard to battlefield with counters."""
    # Find card in graveyard by source_card_name
    # Move to battlefield via put_permanent_onto_battlefield
    # Add counter_type counters to the permanent
```

#### Legal Actions
**File**: `mtg_engine/api/routers/game.py` — `_compute_legal_actions()`
No new legal actions needed. Persist is a mandatory triggered ability — it auto-resolves via the pending trigger system. The `pending_triggers` section already handles presenting triggers to the controller.

#### Choice Handler
**File**: `mtg_engine/api/routers/game.py` — `submit_choice()` / `put_trigger` endpoint
No new choice handler needed. The existing `put_trigger` endpoint puts the persist trigger on the stack, and resolution applies the effect.

#### AI Auto-Resolution
Persist is mandatory (not "you may"), so AI auto-resolves: the trigger fires automatically and the controller must put it on the stack.

#### Acceptance Criteria
- [ ] Creature with persist + no -1/-1 counters dies → returns to battlefield with 1 -1/-1 counter
- [ ] Creature with persist + 1 or more -1/-1 counters dies → goes to graveyard normally
- [ ] Persist trigger appears in `pending_triggers` for the controller
- [ ] Persist trigger can be put on stack via `put_trigger` endpoint
- [ ] Persist works with SBA destruction, spell destruction, and combat damage

---

### 2. Undying (CR 702.51)

**CR Reference**: "When a creature with undying dies, if it had no +1/+1 counters on it, return it to the battlefield under its owner's control with a number of +1/+1 counters on it equal to its power."

**Current State**: `UndyingKeyword.create_trigger()` is fully implemented with counter check and `get_counter_count()`. `apply()` is a no-op. No wiring into death hooks.

#### GameState Field
**Reuse existing**: `pending_triggers: list[PendingTrigger]` — same as Persist.

#### Stack.py Integration
**File**: `mtg_engine/engine/zones.py` — `move_permanent_to_zone()`
**Hook Point**: Same as Persist — when a permanent moves from `battlefield` to `graveyard`, scan for "undying".
**Pattern**:
```python
# After persist check:
if to_zone == "graveyard":
    from mtg_engine.ability.keywords.undying import UndyingKeyword
    undying_kw = UndyingKeyword()
    if undying_kw.from_oracle_text(permanent.card.oracle_text or ""):
        trigger = undying_kw.create_trigger(game_state, permanent, permanent, to_zone)
        if trigger:
            game_state = game_state.model_copy(
                update={"pending_triggers": game_state.pending_triggers + [trigger]}
            )
```

**File**: `mtg_engine/engine/triggers.py` — trigger resolution
**Hook Point**: When an `undying` trigger resolves, apply the effect.
**Pattern**:
```python
if trigger.trigger_type == "undying":
    # Calculate counter count = power + toughness
    # Return card to battlefield with +1/+1 counters
    gs = _return_with_counters(gs, trigger, counter_type="+1/+1", count=power+toughness)
```

#### Legal Actions / Choice Handler / AI
Same as Persist — mandatory trigger, auto-resolves through pending trigger system.

#### Acceptance Criteria
- [ ] Creature with undying + no +1/+1 counters dies → returns with (P+T) +1/+1 counters
- [ ] Creature with undying + existing +1/+1 counters dies → goes to graveyard normally
- [ ] Undying trigger appears in `pending_triggers`
- [ ] Works with both Persist and Undying (controller chooses — later enhancement, for now order in zones.py)
- [ ] Counter count = power + toughness at time of death

---

### 3. Morph (CR 702.36)

**CR Reference**: "Morph {cost} — You may cast this card face down as a 2/2 creature for {3}. Turn it face up any time for its morph cost."

**Current State**: `MorphKeyword` has detection/parsing. `pending_morph_payment` exists in GameState. `cast_spell()` handles `as_face_down=True`. But turn-face-up is only referenced in spec tasks, not implemented.

#### GameState Field
**Reuse existing**: `pending_morph_payment: Optional[dict]` — already exists.
```python
# Format: {"player": str, "permanent_id": str, "morph_cost": str, "card_name": str, "resolved": bool}
```

#### Stack.py Integration
No new stack integration needed for the morph casting itself — `cast_spell()` already handles `as_face_down=True`.

**New function** in `mtg_engine/engine/stack.py` or `morph.py`:
```python
def apply_morph_turn_face_up(game_state, permanent_id, player_name):
    """Turn a face-up morph creature face up. CR 702.36b."""
    # Find permanent on battlefield
    # Pay morph cost from oracle text
    # Set is_face_down = False
    # Restore printed characteristics (name, type_line, oracle_text, P/T, keywords)
    # Fire "turned face up" triggers
    # Returns new GameState
```

#### Legal Actions
**File**: `mtg_engine/api/routers/game.py` — `_compute_legal_actions()`
Add to the main phase / instant-speed section:
```python
# Morph: turn face up
for perm in gs.battlefield:
    if (perm.controller == player_name 
        and perm.is_face_down 
        and "morph" in (perm.card.keywords or [])):
        morph_cost = MorphKeyword.parse_morph_cost(perm.card.oracle_text or "")
        if morph_cost and can_pay_cost(player.mana_pool, morph_cost):
            actions.append(LegalAction(
                action_type="choice",
                card_name="morph_turn_face_up",
                description=f"Turn {perm.card.name} face up (pay {morph_cost})",
                valid_targets=[perm.id],
            ))
```

Also add morph cast actions in the main phase section:
```python
# Morph: cast face-down for {3}
if "morph" in kws_lower and can_pay_cost(player.mana_pool, "{3}"):
    actions.append(LegalAction(
        action_type="cast",
        card_id=card.id,
        card_name=card.name,
        alternative_cost="morph",
        mana_options=[{"mana_cost": "{3}"}],
        description=f"Cast {card.name} face-down (morph {3})",
    ))
```

#### Choice Handler
**File**: `mtg_engine/api/routers/game.py` — `submit_choice()`
```python
elif choice_id == "morph_turn_face_up":
    permanent_id = req.selection
    gs = apply_morph_turn_face_up(gs, permanent_id, player_name)
    mgr.update(game_id, gs)
```

#### AI Auto-Resolution
In `ai_client/heuristic_player.py`, when `action_type == "choice"` and `card_name == "morph_turn_face_up"`:
- Always turn face up if the creature's printed power is > 2 (upside)
- Turn face up if the morph cost is cheap and the creature has valuable ETB/triggers
- Keep face down defensively if opponent has removal open

#### Acceptance Criteria
- [ ] Cast creature face-down for {3} → enters as 2/2 colorless with no abilities
- [ ] Turn face up legal action appears when morph cost is affordable
- [ ] Turning face up restores printed characteristics
- [ ] Turning face up does NOT use the stack (special action)
- [ ] AI turns face up when beneficial

---

### 4. Evoke (CR 702.45)

**CR Reference**: "Evoke {cost} — You may cast this card by paying {cost} rather than its mana cost. When this permanent enters the battlefield, its controller sacrifices it."

**Current State**: `EvokeKeyword` has detection/parsing and `create_trigger()`. `apply()` is a no-op. No integration.

#### GameState Field
**New field on GameState**:
```python
pending_evoke_sacrifice: Optional[dict] = None
# Format: {"player": str, "permanent_id": str, "permanent_name": str, "evoked": bool}
```

The `evoked` field indicates whether the creature was cast via evoke cost (sacrifice is mandatory per CR 702.45) or whether the creature simply has an evoke keyword on an alternate cast.

**Clarification**: Per CR 702.45, evoke is an *alternative cost*. If you cast via evoke, the creature *must* be sacrificed on ETB. However, some cards (like Mulldrifter) have both an ETB trigger and evoke — the evoke sacrifice is separate from the ETB draw. The sacrifice trigger goes on the stack.

#### Stack.py Integration
**File**: `mtg_engine/engine/zones.py` — `put_permanent_onto_battlefield()`
**Hook Point**: After a creature with "evoke" keyword enters the battlefield AND was cast with `alternative_cost="evoke"`.
**Pattern**:
```python
# In resolve_top(), after put_permanent_onto_battlefield for creature spells:
if "evoke" in kws_lower and stack_obj.alternative_cost == "evoke":
    # Queue evoke sacrifice trigger
    from mtg_engine.ability.keywords.evoke import EvokeKeyword
    evoke_kw = EvokeKeyword.from_oracle(card.oracle_text or "")
    if evoke_kw:
        trigger = evoke_kw.create_trigger(card, stack_obj.controller, perm.id)
        game_state = game_state.model_copy(
            update={
                "pending_triggers": game_state.pending_triggers + [trigger],
                "pending_evoke_sacrifice": {
                    "player": stack_obj.controller,
                    "permanent_id": perm.id,
                    "permanent_name": card.name,
                    "evoked": True,
                },
            }
        )
```

#### Legal Actions
**File**: `mtg_engine/api/routers/game.py` — `_compute_legal_actions()`
Add evoke cast action in the main phase creature-casting section:
```python
# Evoke: cast creature for evoke cost (will be sacrificed on ETB)
if "evoke" in kws_lower or "evoke" in oracle_lower:
    evoke_cost = EvokeKeyword.parse_evoke_cost(card.oracle_text or "")
    if evoke_cost and can_pay_cost(player.mana_pool, evoke_cost):
        actions.append(LegalAction(
            action_type="cast",
            card_id=card.id,
            card_name=card.name,
            alternative_cost="evoke",
            mana_options=[{"mana_cost": evoke_cost}],
            description=f"Cast {card.name} (evoke {evoke_cost} — will be sacrificed)",
        ))
```

Also add evoke sacrifice choice (if the creature has an ETB "you may" sacrifice trigger):
```python
# Evoke sacrifice choice (only for creatures with evoke that provide a choice)
if gs.pending_evoke_sacrifice and gs.pending_evoke_sacrifice["player"] == player_name:
    actions.append(LegalAction(
        action_type="choice",
        card_name="evoke_sacrifice",
        description=f"Sacrifice {gs.pending_evoke_sacrifice['permanent_name']} (evoke trigger)",
    ))
```

#### Choice Handler
```python
elif choice_id == "evoke_sacrifice":
    if gs.pending_evoke_sacrifice:
        perm_id = gs.pending_evoke_sacrifice["permanent_id"]
        from mtg_engine.engine.zones import move_permanent_to_zone
        gs = move_permanent_to_zone(gs, perm_id, "graveyard")
        gs.pending_evoke_sacrifice = None
    mgr.update(game_id, gs)
```

#### AI Auto-Resolution
Evoke sacrifice is mandatory (not "you may") — if cast via evoke, the creature is always sacrificed. AI evaluates whether the ETB trigger is worth the sacrifice (evoke Mulldrifter for {3}U to draw 2 cards, then sacrifice). The decision happens at cast time, not at resolution.

#### Acceptance Criteria
- [ ] Cast creature with evoke via evoke cost → enters battlefield, then sacrifices itself
- [ ] Evoke legal action appears with correct cost
- [ ] Sacrifice trigger appears in pending_triggers
- [ ] Creature with evoke + ETB draw (Mulldrifter) draws cards THEN sacrifices
- [ ] AI evaluates evoke cast vs normal cast

---

### 5. Suspend (CR 702.65)

**CR Reference**: "Suspend N—{cost}" means "You may pay {cost} and exile this card from your hand with N time counters on it. At the beginning of your upkeep, remove a time counter. When the last is removed, cast it without paying its mana cost."

**Current State**: `SuspendKeyword` has detection/parsing and `create_trigger()`. Special action handler in `game.py` works (removes from hand, adds to `suspended_cards`, pays cost). Upkeep handler in `turn_manager.py` decrements counters and auto-casts when exhausted. `apply()` is a no-op.

#### GameState Field
**Reuse existing**: `PlayerState.suspended_cards: list[Card]` — cards tracked with `parse_status="suspended:N"`.

#### Stack.py Integration
**File**: `mtg_engine/engine/turn_manager.py` — `begin_step()` upkeep handler
Already implemented: decrements time counters, casts for free when exhausted, grants haste.

**Bug fix needed**: The current upkeep handler adds the card to `active.hand` temporarily, then calls `cast_spell()`. This is a hack — the card should be cast from exile, not hand. Fix: use `from_graveyard=False` with a special flag, or add a `from_suspended=True` path to `cast_spell()`.

**File**: `mtg_engine/engine/stack.py` — `cast_spell()`
Add `from_suspended=False` parameter:
```python
elif from_suspended:
    card = next((c for c in player.suspended_cards if c.id == card_id), None)
    if card is None:
        raise ValueError(f"Card {card_id!r} not in suspended cards")
    player.suspended_cards = [c for c in player.suspended_cards if c.id != card_id]
```

#### Legal Actions
Suspend legal action already exists in the special action endpoint. No new legal actions needed for the basic suspend flow.

For the "cast when time counters removed" path — this is automatic via the upkeep handler, no legal action needed.

#### Choice Handler
No new choice handler needed. The suspend special action and upkeep auto-cast are already implemented.

#### AI Auto-Resolution
The AI should decide whether to suspend a card during the main phase. In `ai_client/heuristic_player.py`, add scoring for suspend actions:
- Suspend is good for expensive cards (CMC >= 4) where you can't cast them now but want them later
- Suspend is bad if the creature needs haste or the game will end before counters are removed
- Suspend is good for "cast when last counter removed" to get free casts

#### Acceptance Criteria
- [ ] Suspend special action removes card from hand, pays cost, adds to suspended_cards
- [ ] Upkeep decrements time counters correctly
- [ ] When last counter removed, card is cast for free (no mana cost)
- [ ] Suspended creature gets haste when cast via suspend
- [ ] Card is cast from exile (not temporarily added to hand)
- [ ] AI evaluates suspend as an option for high-CMC cards

---

## Batch 2: Remaining 12 Keywords — Brief Plans

### Category A: Alternative Casting

#### 6. Unearth (CR 702.64)
- **Wiring**: Extend graveyard cast section in `_compute_legal_actions()` — already checks for "unearth" keyword
- **Apply()**: Implement `UnearthKeyword.apply()` to pay unearth cost, move card from graveyard to battlefield tapped
- **ETB**: Set `unearthed=True` on the permanent (add field to `Permanent` model)
- **Cleanup**: At end of turn (cleanup step in `turn_manager.py`), exile all `unearthed=True` permanents
- **New GameState field**: `pending_unearth_choice: Optional[dict]` for human player
- **Complexity**: Medium — follows existing graveyard cast pattern

#### 7. Miracle (CR 702.41)
- **Wiring**: Hook into draw step in `turn_manager.py` — after `draw_card()`, check if drawn card has miracle
- **Apply()**: Queue `pending_miracle_choice` for human, auto-cast for AI if beneficial
- **Cast**: Cast at miracle cost (alternative cost), not mana cost. Must cast immediately or lose the miracle window
- **New GameState field**: `pending_miracle_choice: Optional[dict]` with `player`, `card_id`, `miracle_cost`, `resolved`
- **Complexity**: Medium — requires draw-step hook

### Category B: Triggered on Resolution

#### 8. Bloodthirst (CR 702.31)
- **Wiring**: Hook into `put_permanent_onto_battlefield()` — after creature enters, check if bloodthirst condition met
- **Check**: Has an opponent been dealt combat damage this turn? (Track in `GameState` or `CombatState`)
- **Effect**: Enter with N +1/+1 counters
- **New GameState field**: `combat_damage_to_opponents_this_turn: dict[str, bool]` (per player)
- **Complexity**: Low — simple counter addition on ETB

#### 9. Extort (CR 702.104)
- **Wiring**: Hook into `cast_spell()` — after any spell is cast, if controller has extort creature, offer extort choice
- **New GameState field**: `pending_extort_choice: Optional[dict]`
- **Legal action**: "Pay extort {W}{B}" — each opponent loses 1 life, you gain 1 life
- **AI**: Auto-resolve if mana available and beneficial (opponent has life to lose)
- **Complexity**: Low — life gain/loss is already implemented

#### 10. Sunburst (CR 702.103)
- **Wiring**: Hook into `put_permanent_onto_battlefield()` — after artifact/creature enters, count colored mana symbols in mana cost
- **Effect**: Put N charge counters (use +1/+1 for creatures, charge counters for artifacts)
- **Complexity**: Low — simple counter addition based on mana cost parsing

#### 11. Transmute (CR 702.68)
- **Wiring**: Add as activated ability in graveyard — card with transmute can be discarded + pay cost to tutor for same CMC
- **Legal action**: In graveyard cast section, add transmute action
- **Apply()**: Discard card, pay cost, search library for cards with same CMC, reveal and put into hand
- **New GameState field**: `pending_transmute_choice: Optional[dict]` for human player
- **Complexity**: Medium — requires library search + CMC matching

### Category C: Triggered on Death/Damage

#### 12. Afterlife (CR 702.108)
- **Wiring**: Same as Persist/Undying — hook into `move_permanent_to_zone()` death path
- **Apply()**: When the trigger resolves, create N 1/1 white Spirit creature tokens
- **Token creation**: Use existing `_create_tokens()` helper in `stack.py`
- **Complexity**: Low — trigger generator already exists, just wire into death hooks and resolve

### Category D: Stack Interaction

#### 13. Replicate (CR 702.87)
- **Wiring**: `StackObject.replicate_count` exists. `resolve_top()` already creates copies.
- **Missing**: Legal action to pay replicate cost multiple times during cast
- **Apply()**: In `_compute_legal_actions()`, when casting a replicate spell, offer "Pay replicate {cost}" additional payment
- **New GameState field**: `pending_replicate_payment: Optional[dict]` — tracks how many times replicate was paid
- **Complexity**: Medium — need to wire multiple-cost payment into cast flow

#### 14. Surge (CR 702.113)
- **Wiring**: In `_compute_legal_actions()`, check if opponent cast a spell this turn
- **Condition**: `gs.spells_cast_this_turn_by_player[opponent] > 0`
- **Effect**: Offer alternative cast action with surge cost (cheaper)
- **Complexity**: Low — just a conditional alternative cost check

#### 15. Buyback (CR 702.28)
- **Wiring**: `StackObject.buyback_paid` exists. `resolve_top()` already returns to hand.
- **Missing**: Legal action to pay buyback cost during cast
- **Apply()**: In `_compute_legal_actions()`, when casting a buyback spell, offer "Cast with buyback {cost}" action
- **Complexity**: Low — just add legal action, resolution already works

#### 16. Entwine (CR 702.39)
- **Wiring**: In `_compute_legal_actions()`, for modal spells with entwine, offer "Pay entwine {cost} — choose all modes"
- **Effect**: When entwine is paid, `modes_chosen` includes all mode indices
- **New GameState field**: `pending_entwine_choice: Optional[dict]` for human player
- **Complexity**: Low — just extend modal spell handling

#### 17. Scavenge (CR 702.106)
- **Wiring**: Add as activated ability in graveyard — exile card + pay cost → put +1/+1 counters on target creature
- **Legal action**: In graveyard cast section, add scavenge action targeting battlefield creatures
- **Apply()**: Exile card from graveyard, pay cost, add counters equal to exiled card's power
- **New GameState field**: `pending_scavenge_target: Optional[dict]` for human player
- **Complexity**: Low — exile + counter addition

---

## Implementation Batch Plan

### Batch 1: Top 5 Keywords (Full Implementation)

**Estimated Complexity**: High
**Files to Modify**:
| File | Changes |
|------|---------|
| `mtg_engine/models/game.py` | Add `pending_evoke_sacrifice` field |
| `mtg_engine/engine/zones.py` | Wire persist/undying/afterlife into `move_permanent_to_zone()` death path |
| `mtg_engine/engine/triggers.py` | Add persist/undying/afterlife trigger resolution patterns |
| `mtg_engine/engine/stack.py` | Add `_return_with_counter()` helper; add `from_suspended` to `cast_spell()`; wire evoke sacrifice into `resolve_top()` |
| `mtg_engine/engine/morph.py` (or `stack.py`) | Add `apply_morph_turn_face_up()` function |
| `mtg_engine/ability/keywords/morph.py` | Implement `apply()` — turn face up logic |
| `mtg_engine/ability/keywords/evoke.py` | Implement `apply()` — sacrifice on ETB |
| `mtg_engine/ability/keywords/suspend.py` | Implement `apply()` — complete suspend flow |
| `mtg_engine/api/routers/game.py` | Add morph/evoke/suspend legal actions + choice handlers |
| `tests/engine/test_persist_integration.py` | 10-15 tests |
| `tests/engine/test_undying_integration.py` | 10-15 tests |
| `tests/engine/test_morph_integration.py` | 8-10 tests |
| `tests/engine/test_evoke_integration.py` | 8-10 tests |
| `tests/engine/test_suspend_integration.py` | 8-10 tests |

### Batch 2: Remaining 12 Keywords (Simpler Implementations)

**Estimated Complexity**: Medium
**Files to Modify**:
| File | Changes |
|------|---------|
| `mtg_engine/models/game.py` | Add `pending_extort_choice`, `pending_miracle_choice`, `pending_transmute_choice`, `pending_scavenge_target`, `pending_entwine_choice`, `pending_replicate_payment` fields; add `combat_damage_to_opponents_this_turn` tracking |
| `mtg_engine/engine/zones.py` | Wire afterlife into death path (if not done in Batch 1) |
| `mtg_engine/engine/turn_manager.py` | Hook miracle into draw step |
| `mtg_engine/engine/combat.py` | Track combat damage to opponents for bloodthirst |
| `mtg_engine/engine/stack.py` | Add extort trigger after spell cast; wire surge/buyback/replicate legal actions |
| `mtg_engine/ability/keywords/unearth.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/miracle.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/bloodthirst.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/extort.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/sunburst.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/transmute.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/afterlife.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/replicate.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/surge.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/buyback.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/entwine.py` | Implement `apply()` |
| `mtg_engine/ability/keywords/scavenge.py` | Implement `apply()` |
| `mtg_engine/api/routers/game.py` | Add legal actions + choice handlers for Batch 2 keywords |
| `tests/engine/test_batch2_keywords_integration.py` | 30-40 tests total |

---

## Task Breakdown (Ordered by Dependency)

### Task 1: Persist Death Hook Wiring
- **Files**: `mtg_engine/engine/zones.py`, `mtg_engine/engine/triggers.py`
- **Description**: Wire `PersistKeyword.create_trigger()` into `move_permanent_to_zone()` death path. Add trigger resolution pattern for persist in `triggers.py`.
- **Acceptance Criteria**: Creature with persist + no -1/-1 counters dies → returns with -1/-1 counter. Creature with persist + counters → goes to graveyard.

### Task 2: Undying Death Hook Wiring
- **Files**: `mtg_engine/engine/zones.py`, `mtg_engine/engine/triggers.py`
- **Description**: Wire `UndyingKeyword.create_trigger()` into `move_permanent_to_zone()` death path. Add trigger resolution pattern for undying.
- **Acceptance Criteria**: Creature with undying + no +1/+1 counters dies → returns with (P+T) counters. Creature with +1/+1 counters → goes to graveyard.

### Task 3: Morph Turn-Face-Up
- **Files**: `mtg_engine/engine/morph.py` (new), `mtg_engine/api/routers/game.py`
- **Description**: Implement `apply_morph_turn_face_up()` function. Add morph cast + turn-face-up legal actions. Add choice handler.
- **Acceptance Criteria**: Turn face up restores characteristics. Legal action appears when morph cost affordable.

### Task 4: Evoke Sacrifice on ETB
- **Files**: `mtg_engine/models/game.py`, `mtg_engine/engine/stack.py`, `mtg_engine/api/routers/game.py`
- **Description**: Add `pending_evoke_sacrifice` field. Wire evoke sacrifice trigger into `resolve_top()`. Add evoke cast legal action + sacrifice choice handler.
- **Acceptance Criteria**: Evoke creature enters → sacrifice trigger fires → creature sacrificed.

### Task 5: Suspend Completion
- **Files**: `mtg_engine/engine/stack.py`, `mtg_engine/engine/turn_manager.py`
- **Description**: Fix suspend cast path (cast from exile, not hand). Complete `SuspendKeyword.apply()`.
- **Acceptance Criteria**: Suspended creature casts from exile. Gets haste.

### Task 6: Batch 2 Keywords
- **Files**: All keyword modules listed in Batch 2
- **Description**: Implement `apply()` for remaining 12 keywords. Wire into appropriate hooks (ETB, death, cast, graveyard).
- **Acceptance Criteria**: All 12 keywords have working `apply()` methods integrated into the game engine.

### Task 7: Test Suites
- **Files**: All test files listed above
- **Description**: Create integration test suites for all 17 keywords.
- **Acceptance Criteria**: All tests pass, no regressions.

---

## Data Models / Interfaces

### New GameState Fields (Batch 1)
```python
# Evoke sacrifice tracking
pending_evoke_sacrifice: Optional[dict] = None
# Format: {"player": str, "permanent_id": str, "permanent_name": str, "evoked": bool}
```

### New GameState Fields (Batch 2)
```python
# Bloodthirst tracking
combat_damage_to_opponents_this_turn: dict[str, bool] = Field(default_factory=dict)
# player_name -> True if dealt combat damage to any opponent this turn

# Miracle choice
pending_miracle_choice: Optional[dict] = None
# Format: {"player": str, "card_id": str, "card_name": str, "miracle_cost": str, "resolved": bool}

# Extort choice
pending_extort_choice: Optional[dict] = None
# Format: {"player": str, "extort_cost": str, "spell_controller": str}

# Transmute choice
pending_transmute_choice: Optional[dict] = None
# Format: {"player": str, "card_id": str, "card_name": str, "transmute_cost": str, "cmc": int}

# Scavenge target
pending_scavenge_target: Optional[dict] = None
# Format: {"player": str, "card_id": str, "card_name": str, "scavenge_cost": str, "power": int}

# Entwine choice
pending_entwine_choice: Optional[dict] = None
# Format: {"player": str, "entwine_cost": str, "modes": list[int]}

# Replicate payment
pending_replicate_payment: Optional[dict] = None
# Format: {"player": str, "replicate_cost": str, "times_paid": int, "max_affordable": int}
```

### Permanent Model Addition
```python
# Add to Permanent class:
unearthed: bool = False  # CR 702.64: exile at end of turn
```

---

## Testing Strategy

### Batch 1 Tests

#### Persist Tests (tests/engine/test_persist_integration.py)
1. `test_persist_returns_with_counter` — 2/2 persist, no counters, dies → returns 2/2 with 1 -1/-1 counter
2. `test_persist_does_not_fire_with_counters` — 2/2 persist, 1 -1/-1 counter, dies → goes to graveyard
3. `test_persist_from_combat_damage` — persist creature dealt lethal damage in combat → returns
4. `test_persist_from_spell_destruction` — persist creature destroyed by Doom Blade → returns
5. `test_persist_from_sba` — persist creature with 0 toughness → goes to graveyard (SBAs don't use destroy)
6. `test_persist_trigger_in_pending` — trigger appears in pending_triggers after death
7. `test_persist_trigger_put_on_stack` — controller puts persist trigger on stack
8. `test_persist_ai_auto_resolve` — AI player's persist creature dies → trigger resolves automatically
9. `test_persist_token_with_persist` — token with persist dies → ceases to exist (no return)
10. `test_persist_pure_transform` — persist resolution returns new GameState

#### Undying Tests (tests/engine/test_undying_integration.py)
1. `test_undying_returns_with_counters` — 2/2 undying, no counters, dies → returns with 4 +1/+1 counters (2 power + 2 toughness)
2. `test_undying_does_not_fire_with_counters` — 2/2 undying, 1 +1/+1 counter, dies → goes to graveyard
3. `test_undying_from_combat_damage` — undying creature dealt lethal damage → returns
4. `test_undying_from_spell_destruction` — undying creature destroyed → returns
5. `test_undying_counter_count_equals_power_plus_toughness` — 3/4 undying → returns with 7 +1/+1 counters
6. `test_undying_trigger_in_pending` — trigger appears in pending_triggers
7. `test_undying_token_with_undying` — token with undying dies → ceases to exist
8. `test_undying_pure_transform` — undying resolution returns new GameState
9. `test_undying_with_zero_power` — 0/1 undying dies → returns with 1 +1/+1 counter

#### Morph Tests (tests/engine/test_morph_integration.py)
1. `test_morph_cast_face_down` — cast creature face-down for {3} → 2/2 colorless
2. `test_morph_turn_face_up_restores_characteristics` — turn face up → printed stats restored
3. `test_morph_turn_face_up_legal_action` — legal action appears when morph cost affordable
4. `test_morph_turn_face_up_no_stack` — turning face up is a special action (no stack)
5. `test_morph_ai_turns_face_up` — AI turns face up when beneficial
6. `test_morph_ai_keeps_face_down` — AI keeps face down when opponent has removal
7. `test_morph_cannot_turn_up_without_mana` — insufficient mana → no legal action
8. `test_morph_megamorph_counter` — megamorph turn face up adds +1/+1 counter

#### Evoke Tests (tests/engine/test_evoke_integration.py)
1. `test_evoke_sacrifice_on_etb` — evoke creature enters → sacrifices itself
2. `test_evoke_cast_legal_action` — evoke legal action with correct cost
3. `test_evoke_etb_draw_then_sacrifice` — Mulldrifter evoke: draw 2, then sacrifice
4. `test_evoke_normal_cast_no_sacrifice` — normal cast of evoke creature → stays on battlefield
5. `test_evoke_trigger_in_pending` — evoke sacrifice trigger appears in pending_triggers
6. `test_evoke_ai_evaluates_cast` — AI evaluates evoke vs normal cast
7. `test_evoke_pure_transform` — evoke resolution returns new GameState
8. `test_evoke_with_anthem` — evoke creature with anthem effect enters, anthem applies briefly

#### Suspend Tests (tests/engine/test_suspend_integration.py)
1. `test_suspend_from_hand` — suspend card from hand → moves to suspended_cards
2. `test_suspend_time_counter_decrement` — upkeep decrements counter
3. `test_suspend_cast_when_exhausted` — last counter removed → cast for free
4. `test_suspend_grants_haste` — suspended creature gets haste on free cast
5. `test_suspend_cost_paid` — suspend cost deducted from mana pool
6. `test_suspend_ai_evaluates` — AI scores suspend action
7. `test_suspend_multiple_counters` — suspend with 3 counters → 3 upkeeps to cast
8. `test_suspend_pure_transform` — suspend resolution returns new GameState

### Batch 2 Tests (tests/engine/test_batch2_keywords_integration.py)
- 2-3 tests per keyword covering:
  - Basic functionality (keyword triggers/applies correctly)
  - Human player choice queuing
  - AI auto-resolution
  - Edge cases (insufficient mana, no valid targets)
  - Pure transform pattern

---

## Potential Risks

1. **Risk**: Persist + Undying on same creature — controller must choose which replacement effect applies → **Mitigation**: For v1, fire both triggers and let the controller choose via the pending trigger system. The existing `is_optional` flag on PendingTrigger handles this.

2. **Risk**: Morph turn-face-up timing — can happen at instant speed, even during combat → **Mitigation**: Implement as a special action (no stack), available any time the controller has priority.

3. **Risk**: Evoke + flicker interaction — evoke creature flickered returns without sacrifice trigger → **Mitigation**: Track "evoked" status on the permanent; if flickered, the new permanent is not "evoked" (CR 603.6e).

4. **Risk**: Suspend cast path is a hack (adds to hand temporarily) → **Mitigation**: Add proper `from_suspended` parameter to `cast_spell()` to cast from exile directly.

5. **Risk**: Token interactions with Persist/Undying — tokens cease to exist when they leave the battlefield → **Mitigation**: Check `permanent.is_token` before creating persist/undying triggers. Tokens that die cease to exist; they don't go to the graveyard.

---

## Handoff to Implementer

**Design Document**: `specs/sprint-a/SA-04-design.md` (this file)
**User Story**: SA-04 — Wire 17 merged keywords into stack resolution + legal actions
**Estimated Complexity**: High (Batch 1: 5 keywords with full integration), Medium (Batch 2: 12 simpler keywords)
**Key Files**:
- `mtg_engine/engine/zones.py` — Death hook wiring for Persist/Undying/Afterlife
- `mtg_engine/engine/stack.py` — Trigger resolution, evoke sacrifice, suspend cast path
- `mtg_engine/engine/triggers.py` — New trigger type patterns
- `mtg_engine/api/routers/game.py` — Legal actions + choice handlers
- `mtg_engine/models/game.py` — New pending_* fields

**Start With**: Task 1 (Persist Death Hook Wiring) — highest impact, simplest integration, establishes the pattern for Undying/Afterlife.

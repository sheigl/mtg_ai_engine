# Research: Rules Engine Complete Parity (Feature 020)

**Feature**: 020-rules-engine-complete-parity
**Date**: 2026-04-01

---

## 1. Mana Ability System Design

**Decision**: Introduce an `is_mana_ability(ability_text, permanent)` classifier function in `mana.py`. When `activate_ability` is called, check the classifier first. If it returns True, resolve the ability immediately (add mana to pool) without placing it on the stack. Modify `_compute_legal_actions()` to tag mana-ability activations with `action_type="activate_mana_ability"` so the UI can distinguish them.

**Rationale**: CR 605 defines mana abilities as activated abilities that (a) could produce mana, (b) do not have a target, and (c) are not loyalty abilities. The classifier checks these three conditions against oracle_text patterns (e.g. `r"[Aa]dd \{[WUBRGC]\}"` or `r"[Aa]dd one mana of any"`) and the absence of "target" in the ability text.

**Implementation approach**:
- New function `is_mana_ability(oracle_text: str, is_loyalty: bool = False) -> bool` in `mana.py`
- Pattern match: `r"[Aa]dd\s+(\{[WUBRGC]\}|one mana|mana of any)"` AND `"target" not in text.lower()` AND `not is_loyalty`
- In `game.py` router's activate endpoint: call classifier before `stack.activate_ability()`. If mana ability, call new `resolve_mana_ability(game_state, permanent_id, ability_index)` directly
- In `_has_split_second()` checks: exempt `activate_mana_ability` action types

**Alternatives considered**:
1. Flag on Card model (`is_mana_ability: bool`). Rejected — would require Scryfall data enrichment and doesn't handle conditional abilities.
2. Separate endpoint for mana abilities. Rejected — creates unnecessary API surface; same activate endpoint with different internal routing is cleaner.

---

## 2. Split Card / MDFC Data Model

**Decision**: Add `card_layout: str = "normal"` to `Card` with values `"normal"`, `"split"`, `"mdfc"`, `"adventure"`, `"aftermath"`, `"transform"`. The existing `Card.faces: list[CardFace]` field holds face data. Add `face_index: int = 0` to `CastRequest` to specify which face to cast. Add `fuse: bool = False` to `CastRequest` for fuse casts.

**Rationale**: The `CardFace` model already contains `name`, `mana_cost`, `type_line`, `oracle_text`, `power`, `toughness`, and `loyalty`. The `faces` list already exists on `Card`. What's missing is:
1. A way for the player to specify which face to cast → `face_index` on `CastRequest`
2. A way for the engine to know the card's layout type → `card_layout` field
3. Fuse support → `fuse` boolean on `CastRequest`

**Cast flow modification**: In `cast_spell()`, when `card.faces` is not None and `len(card.faces) > 1`:
- Read `face_index` from the cast request
- Override the stack object's `source_card` fields (name, mana_cost, type_line, oracle_text) with the selected face's values
- For fuse: merge both faces' costs and effects into a single stack object
- For aftermath: if `face_index=1`, validate the card is in the graveyard (aftermath second half only castable from graveyard)
- For adventure: if `face_index=1` (adventure half), mark the stack object so that on resolution the card is exiled instead of going to graveyard; track adventure exile state for later creature cast from exile

**Legal action generation**: When computing legal actions for a multi-face card, emit one `LegalAction` per castable face. For split cards: two actions (left, right) plus optionally fuse. For MDFCs: one cast action for front face and, if back is a land, a play-land action. For adventure: one creature cast and one adventure cast (if in hand), plus creature cast from exile (if adventure-exiled).

**Alternatives considered**:
1. Separate Card objects per face. Rejected — breaks the single-card identity needed for zone tracking and ownership.
2. Using `alternative_cost` field for face selection. Rejected — face selection is orthogonal to alternative costs; a card can be cast via its right face AND with kicker.

---

## 3. ETB Replacement Effect Pipeline

**Decision**: Add a `apply_etb_replacements(game_state, permanent, controller) -> Permanent` pipeline function in `replacement.py` called from `put_permanent_onto_battlefield()` before the permanent is added to the battlefield list. This function iterates all permanents already on the battlefield looking for ETB modification patterns in their oracle_text.

**Rationale**: ETB replacement effects fall into two categories:
1. **Enters-tapped effects**: "Nonbasic lands enter the battlefield tapped", "Creatures your opponents control enter the battlefield tapped"
2. **Counter modification effects**: "If one or more counters would be placed on a permanent you control, twice that many are placed instead" (Doubling Season)

**Pattern matching approach**: Define a registry of ETB patterns in `replacement.py`:
```python
ETB_TAPPED_PATTERNS = [
    (r"nonbasic lands? (?:you control )?enter(?:s)? the battlefield tapped", lambda perm: "land" in perm.card.type_line.lower() and "basic" not in perm.card.type_line.lower()),
    (r"creatures? your opponents control enter(?:s)? the battlefield tapped", lambda perm, ctrl: "creature" in perm.card.type_line.lower() and perm.controller != ctrl),
]
ETB_COUNTER_PATTERNS = [
    (r"if .* would (?:place|put) .* counter", "double"),
]
```

**Pipeline execution order**: When multiple replacement effects apply:
1. Collect all applicable effects
2. The affected player (permanent's controller) chooses the order (CR 616.1)
3. For now, apply in timestamp order of the source permanents (future: add pending choice for order selection)

**Alternatives considered**:
1. Formal ReplacementEffect registration on GameState. Rejected for now — adds complexity; oracle_text scanning at ETB time is sufficient for the current scope. Can upgrade later.
2. Pre-registering all replacement effects at game start. Rejected — effects come and go as permanents enter/leave the battlefield; scanning at event time is simpler.

---

## 4. Trigger Pattern Approach

**Decision**: Extend the existing regex approach in `triggers.py` with a structured event-type dispatch system. Instead of trying to match all patterns with a single regex pass, route trigger checking by event type: `EVENT_GAIN_LIFE`, `EVENT_LAND_ENTER`, `EVENT_CREATURE_DIES`, `EVENT_DRAW_CARD`, `EVENT_SACRIFICE`, `EVENT_COUNTER_SPELL`, etc. Each event type has its own pattern list and matching function.

**Rationale**: The current monolithic regex approach works for 15 patterns but does not scale. Event-type dispatch means:
- Each event caller (e.g. `gain_life()`, `draw_card()`, `sacrifice()`) calls `check_event_triggers(game_state, event_type, event_data)` with structured data
- The trigger checker dispatches to the appropriate pattern list
- Pattern lists are much simpler because the event type constrains what to match

**New event types and their trigger patterns**:
```python
EVENT_TRIGGERS = {
    "gain_life": [r"whenever you gain life", r"whenever a player gains life"],
    "land_enter": [r"whenever a land enters the battlefield", r"landfall"],
    "creature_dies": [r"whenever a creature you control dies", r"whenever a creature dies"],
    "draw_card": [r"whenever you draw a card", r"whenever a player draws a card"],
    "sacrifice": [r"whenever you sacrifice", r"whenever a player sacrifices"],
    "counter_spell": [r"whenever a spell .* is countered"],
    "enchantment_enter": [r"whenever an enchantment enters the battlefield"],
    "end_step": [r"at the beginning of (?:your|each) end step"],
}
```

**Integration**: Add `check_event_triggers(game_state, event_type, event_data)` calls to:
- `zones.py:draw_card()` → `EVENT_DRAW_CARD`
- New `gain_life()` helper in `zones.py` → `EVENT_GAIN_LIFE`
- `zones.py:move_permanent_to_zone(to_zone="graveyard")` for creatures → `EVENT_CREATURE_DIES`
- `zones.py:put_permanent_onto_battlefield()` for lands → `EVENT_LAND_ENTER`
- `turn_manager.py` end step entry → `EVENT_END_STEP`

**Alternatives considered**:
1. Full oracle text NLP classification. Rejected — over-engineered for current needs; regex with structured dispatch is maintainable.
2. Scryfall-based trigger tagging at import. Rejected — Scryfall data doesn't tag trigger conditions; oracle_text is the source of truth.
3. Keep extending single-pass regex. Rejected — already at 15 patterns and becoming unwieldy; structured dispatch is cleaner.

---

## 5. Damage Modification Replacement Effect Chain

**Decision**: Add a `DamageModifier` model and `GameState.damage_modifiers: list[DamageModifier]` field. Before any damage event is dealt, run `apply_damage_modifiers(game_state, source, target, amount, is_combat) -> int` which iterates all modifiers in timestamp order, applying multipliers. After modification, apply damage prevention shields (existing pipeline).

**Rationale**: Damage doublers and triplers are replacement effects (CR 614.1a). When multiple replacement effects apply, the affected player or controller of the affected object chooses the order. For simplicity, we apply in timestamp order (oldest first), which matches the most common interpretation.

**Model**:
```python
class DamageModifier(BaseModel):
    source_permanent_id: str
    controller: str
    multiplier: int  # 2 for doublers, 3 for triplers
    applies_to: str  # "all" | "sources_you_control" | "combat_only"
```

**Pipeline order**:
1. Base damage amount determined
2. `apply_damage_modifiers()` — multiply as appropriate
3. `apply_damage_prevention()` (existing) — reduce by prevention shields
4. Apply final damage

**Interaction with prevention**: The modified (larger) amount is what prevention shields reduce. A 3-damage prevention shield against a doubled 3-damage source (now 6) prevents 3 and lets 3 through.

**Registration**: When a permanent with a damage-doubling static ability enters the battlefield, add a `DamageModifier` to `game_state.damage_modifiers`. When it leaves, remove it. This is done in `put_permanent_onto_battlefield()` and `move_permanent_to_zone()`.

**Alternatives considered**:
1. Inline detection in damage functions. Rejected — damage is dealt from multiple call sites (combat, spell effects, ability effects); centralizing in a modifier pipeline avoids duplication.
2. Using existing ReplacementEffect model. Rejected — damage modification is distinct from the zone-change replacement effects already modeled; a dedicated model is clearer.

---

## 6. Type-Layer Overwrite Semantics (Blood Moon)

**Decision**: Extend layer 4 handling in `layers.py` to support three operations: `type_add` (existing), `type_remove`, and `type_overwrite`. Blood Moon is a `type_overwrite` effect: it sets the subtype to "Mountain" and grants the intrinsic mana ability while removing all other land subtypes and non-intrinsic abilities.

**Rationale**: CR 305.7 defines intrinsic mana abilities for basic land types. When a land becomes a Mountain (and nothing else), it loses all printed abilities and gains only "{T}: Add {R}". This is layer 4 for the type change and layer 6 for the ability change (removal of old + addition of intrinsic).

**Implementation in `layers.py`**:
```python
class ContinuousEffect(BaseModel):
    # ... existing fields ...
    type_operation: str = "add"  # "add" | "remove" | "overwrite"
    remove_abilities: bool = False  # True for Blood Moon-style effects
    grant_abilities: list[str] = []  # e.g. ["{T}: Add {R}"]
```

**Layer application order**:
- Layer 4: Apply type overwrite (set subtypes to "Mountain")
- Layer 6: If `remove_abilities=True`, clear all non-intrinsic abilities; then add `grant_abilities`

**Blood Moon detection**: Scan oracle_text for patterns like `r"nonbasic lands are (\w+)s?"`. Extract the basic land type. Map to intrinsic ability: Plains→{W}, Island→{U}, Swamp→{B}, Mountain→{R}, Forest→{G}.

**Alternatives considered**:
1. Special-casing Blood Moon. Rejected — the same mechanism handles Spreading Seas, Imprisoned in the Moon, and other type-changing cards.
2. Handling entirely in layer 4. Rejected — ability removal/addition is a layer 6 concern per CR 613.1f; must be split across layers.

---

## 7. Additional Combat Phase State Machine

**Decision**: Add `additional_combat_phases: int = 0` to `GameState`. When `turn_manager.py` would normally transition from combat to postcombat main, check the counter. If > 0, decrement and transition to a new beginning-of-combat step instead of postcombat main. Each additional combat is a full combat phase (all steps). After the additional combats are exhausted, proceed to postcombat main.

**Rationale**: The turn structure is already a state machine in `turn_manager.py`. Adding a combat-phase counter is the simplest extension — it avoids modifying the phase/step enum and reuses the existing combat step sequence.

**Turn flow with additional combats**:
```
... → Combat Phase → Postcombat Main → [if additional_combat_phases > 0] → Combat Phase → Postcombat Main → ... → Ending Phase
```

**Effect registration**: When a trigger or effect grants an additional combat phase (e.g. Aurelia's attack trigger), it increments `game_state.additional_combat_phases`. The turn manager consumes the counter at the appropriate transition point.

**Creature re-attack**: Creatures that attacked in a previous combat this turn can attack again in the additional combat if they are untapped. Some effects that grant additional combats also untap all creatures (Aurelia: "untap all creatures you control") — this is handled by the trigger's effect, not by the combat phase machinery.

**Alternatives considered**:
1. Inserting phase objects into a phase queue. Rejected — the current turn manager uses a simple state machine; a queue adds complexity for minimal benefit.
2. Repeating the entire turn. Rejected — additional combats are NOT extra turns; main phases, untap, upkeep, draw do not repeat.

---

## 8. Ward Cost Payment Flow

**Decision**: Use the existing `pending_ward_payment` field on `GameState`. When a spell or ability targets a permanent with ward, set `pending_ward_payment = {"player": targeting_player, "ward_cost": cost_string, "targeting_spell_id": stack_obj_id, "source_permanent_id": warded_perm_id}`. The game pauses for the targeting player to submit payment via `POST /game/{game_id}/choice` with `choice_id="ward_payment"`.

**Rationale**: The `pending_ward_payment` field already exists on `GameState` but the ward trigger detection and payment flow are not implemented. Ward is a triggered ability that fires when the permanent becomes the target of a spell/ability an opponent controls. The trigger goes on the stack; when it resolves, the opponent must pay or the targeting spell is countered.

**Flow**:
1. Player A casts spell targeting Player B's warded creature
2. Spell goes on stack
3. Ward triggered ability goes on stack (above the spell)
4. Ward trigger resolves: set `pending_ward_payment`
5. Player A submits choice: pay or decline
6. If paid: ward trigger finishes, spell remains on stack
7. If declined: spell is countered and removed from stack

**Ward cost parsing**: Scan oracle_text for `r"[Ww]ard\s*(?:—\s*)?(.+?)(?:\.|$)"`. The captured group is the cost. Mana costs like `{2}` are parsed normally. Non-mana costs like "Discard a card" or "Pay 3 life" are handled as special ward cost types.

**Alternatives considered**:
1. Auto-paying ward costs if the player has the mana. Rejected — the player must choose whether to pay; auto-pay removes strategic decisions (and non-mana ward costs cannot be auto-paid).
2. New endpoint for ward payment. Rejected — the existing `/choice` endpoint and `pending_ward_payment` mechanism handle this cleanly.

---

## 9. Cleanup Step Design

**Decision**: Implement cleanup as a new function `process_cleanup_step(game_state) -> GameState` in `turn_manager.py`. Called at the end of the ending phase after the end step. The function performs three actions in order: (1) active player discards to hand size, (2) remove all damage and expire "until end of turn" effects, (3) check SBAs and triggers — if any fire, grant priority and repeat cleanup after stack empties.

**Discard implementation**: Set `pending_discard_choice` on `GameState` with `count = len(hand) - max_hand_size`. Wait for player to submit discard choices via the existing `/choice` endpoint.

**Damage removal**: Iterate `game_state.battlefield`, set `damage_marked = 0` for all permanents.

**Effect expiry**: Iterate `game_state.battlefield`, reset `power_bonus = 0` and `toughness_bonus = 0` for all permanents where `power_bonus_expires == "end_of_turn"` or `toughness_bonus_expires == "end_of_turn"`. Also clear `crewed_until_end_of_turn`, any temporary keyword grants, etc.

**Priority during cleanup**: By default, no priority is granted. If `check_sba()` returns changes or `check_triggers()` adds pending triggers, grant priority to the active player. After the stack empties, begin a new cleanup step.

**Alternatives considered**:
1. Folding cleanup into the end step. Rejected — CR 514 is explicit that cleanup is a separate step with distinct rules about priority.
2. Skipping discard-to-hand-size and handling it as an SBA. Rejected — CR 514.1 specifies this happens during cleanup, not as an SBA. The timing matters for cards that care about discarding.

---

## 10. Phasing Design

**Decision**: Add `phased_out: bool = False` to `Permanent`. During the untap step (before untapping), iterate all permanents: those with `phased_out=True` phase in (set to False); those with phasing keyword or flagged to phase out set `phased_out=True`. All game systems that query the battlefield must filter out `phased_out=True` permanents.

**Indirect phasing**: When a permanent phases out, find all Auras, Equipment, and Fortifications attached to it (via `attached_to` field). Set their `phased_out=True` as well. When phasing back in, they phase in still attached.

**Tokens**: If a token has `phased_out=True` and would phase in, instead remove it from the battlefield entirely (CR 702.25d).

**Not-entering**: Phasing in does NOT count as entering the battlefield. No ETB triggers fire. This is critical for correctness.

**Battlefield filtering**: Add a helper `get_active_battlefield(game_state) -> list[Permanent]` that returns only permanents with `phased_out=False`. All combat, targeting, SBA, trigger, and layer functions must use this filtered list.

**Alternatives considered**:
1. Moving phased-out permanents to a separate zone. Rejected — CR 702.25a specifies phased-out permanents remain on the battlefield; they are merely treated as though they don't exist. A separate zone would break ownership and attachment tracking.
2. Only supporting Teferi's Protection. Rejected — implementing the general phasing mechanism is not much more work than special-casing one card, and it handles all phasing cards.

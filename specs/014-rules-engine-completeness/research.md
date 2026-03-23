# Research: Rules Engine Completeness (014)

**Date**: 2026-03-23

---

## Decision 1: Deck-Out SBA (CR 704.5b)

**Decision**: Flag the player as having lost inside `draw_card()` in `zones.py` when the library is empty; the existing SBA loop in `check_and_apply_sbas` will detect `p.has_lost` on the next priority grant.

**Why**: The existing `draw_card` already has a comment "SBA will handle the loss condition", but `sba.py` has no 704.5b check. The cleanest fix is to mark `p.has_lost = True` (and log it) directly in `draw_card` so the SBA loop picks it up without a structural change to `sba.py`. An alternative `failed_draw` flag on `PlayerState` was considered but adds model complexity for no benefit.

**Alternatives considered**:
- Add a `failed_draw: bool` field to `PlayerState` and check it in `_check_once` — rejected (more model churn, same effect).
- Check inside `begin_step` before calling `draw_card` — rejected (wrong layer; draw_card is called in other contexts too).

---

## Decision 2: Combat Damage Triggers

**Decision**: Add `check_damage_triggers(game_state, assignments)` to `triggers.py`, called from `assign_combat_damage` in `combat.py` after damage is marked. It scans all permanents for `"whenever this deals damage"` / `"whenever ~ deals combat damage"` oracle patterns and queues `PendingTrigger` entries.

**Why**: The existing `_on_zone_change` listener pattern shows how triggers are queued from events. The same pattern applies to damage events — scan permanents, match oracle text, enqueue. Calling from `assign_combat_damage` is the natural insertion point because that's where damage is resolved.

**Alternatives considered**:
- Add a global damage event emitter (like `_zone_change_listeners`) — more flexible but adds indirection and is over-engineered for the current trigger set.
- Fire triggers only for "deals damage to a player" — partially correct, but "deals damage to a creature" patterns also exist.

---

## Decision 3: Hybrid and Phyrexian Mana Validation

**Decision**: Extend `_can_pay_simple` in `mana.py` to handle hybrid symbols (`W/U`, `2/B`, etc.) and Phyrexian symbols (`B/P` etc.). Hybrid: accepts either color option or generic-for-2 variant. Phyrexian: accepts the color mana OR deducts 2 life from the casting player.

**Why**: Hybrid symbols are already parsed to e.g. `"W/U"` in `parse_mana_cost` but then ignored in `_can_pay_simple`. The fix is a targeted loop over hybrid/Phyrexian keys. Phyrexian life payment requires access to player state — `can_pay_cost` will need an optional `player: PlayerState | None` parameter.

**Pattern for hybrid** (e.g. `{W/U}`): player has ≥1 W **or** ≥1 U in pool. Remove one of the available color; if neither is available, return False.

**Pattern for hybrid-generic** (e.g. `{2/B}`): player can pay 2 generic **or** pay 1 B. The 2-generic variant is more mana-efficient for the player but the validator only needs to check if either path is affordable.

**Pattern for Phyrexian** (e.g. `{B/P}`): player has 1 B in pool **or** player has ≥2 life remaining after the life payment. Life payment is applied at cast time, not just validation.

**Alternatives considered**:
- Require an explicit `payment` dict for all hybrid/Phyrexian casts — shifts burden to caller (AI, API client) which currently passes `{}` for auto-payment.

---

## Decision 4: Damage Prevention Replacement Effects

**Decision**: Add a `prevention_effects: list[DamagePreventionEffect]` field to `GameState`. Add `DamagePreventionEffect` as a new Pydantic model in `models/game.py`. Detection of permanent-sourced prevention (like "prevent the next N damage") is added to `_get_replacement_effects` in `replacement.py`. A new `check_prevention_effects` pass inside `apply_damage_event` reduces `final_damage` before marking.

**For protection from color**: Check source card's color against the target's protection keywords during `apply_damage_event`. Protection means the damage is entirely prevented.

**For "prevent all combat damage" (Fog-style)**: A `GameState.prevent_all_combat_damage: bool` flag (reset each turn) is the simplest representation. Set it in stack resolution when a Fog-like card resolves; `assign_combat_damage` checks it before applying.

**Why**: The existing `ReplacementEffect` model handles destruction replacement but not damage prevention. Adding `DamagePreventionEffect` as a separate targeted model (with `remaining: int | None` for finite shields, `None` for unlimited) avoids polluting the destroy-replacement path.

**Alternatives considered**:
- Reuse `ReplacementEffect` with a new event type — workable but the model fields don't map well (no `remaining` counter, no color restriction fields).

---

## Decision 5: Full Layer System (Layers 1–5)

**Decision**: Extend `collect_continuous_effects` in `layers.py` to generate effects for layers 1–5 from oracle text patterns, matching the existing pattern used for layers 6–7.

- **Layer 1 (Copy)**: When a permanent has `copy_of_permanent_id` set (new optional field on `Permanent`), generate a layer-1 effect that overwrites the permanent's `card` with the source card's copiable values.
- **Layer 2 (Control)**: Oracle pattern `"you control enchanted creature"` or `"gain control of target creature"` (as an aura effect). Generate a layer-2 effect that changes `perm.controller`.
- **Layer 4 (Type)**: Oracle patterns `"is an artifact in addition"`, `"becomes a [type]"`. Generate a layer-4 effect that modifies `perm.card.type_line`.
- **Layer 5 (Color)**: Oracle patterns `"is [color]"`, `"is all colors"`, `"is colorless"`. Generate a layer-5 effect that modifies `perm.card.colors`.
- **Layer 3 (Text)**: Text-change effects (e.g., Magical Hack) are rare and complex; add a scaffold but no pattern matching for initial implementation (leave empty with comment).

**Why**: The layer framework already iterates all layers; only `collect_continuous_effects` is missing entries for 1–5. Following the existing closure-based pattern (like `_make_ability_remover`, `_make_pt_setter`) makes the additions consistent.

**Alternatives considered**:
- Implement full text-change (layer 3) — very low card coverage, disproportionate complexity. Deferred.

---

## Decision 6: Attack/Block Constraints

**Decision**: Add `attack_constraints: list[AttackConstraint]` and `block_constraints: list[BlockConstraint]` to `GameState`. Derive constraints at legal-actions time from oracle text on permanents (Propaganda, ghostly prison, "must attack", "can't block"). Enforce in legal-actions computation in `game.py`.

**`AttackConstraint` fields**: `source_id`, `affected_id` (specific creature or `"all"`), `constraint_type` (`"must_attack"` | `"cannot_attack"` | `"cost_to_attack"`), `cost: str | None`, `goad_controller: str | None`.

**`BlockConstraint` fields**: `source_id`, `affected_id`, `constraint_type` (`"cannot_block"` | `"cannot_block_evasion"` | `"min_blockers"`), `restriction: str | None`.

**Why**: Storing constraints on GameState (derived from oracle scanning each time legal actions are computed) avoids needing a separate "constraint registration" system. The existing `collect_continuous_effects` pattern shows this is viable.

**Propaganda enforcement**: When "cost to attack" constraint applies to a creature, legal actions omit it from attackers unless the cost is payable from the player's mana pool.

**Goad**: Tracked as a counter key `"goad_by_{controller}"` on `Permanent` — the constraint scanner checks for this counter.

**Alternatives considered**:
- Track constraints only on GameState (register once when a permanent ETBs) — more accurate for edge cases but significantly more infrastructure for the current card set.

---

## Decision 7: Copy Effects on Stack

**Decision**: Add `copy_spell` action: takes `target_stack_object_id`, creates a new `StackObject` with `is_copy=True` and the same `source_card`, `effects`, and optionally new `targets`. Add `phase_skip_flags: dict[str, bool]` to `GameState` to track active phase-skip effects; checked in `advance_step`.

**Copy spell resolution**: When a copy resolves, it uses the same `resolve_top` path in `stack.py`. Since it doesn't come from a hand card, skip the "move to graveyard" step (check `is_copy` flag before graveyard move).

**Phase skipping**: `phase_skip_flags = {"combat": True}` → `advance_step` skips the COMBAT phase steps if the flag is set for the current phase. Clear flags at the end of the turn.

**Why**: `StackObject` already has `is_copy: bool` field — it just needs to be utilized in `resolve_top`. The copy action itself is minimal: clone the StackObject, assign new targets, push to stack.

**Alternatives considered**:
- Deep-copy with new UUID for every field — unnecessary, Pydantic `model_copy` is sufficient.

# Story: Static Abilities (CR 604)

## User Story
As a game engine developer, I want the static ability system to function correctly per the Comprehensive Rules, so that continuous effects from static abilities are applied and maintained correctly using the layer system.

## Context
Static abilities are abilities that do something continuously rather than being activated or triggered. They apply as long as the permanent with the static ability is on the battlefield (unless specified otherwise). Static abilities do not use the stack — they are simply "on" from the moment the permanent enters the battlefield until it leaves (CR 604.1).

Key characteristics:
- Static abilities create continuous effects that modify game rules, power/toughness, abilities, and other characteristics
- They do not use the stack and cannot be responded to (CR 604.1)
- They are applied through the **layer system** (CR 613) which determines the order of effect application
- Layers (in order): 1 — Copy effects, 2 — Control-changing effects, 3 — Text-changing effects, 4 — Type-changing effects, 5 — Color-changing effects, 6 — Ability-adding/removing effects, 7a — Characteristic-defining abilities, 7b — Power/toughness-setting effects, 7c — Power/toughness-changing effects
- Dependency system: if an effect depends on another, the dependent effect is applied after the effect it depends on (CR 613.6)
- "Always-on" activated abilities (abilities with no cost that are always active) are distinct from static abilities — they are activated abilities that can be activated at any time

### Comprehensive Rules Grounding
- **CR 604.1**: "A static ability does something all the time rather than being activated or triggered."
- **CR 604.3**: "A static ability may create a continuous effect that modifies the characteristics of objects, controls which objects can attack or block, or affects the game in other ways."
- **CR 613.1**: "The application of continuous effects that modify characteristics of permanents is handled by the layer system."
- **CR 613.1a-613.1h**: Layers 1-7 with sublayers for power/toughness modifications
- **CR 613.6**: "If two or more effects would be applied to the same object in the same layer, the effects are applied in timestamp order, except that dependencies are applied first."
- **Example card**: Glorious Anthem — "Creatures you control get +1/+1."
- **Example card**: Archetype of Courage — "Creatures you control have first strike. Creatures your opponents control lose first strike and can't have or gain first strike."

## Acceptance Criteria
- [ ] `is_static_ability(oracle_text: str) -> bool` identifies continuous effects (no "when/whenever/at" trigger, no "cost:" activation pattern, no "N+1" loyalty pattern)
- [ ] `get_static_continuous_effects(gs, permanent) -> list[ContinuousEffect]` extracts continuous effect information from a permanent's static abilities
- [ ] Layer system implementation: `apply_continuous_effects(gs) -> GameState` applies all static effects in correct layer order (1-7c)
- [ ] Timestamp ordering within layers: effects applied in timestamp order (CR 613.6)
- [ ] Dependency tracking: effects that depend on other effects are applied after their dependencies (CR 613.6)
- [ ] Layer 6 support: ability-adding/removing static effects correctly grant or remove keyword abilities from affected permanents
- [ ] Layer 7a-7c support: CDA, P/T-setting, and P/T-changing effects resolve correctly
- [ ] Static effects that modify rules (e.g., "Creatures can't attack" or "Players can't cast spells") apply continuously
- [ ] Static ability applies only while source is on the battlefield, unless otherwise specified (CR 604.2)
- [ ] Card type-setting static abilities (e.g., "~ is a creature" regardless of type) use characteristic-defining ability rules
- [ ] Full regression passes

## Dependencies
- None (foundational)

## Status: 🔄 Partial

Implemented: `StaticAbility(ABC)` base class at `ability/staticability.py` with CantAttackBlock, ContinuousPump, HexproofGrant, IndestructibleGrant, ContinuousEffect subclasses. `engine/layers.py` (500 lines) full CR 613 layer system (layers 1-7). `engine/duration.py` for duration tracking.

**Gap**: `_apply_static_abilities()` in sba.py only hard-codes one pattern (`"+1/+1" and "other creatures"`). The vast majority of static ability effects are NOT applied through this pathway. Layer system is not systematically populated from keyword modules. StaticAbility subclasses like HexproofGrant have `pass` bodies.

## Priority: High

## Notes
- The layer system is one of the most complex parts of MTG rules. The engine already has some continuous effect handling in combat (`combat/core.py`), but needs a dedicated layer system module.
- Static abilities are distinct from activated abilities that have no cost — those can still be activated at will (they're just free).
- "Can't" static effects (e.g., "Players can't gain life") are particularly important and interact with replacement effects.
- Forge reference: `StaticAbility` class with layer-based resolution in `forge-game`.

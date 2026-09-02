# Story: Replacement Effects (CR 614)

## User Story
As a game engine developer, I want replacement effects to correctly modify game events using the layer/order system, so that cards like "If you would draw a card, instead..." function per the Comprehensive Rules.

## Context
Replacement effects watch for specific events and replace them with modified versions. They follow a specific ordering system: replacement effects that modify a permanent's controller apply first, then those that modify cost/target, then those that modify damage. When multiple replacement effects try to modify the same event, the affected player or controller of the affected object chooses the order of application (CR 616.1).

### Comprehensive Rules Grounding
- **CR 614.1**: "Replacement effects replace one event with another. They are written as 'If [event] would happen, instead [modified event] happens.'"
- **CR 614.5**: "Some replacement effects are 'self-replacement effects' — they modify how an object enters or leaves a zone."
- **CR 616.1**: "If two or more replacement effects would modify the same event, the player who controls the affected object or the affected player chooses one to apply."
- **CR 614.15**: "Some replacement effects are 'can't' effects. 'Can't' effects prevent replacement effects from applying."
- **Example card**: Thought Reflection — "If you would draw a card, draw two cards instead."

## Acceptance Criteria
- [ ] Replacement effects are registered via `PendingReplacement` or similar model on GameState
- [ ] Replacement effects are categorized as: controller-change, cost, target, damage, other
- [ ] When an event occurs, engine checks for matching replacement effects before applying the event
- [ ] Multiple replacement effects on the same event: affected player/controller chooses order (CR 616.1)
- [ ] "Can't" effects prevent replacement effects from applying (CR 614.15)
- [ ] Self-replacement effects apply automatically (e.g., "enters tapped") (CR 614.5)
- [ ] Replacement effects that modify damage (e.g., "prevent the next 3 damage") interact correctly with prevention effects
- [ ] Pure transform: replacement application returns new GameState via `model_copy(update={...})`
- [ ] Existing `mtg_engine/engine/replacement.py` patterns are used/refactored as needed
- [ ] Integration tests cover: single replacement, multiple replacement order choice, "can't" override, self-replacement effects
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: State-Based Actions (CR 704) — replacement effects often create events checked by SBAs

## Priority: High

## Status: 🔄 Partial

### Gap Description
Replacement effect framework exists with models and basic processing (shield counters, regeneration shields, prevention effects), but missing: CR 614.15 'can\'t' effect override, full CR 616.1 player-choice ordering for multiple replacements, comprehensive draw replacement integration, self-replacement effect patterns beyond shield/regen, and systematic event pipeline for all replacement types.

## Estimated Effort: L

## Notes
- The engine already has `mtg_engine/engine/replacement.py` with initial replacement effect logic — this story refactors it to full CR 614 compliance
- Replacement effects are distinct from triggered abilities: replacement effects PREVENT and REPLACE events rather than triggering after them
- Key pattern: replacement effects are checked DURING event processing, BEFORE the event is applied
- Common replacement patterns: "enters tapped" (self-replacement), "instead draw two cards" (draw replacement), damage prevention
- The ordering system (CR 616) is critical for correctness — effects like "prevent all damage" vs "instead deal double damage" must resolve in the right order

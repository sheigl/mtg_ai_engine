# Story: Triggered Abilities (CR 603)

## User Story
As a game engine developer, I want the triggered ability system to function correctly per the Comprehensive Rules, so that cards using triggered abilities (using "when," "whenever," or "at") automatically trigger and resolve properly.

## Context
Triggered abilities are abilities that automatically trigger when a specific game event occurs. They are written using "When," "Whenever," or "At" followed by a trigger condition and an effect (CR 603.1). Unlike activated abilities, triggered abilities do not require a player to actively activate them — they fire automatically when the trigger condition is met.

Key characteristics:
- Triggered abilities use the words "when," "whenever," or "at" (CR 603.1)
- They automatically go onto the stack when the trigger event occurs (CR 603.3)
- They can be responded to like any other spell/ability on the stack
- Multiple triggers that happen simultaneously are handled by AP/NAP order (CR 603.3b)
- "Intervening if" clauses must be checked both at trigger time and at resolution (CR 603.4)
- Trigger conditions can be specific: "when ~ enters the battlefield," "whenever a creature dies," "at the beginning of your upkeep"

The engine already has a trigger detection system in `mtg_engine/engine/triggers.py` with 32 defined trigger categories, ~18 wired into the engine, and ~95 missing. This story covers the foundational trigger framework — the remaining individual trigger patterns are covered by their own `story-trg-*` files.

### Comprehensive Rules Grounding
- **CR 603.1**: "A triggered ability has a trigger condition and an effect. It is written as 'When/Whenever/At [trigger condition], [effect].'"
- **CR 603.2**: "A triggered ability may be written in a variety of ways. The words 'when,' 'whenever,' and 'at' indicate that a triggered ability is being written."
- **CR 603.3**: "Whenever a game event or game state matches a triggered ability's trigger event, that ability triggers."
- **CR 603.3b**: "If a triggered ability has a condition that must be met when it triggers or resolves, the ability triggers only if the condition is true at the time of the trigger event AND the ability resolves only if the condition is still true when it resolves. (This is the 'intervening if' clause.)"
- **CR 603.7**: "A delayed triggered ability is an ability created by a spell or other ability that triggers at a specific time or event."
- **Example card**: Solemn Simulacrum — "When Solemn Simulacrum enters the battlefield, you may search your library for a basic land card, put that card onto the battlefield tapped, then shuffle."
- **Example card**: Blood Artist — "Whenever Blood Artist or another creature dies, target player loses 1 life and you gain 1 life."

## Acceptance Criteria
- [x] `is_triggered_ability(oracle_text: str) -> bool` detects "when," "whenever," "at" prefix pattern (CR 603.1)
- [x] `parse_trigger_condition(text: str) -> TriggerCondition` extracts the trigger event description from the prefix to the comma
- [x] `parse_trigger_effect(text: str) -> str` extracts the effect text after the trigger condition
- [x] Trigger detection engine (`check_*_triggers` functions) matches game events to registered trigger patterns and queues `PendingTrigger` objects on GameState
- [x] AP/NAP ordering: multiple simultaneous triggers ordered correctly per CR 603.3b (active player first, then non-active player)
- [x] "Intervening if" check: condition verified at both trigger queuing time AND resolution time (CR 603.4)
- [x] Delayed triggered ability framework: ability resolution creates a delayed trigger that fires once (CR 603.7)
- [x] Triggered abilities on the stack can be responded to and countered
- [x] Trigger removal: when source of a triggered ability leaves the zone, the trigger already on the stack still resolves ("leaves the battlefield" clause tracking)
- [x] Full regression passes

## Dependencies
- None (foundational — individual trigger patterns build on this)

## Status: ✅ Complete

Implemented: `engine/triggers.py` (1786 lines) with 30+ trigger categories, 55+ regex patterns, zone-change listener dispatch, PendingTrigger model, APNAP ordering, death triggers for Afterlife/Undying/Persist, TRG-20 pure transform fixes. API endpoints for trigger put/decline. Full stack integration.

## Priority: High

## Notes
- The engine already has partial trigger infrastructure in `mtg_engine/engine/triggers.py` (32 categories, ~18 wired). This story focuses on the core framework: detection, parsing, queuing, AP/NAP ordering, and resolution.
- Individual trigger patterns (sacrifice, life gain/lost, fight, transformed, etc.) are covered by `story-trg-*` files and depend on this foundation.
- The existing `PendingTrigger` model in `models/game.py` should be reviewed for completeness.
- Forge reference: `TriggerHandler` class with trigger condition matching and resolution.

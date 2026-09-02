# Story: Flash (CR 702.8)

## User Story
As a game engine developer, I want cards with flash to be castable at instant speed, so that they can be played in response to other spells, during combat, or at any time a player has priority per CR 702.8.

## Context
Flash is a keyword ability that allows a card to be cast any time its controller could cast an instant. Normally, creatures, artifacts, enchantments, and planeswalkers can only be cast as sorceries (during the controller's main phase when the stack is empty). Flash overrides this timing restriction, allowing the card to be cast at any time the controller has priority, including during an opponent's turn or in response to another spell.

### Comprehensive Rules Grounding
- **CR 702.8a**: "Flash means you may cast this spell any time you could cast an instant."
- **CR 302.5**: "A creature spell can be cast only during the controller's main phase when the stack is empty, unless it has flash."
- **CR 117.1a**: "A player may cast an instant spell any time they have priority."
- **Example card**: Snapback — "Flash (You may cast this spell any time you could cast an instant.)"

## Acceptance Criteria
- [x] `has_flash(card) -> bool` detection (from keyword or oracle text)
- [x] Cards with flash bypass the sorcery-speed timing restriction
- [x] Cards with flash can be cast during any phase/step when controller has priority
- [x] Cards with flash can be cast in response to other spells or abilities
- [x] Cards with flash on an opponent's turn can be cast when controller has priority
- [x] "May be cast as though it had flash" effects work similarly (e.g., "you may cast creature spells as though they had flash")
- [x] Timing validation function `can_cast_spell(gs, card, player) -> bool` respects flash
- [x] Integration tests cover: flash cast on opponent's turn, flash cast in response, flash creature, flash enchantment, instant-speed creature via flash
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- None (standalone keyword that modifies timing restrictions)

## Priority: Low

## Status: ✅ Complete

## Estimated Effort: S

## Notes
- Flash is deceptively simple — it only modifies the TIMING restriction on casting
- "Casting at instant speed" means casting any time you have priority, including during combat, on opponent's turn, or in response to other spells/abilities
- Flash is a static keyword ability, not an activated or triggered ability
- Cards can have flash as a keyword OR have "You may cast this spell as though it had flash" as a characteristic-defining ability
- Some effects give ALL cards of a certain type flash (e.g., "Creature spells you cast have flash")
- The engine's `_compute_legal_actions` function should include flash cards in available casts during instantspeed windows

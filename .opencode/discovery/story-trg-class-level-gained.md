# Story: Class Level Gained Trigger (CR 702.XX)

## User Story
As an MTG engine developer, I want a class-level-gained trigger pattern with check function and engine wiring, so that cards with "Whenever one or more level counters are put on ~" triggered abilities fire correctly.

## Context
No detection regex or check function exists for this trigger. A new trigger pattern must be created following the established pattern in triggers.py. "Class level gained" refers to Class enchantments from Adventures in the Forgotten Realms (AFR) that gain level counters and level up.

### Comprehensive Rules Grounding
- **CR 702.XX**: "Class is a subtype of enchantment. Each Class card has three levels, each with an activated ability that puts a level counter on the Class and additional abilities that are active while the Class has a certain number of level counters."
- **Example card**: *Acclaimed Contender* — "Whenever one or more level counters are put on Acclaimed Contender, you may search your library for a card with mana value equal to the number of level counters on it."

## Acceptance Criteria
- [ ] Add regex pattern to trigger detection in triggers.py
- [ ] Add check function that creates PendingTrigger
- [ ] Wire into level counter placement flow
- [ ] Integration tests
- [ ] No regressions

## Dependencies
- Story guidelines at STORY-GUIDELINES.md

## Priority: Medium

## Estimated Effort: M

## Notes
- Class level triggers fire when level counters are put on a Class enchantment specifically.
- Must distinguish from general +1/+1 counter placement on creatures — this is specifically about level counters.
- All Class enchantments from AFR have three levels with unique abilities at each level.
- Example cards: *Barbarian Class*, *Cleric Class*, *Fighter Class*, *Wizard Class*, *Ranger Class*.

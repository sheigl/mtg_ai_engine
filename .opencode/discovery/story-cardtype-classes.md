# Story: Class Rules (CR 716)

## User Story
As a game engine developer, I want Class rules to function correctly per the Comprehensive Rules, so that Classes enter at level 1, can be leveled up by paying mana, and each level grants additional abilities on the enchantment.

## Context
Classes are enchantment subtypes from Adventures in the Forgotten Realms (2021). A Class enters the battlefield at level 1. Each Class has a level-up cost (or costs) printed on the card. By paying the level-up cost as a sorcery, the Class gains its next level. Each level grants a static ability. The Class's level is tracked with level counters.

### Comprehensive Rules Grounding
- **CR 716.1**: "A Class is an enchantment subtype that can be leveled up."
- **CR 716.2**: "A Class enters the battlefield at level 1."
- **CR 716.3**: "A Class has a level-up cost. Paying this cost adds a level to the Class."
- **CR 716.4**: "Level-up is an activated ability that can be activated only as a sorcery."
- **CR 716.5**: "Each level of a Class grants a static ability. These abilities are cumulative: level 1 abilities plus level 2 abilities."
- **CR 716.6**: "Classes are tracked by level counters. The number of level counters = the current level minus 1."
- **Example card**: Bard Class — Enchantment — Class, "Level 1: {1}{R}: Level up. Level 2: {2}{W}: Level up. Level 3: Creatures you control get +2/+2."

## Acceptance Criteria
- [ ] Class enters the battlefield at level 1 (no level counters yet) (CR 716.2)
- [ ] Level-up cost can be paid at sorcery speed to add a level (CR 716.4)
- [ ] Level counters track the Class's level (level = level counters + 1) (CR 716.6)
- [ ] Static abilities from each level are cumulative — you get all abilities from level 1 up to current level (CR 716.5)
- [ ] Level-up can be activated multiple times until max level is reached
- [ ] Level-up cost may differ for each level (some Classes have different costs for different levels)
- [ ] Class that is removed from battlefield loses all its counters (goes to graveyard as normal enchantment)
- [ ] "Class" subtype grants triggered interactions (e.g., "Class level gained" triggers)
- [ ] Full regression suite passes

## Dependencies
- Story: Enchantment Rules (CR 303) — parent card type rules
- Story: Level Up Keyword (CR 702.84) — level-up mechanic

## Status: 🔄 Partial

Implemented: Level Up keyword for Leveler creatures (CR 702.44) at `ability/keywords/level.py` with full level up cost/effect parsing and active abilities per level.

**Gap**: Strixhaven Class enchantments (CR 716) are NOT implemented. These have a different level-up structure (sorcery-speed activation with static abilities per class level) vs Leveler creatures (counter-based level tracking). `EnchantmentSubtype.CLASS` enum exists but no engine code processes it.

## Priority: Medium

## Notes
- Classes are similar to Level Up creatures (from Zendikar) but on enchantments — the CR 716 mechanics are distinct from CR 702.84 Level Up
- Level 1 is the starting level — there are NO level counters on entry (level counters = current level - 1)
- Level-up costs for Classes are printed as: "Level {N}: {cost}: Level up" — each level may have a different cost
- The static abilities from each level represent what the Class does at that level
- Some Classes have triggered or activated abilities at certain levels, not just static abilities
- "Class" as a creature type also exists (e.g., "Cleric Class" creature) but that's unrelated to this enchantment subtype
- Level-up can be responded to (it uses the stack as an activated ability, except... wait, is it a mana ability? No, it's a regular activated ability)
- If a Class is at max level, its level-up ability can't be activated (no higher level to reach)
- Level counters on Classes can be added/removed by other effects (proliferate, remove counter), changing the active level

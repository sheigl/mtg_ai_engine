# Story: Spell Copy Rules (CR 706)

## User Story
As a game engine developer, I want spell copy rules to function correctly per the Comprehensive Rules, so that effects that copy spells on the stack create proper copies with the option to choose new targets.

## Context
This game action is already documented under the rule story `story-rule-copy-effects.md`. This file serves as an action-oriented reference focused on copying spells (as opposed to permanents or cards).

### Comprehensive Rules Grounding
- **CR 706.10**: "To copy a spell, put a copy of it onto the stack. The copy is not cast."
- **CR 706.10a**: "A copy of a spell becomes a spell on the stack. It has the same characteristics as the original."
- **CR 706.10b**: "The controller of the copy can choose new targets."
- **CR 706.10c**: "Copies are not 'cast' — they don't trigger 'whenever you cast' triggers."
- **CR 706.10d**: "If the original spell has modal choices, the copy has the same choices."
- **Example card**: Reverberate — "Copy target instant or sorcery spell. You may choose new targets for the copy."

## Acceptance Criteria
- [x] See `story-rule-copy-effects.md` for full acceptance criteria specific to spell copying
- [x] `copy_spell(stack_obj, new_controller)` creates a new StackObject on the stack
- [x] Copy has same characteristics: mana cost, text, types, P/T, etc.
- [x] Copy controller may choose new targets (CR 706.10b)
- [x] Copy is not "cast" — no cast triggers (CR 706.10c)
- [x] Copy retains modal choices of the original (CR 706.10d)
- [x] Multiple copies of the same spell are independent
- [x] Storm copies follow the same rules (story-kw-storm.md)

## Dependencies
- story-rule-copy-effects.md (full rules story)
- Casting a Spell (story-action-cast-spell.md) — copies go on the stack
- Storm (story-kw-storm.md)

## Priority: High
## Status: ✅ Complete

## Estimated Effort: L

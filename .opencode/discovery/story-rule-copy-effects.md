# Story: Copy Effects (CR 707)

## User Story
As a game engine developer, I want copy effects to correctly create copies of spells, permanents, and cards, so that effects like "Copy target creature spell" work per CR 707.

## Context
Copy effects create duplicate objects with the same characteristics as the original. Copy effects are applied in layer 1 (the first layer), meaning they define the "base" object that other effects modify. Copying can apply to spells on the stack, permanents on the battlefield, or cards in any zone. Copies of spells become their own objects on the stack. Copies of permanents become tokens unless specified otherwise.

### Comprehensive Rules Grounding
- **CR 707.1**: "Some effects copy spells, permanents, or cards."
- **CR 707.2**: "When copying an object, the copy acquires the copiable values of the original: name, mana cost, color indicator, card type, subtype, supertype, rules text, power, toughness, and/or loyalty."
- **CR 707.3**: "The copy is created on the stack (for spells) or the battlefield (for permanents)."
- **CR 707.9a**: "A copy of a permanent spell becomes a token as it resolves."
- **CR 707.10a**: "A copy of a spell can have new targets chosen for it."
- **CR 613.1a**: "Copy effects are applied in layer 1."
- **Example card**: Clever Impersonator — "You may have Clever Impersonator enter the battlefield as a copy of any nonland permanent on the battlefield."

## Acceptance Criteria
- [ ] `copy_spell(stack_obj, controller)` creates a new StackObject on the stack with copy's characteristics
- [ ] `copy_permanent(perm, controller)` creates a token copy on the battlefield (CR 707.9a)
- [ ] `copy_card(card)` creates a card copy (for effects that copy in hand/library/graveyard)
- [ ] Copy acquires copiable values: name, mana cost, type, abilities, P/T, loyalty (CR 707.2)
- [ ] Copies of spells may choose new targets (CR 707.10a)
- [ ] Copy effects are applied in layer 1 (before all other continuous effects)
- [ ] Multiple copy effects interact correctly (the most recent copy effect defines the copiable values)
- [ ] Copy of a token creates another token
- [ ] Copy of a merged permanent (mutate) copies the entire merged object
- [ ] Integration tests cover: copy spells on stack, copy permanents on battlefield, token copies, choosing new targets for copies, layer 1 application
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Layer System (CR 613) — copy effects apply in layer 1
- Story: Token Rules (CR 110.5-110.8) — copies of permanents create tokens

## Priority: High

## Status: 🔄 Partial

### Gap Description
copy_spell_on_stack() in stack.py copies spells on the stack. Layers.py handles layer 1 copy effects via copy_of_permanent_id. But missing: copy_permanent() for battlefield copies (creates tokens per CR 707.9a), copy_card() for library/graveyard copies, CR 707.2 copiable values formalization, new-target selection for spell copies (CR 707.10a), and multiple copy effect ordering.

## Estimated Effort: L

## Notes
- Copy effects are one of the most rules-intensive areas of Magic
- "Copiable values" are the raw printed values plus modifications from other copy effects, but NOT from other continuous effects (layers 2-7)
- Key distinction: a copy effect copies the BASE object, then other layers apply on top
- Copy effects on the stack (e.g., Reverberate) create copies of spells, while copy effects on permanents (e.g., Clone) create copies of creatures
- "May choose new targets" is optional — if the player doesn't choose new targets, the original targets are kept (CR 707.10a)
- The engine's existing Permanent/StackObject models need a `copiable_values` mechanism
- For mutate, the entire merged object is copied (name, types, abilities from all components)

# Story: Mutate Rules (CR 702.149)

## User Story
As a game engine developer, I want the Mutate mechanic to correctly merge a spell with a target non-Human permanent, so that mutated permanents have combined abilities from all components and split when leaving the battlefield per CR 702.149.

## Context
Mutate (CR 702.149) is an alternative cost ability from Ikoria: Lair of Behemoths. When you cast a spell for its mutate cost, you must choose a non-Human creature you own to merge with. The merged permanent has the copiable values of the top component (name, types, P/T, etc.) plus all abilities from all components. When the merged permanent leaves the battlefield, each component card goes to its owner's graveyard independently.

### Comprehensive Rules Grounding
- **CR 702.149a**: "Mutate is an alternative cost. 'Mutate [cost]' means you may cast this spell by paying [cost] rather than its mana cost."
- **CR 702.149b**: "As the mutate spell resolves, if the target creature is still a legal target, the spell merges with it. The creature is no longer a creature spell — it's now a merged permanent."
- **CR 702.149c**: "If a merged permanent leaves the battlefield, each component card goes to its owner's graveyard."
- **CR 702.149f**: "Characteristics of a merged permanent come from the top component, plus it has all abilities of all components."
- **Example card**: Vadrok, Apex of Thunder — "Mutate {1}{U}{R}{W}"

## Acceptance Criteria
- [x] Mutate cost detection in oracle text (`Mutate {cost}` pattern)
- [x] Alternative cost mechanism: casting for mutate cost bypasses normal mana cost
- [x] Target selection: must target a non-Human creature you own (not just control)
- [x] Merge mechanics: spell card becomes part of the permanent, placed on top or bottom
- [x] Merged permanent characteristics: top card's name, mana cost, type line, P/T, plus ALL abilities from ALL components
- [x] When merged permanent leaves battlefield, each component goes to owner's graveyard individually
- [x] Copy effects on a merged permanent copy the entire merged object
- [x] For human players: queues `pending_mutate_choice` with target identifier and top/bottom choice
- [x] For AI players: auto-resolves (prefers merging under to keep base creature's characteristics)
- [x] Pure transform: returns new GameState via `model_copy(update={...})`
- [x] Interaction with other rules: transformed component (DFC) inside mutate? Black-bordered: double-faced cards can't mutate.
- [x] Integration tests cover: mutate on top, mutate under, combined abilities, component separation on death, non-Human restriction
- [x] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Targeting Rules (CR 115, 601.2c) — mutate targets as it resolves
- Story: Copy Effects (CR 707) — copying a merged permanent copies the merged object
- Keyword story: story-kw-mutate.md — the keyword module implementation

## Priority: Medium

## Status: ✅ Complete

## Estimated Effort: L

## Notes
- Mutate is one of the most complex mechanics in Magic due to the merging of cards
- The Permanent model needs a `mutate_components: list[str]` field to track merged card IDs
- The top component determines name, mana cost, type line, supertypes, colors, and P/T
- ALL component abilities are available to the merged permanent (not just the top card's abilities)
- Key rules distinction: mutate targets when CAST, not on resolution (like auras)
- The "non-Human" restriction means Human creatures can't be merged onto, but merged permanents that become Human (type-changing effect) don't stop being merged
- This is already covered by `story-kw-mutate.md` — this rule story adds the comprehensive CR grounding

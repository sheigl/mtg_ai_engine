# Story: Modal Spells (CR 700.2)

## User Story
As a game engine developer, I want modal spells ("Choose one — ...") to present valid choices to the player during casting, resolve the chosen mode's effects independently, and correctly interact with copying and timing, so that modal cards work per CR 700.2.

## Context
Modal spells and abilities let the player choose one (or more, with entwine) effect from a set of options. The mode is chosen during announcement (CR 601.2b), and only the chosen mode's effects are applied on resolution. Cards with "Choose one —" modes can be copied to add modes, and cards like "Choose two —" allow multiple selections.

### Comprehensive Rules Grounding
- **CR 700.2**: "Some spells and abilities have modal choices. 'Choose one — ...' allows the spell's controller to pick one mode."
- **CR 700.2d**: "Some modal spells say 'Choose two —' or 'Choose three —' — the controller picks that many modes."
- **CR 601.2b**: "The player announces the chosen mode(s) as part of casting a modal spell or activating a modal ability."
- **CR 700.2e**: "If a modal spell is copied, the copy's controller may choose the same or different modes."
- **CR 702.41**: "Entwine — you may choose all modes by paying the entwine cost."
- **Example card**: "Choose one — Draw two cards; or gain 5 life."

## Acceptance Criteria
- [ ] Modal spells are detected during casting with their available modes
- [ ] Player chooses mode(s) during casting/announcement (CR 601.2b)
- [ ] "Choose one": exactly one mode must be chosen
- [ ] "Choose two/three": that many modes must be chosen (distinct unless text says otherwise)
- [ ] Only the chosen mode's effects are applied on resolution
- [ ] Copying a modal spell: copy's controller may choose different modes (CR 700.2e)
- [ ] Entwine: paying entwine cost allows choosing all modes
- [ ] Modes with targets: only the chosen mode's targets need to be legal
- [ ] Partial resolution: if some targets of the chosen mode are illegal, the remaining targets in that mode are still affected
- [ ] Integration tests cover: choose one mode, choose two modes, entwine (all modes), copy with mode change, mode targeting, partial illegality
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Targeting Rules (CR 115, 601.2c) — mode-dependent targeting
- Story: Copy Effects (CR 707) — mode choice when copying

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Basic modal spell support exists: StackObject.modes_chosen field, _apply_spell_effect() applies only chosen modes by splitting oracle text on bullet markers. But missing: 'Choose one/two/three' detection and enforcement during casting, entwine keyword integration (CR 702.41), mode-dependent targeting, modal spell UI in legal actions, and mode re-selection on copy.

## Estimated Effort: M

## Notes
- Modal spells are common in Magic — hundreds of modal cards exist across all sets
- The mode is a characteristic of the spell on the stack (chosen and fixed at announcement)
- Each mode is a separate effect in the spell's text, separated by "or" not "and"
- Targeting is mode-dependent: if mode 1 targets and mode 2 doesn't, the spell has a target only when mode 1 is chosen
- Some modal spells use "Choose one or both" — allows picking 1 or 2 modes
- For "choose X" where X > 1, the same mode can't be chosen multiple times unless text says "you may choose the same mode more than once"
- Entwine is a keyword that specifically interacts with modal spells to allow selecting all modes

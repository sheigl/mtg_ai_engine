# Story: Transform Rules (CR 701.28)

## User Story
As a game engine developer, I want transforming double-faced cards (DFCs) to correctly change between their front and back faces, so that transforming per CR 701.28 works for both triggered transforms (e.g., werewolves) and spell-based transforms.

## Context
Transform is an action that turns a double-faced card (DFC) from its front face to its back face (or vice versa). Only DFCs can transform. Transform is triggered by specific conditions (e.g., "At the beginning of each upkeep, if no spells were cast last turn, transform this creature") or by spells/abilities that say "transform target permanent." The Day/Night cycle also causes certain DFCs to transform.

### Comprehensive Rules Grounding
- **CR 701.28a**: "To transform a permanent, turn it so its other face is up."
- **CR 701.28b**: "Only double-faced cards can transform. A double-faced card has two faces: a front face and a back face."
- **CR 701.28c**: "When a permanent transforms, its characteristics change to those of its other face."
- **CR 711.3**: "A double-faced card enters the battlefield with its front face up unless an effect says otherwise."
- **CR 711.8**: "If a double-faced card leaves the battlefield, it's revealed to all players."
- **Example card**: Huntmaster of the Fells — transforms between its two sides

## Acceptance Criteria
- [ ] Double-faced card detection: `is_double_faced(card) -> bool`
- [ ] DFC has front_face and back_face with separate characteristics
- [ ] DFC enters the battlefield front-face up (CR 711.3)
- [ ] `transform_permanent(gs, perm_id) -> GameState` changes to other face
- [ ] Transform updates: name, mana cost, type, abilities, P/T, etc. to match the other face
- [ ] DFC in non-battlefield zones: only front face is considered
- [ ] DFC leaving battlefield: revealed to all players (CR 711.8)
- [ ] Transform is NOT a new object entering the battlefield — no ETB triggers for the transformed side
- [ ] Effects that say "target creature transforms" can target any DFC (not just those with transform in oracle)
- [ ] Day/Night cycle triggers certain DFCs to transform at specific times
- [ ] Integration tests cover: DFC enters front-face, transform to back, transform to front, transform doesn't trigger ETB, DFC leaves revealed
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Day/Night Cycle (CR 702.148) — day/night triggers transforms
- Game mechanic story: `story-gm-mdfc.md` — the MDFC/transform mechanic overview

## Priority: Medium

## Status: 🔄 Partial

### Gap Description
Card model supports faces list and face_index. _apply_face_to_card() in stack.py applies face characteristics. Day/night module transforms DFCs. But missing: dedicated transform_permanent() function, transform action in legal actions, DFC enters-front-face enforcement, leaving-battlefield reveal, and comprehensive transform testing.

## Estimated Effort: M

## Notes
- This story covers the RULES for transforming, while `story-gm-mdfc.md` covers the MDFC (Modal Double-Faced Cards) game mechanic overview
- Transform is distinct from MDFC (Modal Double-Faced Cards). MDFCs can choose which side to play, while DFCs transform from one side to another based on game conditions
- Key rule: transforming is NOT entering the battlefield — the permanent stays on the battlefield, just with different characteristics
- Because transform doesn't involve zone change, effects that trigger "when this creature enters the battlefield" don't trigger on transform
- Some DFCs have triggered abilities on both faces that trigger transformation
- DFCs in a player's hand show only the front face (except for certain effects that allow looking at hidden zones)
- The Card model needs `front_face: Card` and `back_face: Card` fields (or a `faces` list)
- Transform tokens don't exist (tokens can't have multiple faces)

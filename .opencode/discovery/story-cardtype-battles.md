# Story: Battle Rules (CR 310)

## User Story
As a game engine developer, I want battle rules to function correctly per the Comprehensive Rules, so that battles enter with defense counters, can be attacked by opponents, and are cast as transformed when their defense counters reach 0.

## Context
Battles are a permanent type introduced in March of the Machine (2023). The primary subtype is "Siege." Battles enter the battlefield with defense counters (printed on the card) and are controlled by their owner. Opponents can attack battles; when a battle loses all its defense counters, it is exiled and then cast as its transformed (back) face.

### Comprehensive Rules Grounding
- **CR 310.1**: "A battle is a permanent that protects a player. Siege is a subtype of battle."
- **CR 310.2**: "A battle enters the battlefield with defense counters equal to its printed defense number."
- **CR 310.3**: "A battle's controller is its owner. The protected player is determined by the battle's controller."
- **CR 310.4**: "A battle that loses all defense counters is exiled and then cast as its transformed face."
- **CR 310.5**: "A battle can be attacked by creatures. If a creature attacks a battle, the battle is the defending permanent for that attack."
- **CR 310.6**: "If a battle would go to a graveyard from anywhere, it's exiled instead."
- **CR 310.7**: "Battle subtypes include Siege and may include others in the future."
- **CR 310.8**: "Siege enters under the control of its owner and protects that owner's opponent."
- **Example card**: Invasion of Ikoria — Battle — Siege, defense 4, transforms into "Zilortha, Apex of Ikoria"

## Acceptance Criteria
- [ ] Battle permanents have defense counters equal to printed defense on entry (CR 310.2)
- [ ] Battle controller = owner (CR 310.3)
- [ ] Siege subtype: battle protects the opponent of the battle's controller (CR 310.8)
- [ ] Creatures can attack battles — battle is the defending permanent (CR 310.5)
- [ ] Combat damage to a battle removes defense counters instead of dealing "damage" (CR 310.4)
- [ ] Non-combat damage can also reduce defense counters (e.g., "Deal 3 damage to target battle")
- [ ] When defense counters reach 0: exile the battle, then cast the transformed face (CR 310.4)
- [ ] If a battle would go to a graveyard from anywhere, it's exiled instead (CR 310.6)
- [ ] The transformed face of a battle is cast as a spell (uses the stack, can be countered)
- [ ] Full regression suite passes

## Dependencies
- Story: Transform Rules (CR 711) — modal double-faced card transformation
- Story: Combat System (CR 506-511) — attacking battles

## Status: ❌ Not Implemented

Not implemented: `models/battle.py` exists with `BattleModel` (defense counters, protector, subtype, parser). `CardType.is_battle()` and `CardType.is_siege()` enums defined. But there is **zero engine integration** — defense counters not tracked on Permanent, no `put_permanent_onto_battlefield()` integration for battles, no combat rules for attacking battles, no SBA for defense counters reaching 0.

## Priority: High

## Notes
- The existing `mtg_engine/models/battle.py` has a `BattleModel` with `from_type_line()` and defense counter fields
- `mtg_engine/models/card_type.py` has `BattleSubtype.SIEGE` and `CardType.is_battle()` and `CardType.is_siege()` helper methods
- Battles use defense counters — NOT loyalty counters (they are fundamentally different)
- When a battle is exiled and cast as transformed, the transformed face is a different card type (usually a creature)
- The "protected player" for a Siege is the controller's opponent — this means if control of the battle changes, the protected player changes
- Battles cannot have "summoning sickness" because they don't have tap abilities or attack — they only get attacked
- A battle with 0 defense entering the battlefield would immediately trigger the exile-and-cast progression
- Copy effects on battles need careful handling (the copy enters with defense counters of the copy)
- The attackable-battle mechanic requires combat system modifications to allow attacking permanents instead of just players

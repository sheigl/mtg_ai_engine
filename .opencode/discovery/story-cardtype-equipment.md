# Story: Equipment Rules (CR 301.5)

## User Story
As a game engine developer, I want Equipment rules to function correctly per the Comprehensive Rules, so that Equipment can be attached to creatures at sorcery speed via the Equip ability and stays on the battlefield when its equipped creature dies.

## Context
Equipment is an artifact subtype that can be attached to creatures. Unlike Auras, Equipment does NOT target on cast — it enters the battlefield as a normal artifact. The Equip ability (activated at sorcery speed) attaches it to a creature. If the equipped creature leaves the battlefield, the Equipment remains on the battlefield unattached. Equipment doesn't become tapped when the equipped creature becomes tapped.

### Comprehensive Rules Grounding
- **CR 301.5**: "An Equipment is an artifact subtype that can be attached to a creature. It doesn't become tapped when the equipped creature does."
- **CR 301.5a**: "An Equipment's controller may pay its equip cost to attach it to a creature they control."
- **CR 301.5b**: "If an Equipment would be put onto the battlefield attached to a creature, it enters unattached."
- **CR 301.5c**: "An Equipment that's also a creature can't equip a creature (but can be attached)."
- **CR 702.6**: "Equip — {cost}: Attach target Equipment you control to target creature you control. Activate only as a sorcery."
- **CR 702.6c**: "If an Equipment leaves the battlefield, any creature it was attached to remains unchanged. If a creature leaves the battlefield, the Equipment remains on the battlefield."
- **Example card**: Sword of Fire and Ice — Artifact — Equipment, "Equipped creature gets +2/+2 and has protection from red and from blue."

## Acceptance Criteria
- [x] Equipment does NOT target on cast — enters battlefield as a normal artifact
- [x] Equip cost can be paid at sorcery speed to attach to a creature (CR 702.6)
- [x] Only the Equipment's controller can activate the Equip ability
- [x] Equipment attaches to a creature and stays attached across turns
- [x] Equipment does NOT become tapped when equipped creature becomes tapped (CR 301.6)
- [x] When equipped creature leaves the battlefield, Equipment remains on battlefield unattached (CR 702.6c)
- [x] When Equipment leaves the battlefield, equipped creature is unaffected
- [x] Equipment that is also a creature cannot equip (CR 301.5c)
- [x] A creature can be equipped by multiple Equipment
- [x] Equipped creature bonuses (power/toughness/abilities) applied via continuous effects
- [x] Full regression suite passes

## Dependencies
- Story: Equip Keyword (CR 702.6) — detailed equip ability rules
- Story: Artifact Rules (CR 301) — parent card type rules

## Status: ✅ Complete

Implemented: Covers under Artifact story. Equipment model (`models/artifact.py`), Equip keyword (`ability/keywords/equip.py`), SBA detach (`sba.py:277-298`).

## Priority: High

## Notes
- The existing `mtg_engine/models/artifact.py` has `can_equip()` and `EquipmentModel` class
- `mtg_engine/models/card_type.py` has `ArtifactSubtype.EQUIPMENT` and `CardType.is_equipment()` helper
- Equipment is fundamentally different from Auras in that:
  - Equipment doesn't target on cast (Auras do)
  - Equipment stays when creature leaves (Auras go to graveyard)
  - Equipment can be moved between creatures (Auras are locked once attached)
- The Equip ability can be activated at sorcery speed and targets both the Equipment and a creature
- Some Equipment have "Equip [creature type]" or "Equip [cost]" with restrictions
- Living Weapon keyword equips the created token automatically (see story-kw-living-weapon.md)
- Equipment bonuses are continuous effects that modify the equipped creature
- "Reconfigure" from Neon Dynasty is a variant that turns Equipment into creatures and back

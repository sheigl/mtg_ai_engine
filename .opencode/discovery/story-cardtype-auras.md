# Story: Aura Rules (CR 303.4)

## User Story
As a game engine developer, I want Aura rules to function correctly per the Comprehensive Rules, so that Auras target on cast, enter attached, and are put into graveyards when they are illegally attached.

## Context
Auras are enchantment subtypes that become attached to permanents (usually creatures, lands, or players). When an Aura spell is cast, it targets the thing it will enchant. On resolution, it enters the battlefield attached to that target. If the target becomes illegal (hexproof, shroud, protection), the Aura spell doesn't resolve. If an Aura in play is no longer attached to something legal, it's put into the graveyard as a state-based action.

### Comprehensive Rules Grounding
- **CR 303.4**: "Aura is an enchantment subtype. An Aura enters the battlefield attached to the permanent or player it targets."
- **CR 303.4a**: "An Aura spell targets the permanent or player it will enchant. If the target is illegal when the spell resolves, the Aura spell doesn't resolve."
- **CR 303.4b**: "If an Aura is put onto the battlefield without being cast, its controller chooses what it will enchant as it enters."
- **CR 303.4c**: "An Aura that can't enchant its target is put into its owner's graveyard as a state-based action."
- **CR 303.4d**: "Enchant is a keyword that defines the type of permanent or player an Aura can enchant."
- **CR 303.5**: "If an Aura is simultaneously also a creature, it can't enchant anything (but can still be attached)."
- **CR 702.5a**: "Enchant [quality] — The Aura may enchant only a permanent or player with that quality."
- **Example card**: Unholy Strength — Enchantment — Aura, "Enchant creature. Enchanted creature gets +2/+1."

## Acceptance Criteria
- [x] Aura spells target the permanent/player they will enchant (CR 303.4a)
- [x] Aura spell with illegal target on resolution doesn't resolve (goes to graveyard)
- [x] Auras put onto battlefield without being cast use ETB choice to determine target (CR 303.4b)
- [x] Aura ceases to exist as SBA if attached to illegal permanent (CR 303.4c)
- [x] "Enchant [quality]" restrictions enforced (Enchant creature, Enchant land, Enchant player, etc.)
- [x] Aura attached state tracked on both the Aura and the enchanted permanent (e.g., `attached_to` field)
- [x] When enchanted permanent leaves battlefield, the Aura is put into graveyard as SBA
- [x] Creature Auras can't enchant but can be attached via other means (CR 303.5)
- [x] Hexproof/shroud on the target prevents Aura attachment from opponents
- [x] Protection removes Auras via SBA (CR 702.16)
- [x] Full regression suite passes

## Dependencies
- Story: Enchant Keyword (CR 702.5) — defines enchant quality restrictions
- Story: State-Based Actions (CR 704) — illegal attachment SBA
- Story: Targeting Rules (CR 115, 601.2c) — Aura targeting

## Status: ✅ Complete

Implemented: Aura subtype rules covered under Enchantment story. `AuraTarget` model, aura attachment at `stack.py:602-624`, SBA for illegal targets at `sba.py:251-275`.

## Priority: High

## Notes
- The existing `mtg_engine/models/enchantment.py` has `can_enchant_permanent()` helper and `is_aura_type_line()` functions
- Aura attachments are modeled via an `attached_to: Optional[str]` field on Permanent (the permanent ID it's attached to)
- When an Aura enters without being cast (e.g., "put onto battlefield" from "Zur the Enchanter"), the controller chooses a legal target — this should use the ETB choice system pattern
- Curse Auras enchant players, not permanents — this needs special handling
- Bestow creatures are Aura spells but become creature permanents if not cast as Auras — see story-kw-bestow.md
- The "attached creature gets +X/+Y" effect from Auras is a continuous effect that should use the layer system
- Auras that have "flash" can be cast at instant speed, but still target on cast
- For Auras that can enchant any permanent (no Enchant restriction), use "enchant permanent"

# Story: Enchantment Rules (CR 303)

## User Story
As a game engine developer, I want enchantment rules to function correctly per the Comprehensive Rules, so that enchantments provide continuous effects, Auras attach to permanents, and enchantment subtypes (Sagas, Classes, etc.) work correctly.

## Context
Enchantments are permanents that usually provide ongoing effects. They can be Auras (which enchant a permanent or player), have various subtypes like Saga (chapter abilities), Class (level-up), Curse (enchant player), and more. Some enchantments are also creatures ("enchantment creatures") or artifacts ("enchantment artifacts").

### Comprehensive Rules Grounding
- **CR 303.1**: "An enchantment is a permanent that usually provides ongoing effects."
- **CR 303.2**: "An enchantment may also be a creature, artifact, or have other types."
- **CR 303.3**: "An enchantment enters the battlefield unless its type says otherwise."
- **CR 303.4**: "Aura is an enchantment subtype. An Aura enters the battlefield attached to the permanent or player it targets. See rule 702.5, 'Enchant.'"
- **CR 303.4a**: "An Aura spell targets the permanent or player it will enchant. If the target is illegal when the spell resolves, the Aura spell doesn't resolve."
- **CR 303.4b**: "If an Aura is put onto the battlefield without being cast, its controller chooses what it will enchant as it enters."
- **CR 303.4c**: "An Aura that can't enchant its target is put into its owner's graveyard as a state-based action."
- **CR 303.5**: "If an Aura is simultaneously also a creature, it can't enchant anything (but can be attached)."
- **Example card**: Pacifism — Enchantment — Aura, "Enchant creature. Enchanted creature can't attack or block."

## Acceptance Criteria
- [x] Enchantments enter the battlefield and provide continuous effects
- [x] Enchantment creatures follow both enchantment and creature rules
- [x] Enchantment artifacts follow both enchantment and artifact rules
- [x] Aura targeting on cast: Aura spells target the permanent/player they will enchant (CR 303.4a)
- [x] Aura ETB without being cast: controller chooses what to enchant (CR 303.4b)
- [x] Aura put into graveyard as SBA if not attached to legal target (CR 303.4c)
- [x] Enchantment creature Auras can't enchant (CR 303.5)
- [x] Enchantment subtypes (Aura, Saga, Class, Curse, etc.) tracked correctly
- [x] "Enchant creature"/"Enchant land"/etc. restrictions enforced on attachment
- [x] Full regression suite passes

## Dependencies
- Story: Aura Rules — detailed Aura mechanics
- Story: State-Based Actions (CR 704) — Aura illegal attachment SBA
- Story: Enchant Keyword (CR 702.5) — Enchant ability

## Status: ✅ Complete

Implemented: `AuraTarget` model at `models/enchantment.py` with `parse_aura_target()` for enchant X patterns. Aura attachment at `stack.py:602-624` with P/T bonuses and keyword grants. SBA for illegal aura targets (`sba.py:251-275`). Full CR 613 layer system at `layers.py` with layers 1-7, timestamps, dependency ordering. `StaticAbility` base class at `ability/staticability.py`.

## Priority: High

## Notes
- `mtg_engine/models/enchantment.py` has helper functions including `can_enchant_permanent()` and `is_aura_type_line()`
- `mtg_engine/models/card_type.py` has `EnchantmentSubtype` enum with AURA, BACKGROUND, CARTOUCHE, CASE, CLASS, CURSE, ESTATE, ROLE, RUNE, SAGA, SHRINE, SHIRE
- Curse is an Aura subtype that enchants a player rather than a permanent — this needs special handling for player-targeting
- Auras that enchant players (like Curse subtypes) need to track which player they're attached to
- A creature that is both an Aura and a creature can't enchant anything — this is a complex edge case (e.g., "Boonweaver Giant" style effects)
- The engine's existing Aura attachment logic needs to be verified against CR 303.4

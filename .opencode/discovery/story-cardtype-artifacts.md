# Story: Artifact Rules (CR 301)

## User Story
As a game engine developer, I want artifact rules to function correctly per the Comprehensive Rules, so that artifacts are colorless by default, can be creatures, and artifact subtypes like Equipment and Fortification work correctly.

## Context
Artifacts are colorless permanents that can have various abilities. They are traditionally colorless unless a colored mana cost includes colored mana. Artifacts can be creatures (e.g., artifact creatures like "Golem" tokens), and have subtypes including Equipment (can be attached to creatures), Fortification (can be attached to lands), and Vehicles (can become creatures).

### Comprehensive Rules Grounding
- **CR 301.1**: "An artifact is a permanent that can have various abilities."
- **CR 301.2**: "An artifact is colorless by default, even if its mana cost includes colored mana."
- **CR 301.3**: "If a non-creature artifact is also a creature, it's an artifact creature. Its colors are determined by its mana cost."
- **CR 301.4**: "Artifact creatures are subject to all rules governing both artifacts and creatures."
- **CR 301.5**: "Equipment is an artifact subtype that can be attached to a creature. See rule 702.6, 'Equip.'"
- **CR 301.6**: "An Equipment doesn't become tapped when the equipped creature does."
- **CR 301.7**: "Vehicle is an artifact subtype that can become an artifact creature. See rule 702.121, 'Crew.'"
- **Example card**: Sol Ring — "{T}: Add {C}{C}"

## Acceptance Criteria
- [x] Artifact permanents are colorless by default (CR 301.2)
- [x] Artifact creatures follow both artifact and creature rules (CR 301.4)
- [x] Equipment subtype correctly attaches to creatures via Equip and stays attached
- [x] Equipment remains on battlefield when equipped creature leaves (unlike Auras)
- [x] Equipment doesn't become tapped when equipped creature becomes tapped (CR 301.6)
- [x] Vehicle subtype starts as non-creature and becomes creature via Crew (CR 301.7)
- [x] Fortification subtype attaches to lands (analogous to Equipment for lands)
- [x] Artifact subtypes (Equipment, Vehicle, Fortification) parsed from type_line
- [x] Full regression suite passes

## Dependencies
- Story: Equip Keyword (CR 702.6) — Equipment attachment
- Story: Crew Keyword (CR 702.121a) — Vehicle animation
- Story: Fortify Keyword (CR 702.54a) — Fortification attachment

## Status: ✅ Complete

Implemented: Colorless by default (`card_factory.py:183`). Equipment model at `models/artifact.py:49-65` with equip cost parsing. `Equip` keyword at `ability/keywords/equip.py`. Vehicle model at `models/artifact.py:68-98` with crew/uncrew. `Crew` keyword at `ability/keywords/crew.py`. SBA equipment detach (`sba.py:277-298`). `crewed_until_end_of_turn` on Permanent (`models/game.py:129`).

## Priority: High

## Notes
- The existing `mtg_engine/models/artifact.py` has helper functions: `can_equip()`, `is_creature_type_line()`
- `mtg_engine/models/card_type.py` has `ArtifactSubtype` enum with `EQUIPMENT`, `FORTIFICATION`, `VEHICLE`
- Equipment does NOT tap when the equipped creature taps — this is a common rules gotcha
- When an Equipment creature dies, the Equipment unattaches first, then is put into graveyard as a separate permanent
- Vehicles have base power/toughness for Crew cost calculation
- Fortifications are to lands what Equipment is to creatures — an uncommon subtype
- Indestructible artifact creatures (e.g., "Darksteel Colossus") follow artifact AND creature indestructible rules

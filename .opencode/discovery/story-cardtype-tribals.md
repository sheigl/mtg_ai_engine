# Story: Tribal Rules (CR 308.2)

## User Story
As a game engine developer, I want tribal rules to function correctly per the Comprehensive Rules, so that tribal cards have creature types but aren't creatures, and the tribal type allows creature-type-referencing effects on non-creature spells.

## Context
Tribal is a card type introduced in Lorwyn (2007) and only appears in that block (and some reprints). A tribal card has a creature type (like Faerie, Goblin, etc.) but is NOT a creature itself. For example, "Bitterblossom" is a Tribal Enchantment — Faerie. Tribal allows non-creature cards to have creature types, making them eligible for creature-type-based interactions (e.g., "Goblin" effects).

### Comprehensive Rules Grounding
- **CR 308.2**: "A tribal card is a spell that has a creature type but isn't a creature."
- **CR 308.2a**: "Tribal is a card type. Each tribal card has the 'tribal' card type and at least one other card type."
- **CR 308.2b**: "Tribal cards have creature subtypes but aren't creatures. They follow the rules for their other card types."
- **CR 308.2c**: "Tribal spells are subject to the timing restrictions of their other card types (e.g., Tribal Sorcery follows sorcery timing)."
- **CR 308.2d**: "Tribal is not a permanent type — it's a spell type. Tribal cards go to the graveyard as normal when they resolve."
- **Example card**: Bitterblossom — Tribal Enchantment — Faerie

## Acceptance Criteria
- [ ] Tribal is recognized as a card type alongside its paired type (e.g., Tribal Enchantment, Tribal Sorcery)
- [ ] Tribal cards have creature subtypes parsed from the type line
- [ ] Tribal cards follow the rules of their non-tribal type (e.g., Tribal Enchantment follows enchantment rules)
- [ ] Creature-type-referencing effects (e.g., "Goblin spells cost {1} less") apply to Tribal cards with that creature type
- [ ] Tribal is NOT a permanent type — Tribal Sorcery/Instant go to graveyard on resolution like normal
- [ ] Tribal Enchantments enter the battlefield as enchantments (and keep their creature subtypes)
- [ ] "Tribal" is tracked in the card's type_line and parsed correctly by `parse_type_line()`
- [ ] Full regression suite passes

## Dependencies
- Story: Creature Types (CR 302 subtypes) — creature type system used by Tribal
- Story: Sorcery Rules / Instant Rules / Enchantment Rules depending on paired type

## Status: ❌ Not Implemented

Not implemented: No `CoreType` for Tribal. Only `Supertype.TRIBAL` exists at `card_type.py:34`. Zero engine processing for Tribal card type rules.

## Priority: Medium

## Notes
- Tribal was only used in the Lorwyn/Shadowmoor blocks and a few supplemental products (Modern Horizons)
- The main purpose of Tribal is to give non-creature cards a creature type for tribal synergies
- `mtg_engine/models/card_type.py` does NOT currently have a `CoreType.TRIBAL` — the CoreType enum is marked as "Spell" instead
- The existing `CoreType` enum has: `SPELL = "Spell"` — this may need updating or may already handle Tribal via other means
- Tribal Enchantments are permanent (they stay on the battlefield), while Tribal Sorceries and Instants are not
- Bitterblossom (Tribal Enchantment — Faerie) triggers "Faerie" effects while being an enchantment on the battlefield
- "Tarfire" (Tribal Instant — Goblin) is a Goblin spell for "Goblin" tribal effects
- Since Tribal cards are primarily a Lorwyn block oddity, implementation priority may be low unless specifically needed

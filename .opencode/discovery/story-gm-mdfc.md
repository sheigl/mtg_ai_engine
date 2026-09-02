# Story: MDFC / Transform (CR 711) — Multi-Face Cards

## User Story
As a player, I want Modal Double-Faced Cards (MDFCs) and transform cards fully supported — correct face selection on cast, zone tracking for both faces, and transform effects — so that cards like Birgi, God of Storytelling and Jace, Vryn's Prodigy work correctly.

## Context
**Status: ✅ Complete**

Full CR 711 Multi-Face Card support with zone tracking and transform logic:

- **Face selection on cast**: `stack.py` `_apply_spell_effect()` handles multi-face cards (split cards, MDFCs, aftermath) by selecting the correct card face via `face_index` parameter.
- **`_apply_face_to_card(card, card_face)`**: Copies face-specific attributes (name, mana_cost, type_line, oracle_text, power, toughness, loyalty, colors) from card face data onto the base card.
- **`_resolve_mdfc_cast(card)`**: Helper that resolves the front and back faces of an MDFC for casting.
- **Zone tracking**: Cards maintain their identity across zones; `face_index` tracks which face is currently active.
- **Day/Night integration**: `_transform_daybound_permanents()` in `daynight.py` uses `face_index` to flip DFCs on day/night transitions.
- **Adventure support**: Cards with `card_layout == "adventure"` use `face_index=1` for the adventure half.

## Acceptance Criteria
- [x] MDFC face selection on cast via face_index parameter
- [x] `_apply_face_to_card()` copies face-specific attributes (name, mana_cost, type_line, oracle_text, P/T, loyalty, colors)
- [x] `_resolve_mdfc_cast()` handles front/back face resolution
- [x] Face index tracked on permanents for transform effects
- [x] Daybound/nightbound permanents use face_index for day/night transformation
- [x] Adventure cards use face_index=1 for adventure half
- [x] Zone tracking preserves card identity across zone changes with face information
- [x] Test coverage in `tests/test_020/test_020_split_cards.py` (MDFC section)

## Dependencies
- Day/Night Cycle (story-gm-day-night.md) — daybound/nightbound DFCs transform via day/night transitions
- Card data model (Card.faces field)

## Priority: High | Effort: Completed ✅

## Notes
- Key files: `mtg_engine/engine/stack.py` (lines 107-113, 1860-1889), `mtg_engine/engine/daynight.py` (lines 66-71)
- Card model has `faces: list[CardFace]` field for storing alternative faces
- CardFace model includes: name, mana_cost, type_line, oracle_text, power, toughness, loyalty, colors, flavor_text
- MDFC integration predates the story system — was part of the original engine development

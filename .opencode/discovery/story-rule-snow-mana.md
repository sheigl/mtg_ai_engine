# Story: Snow Mana / Snow Permanents (CR 205.4g)

## User Story
As a game engine developer, I want snow mana and snow permanents to be tracked correctly, so that snow mana matters for cards that require snow mana or care about snow permanents, and mana produced by snow sources is correctly tagged.

## Context
Snow is a supertype (like "basic," "legendary," "world") that appears on some permanents. Snow mana is mana produced by snow sources. Some cards specifically require snow mana or check for snow permanents. Snow-covered basics are variants of basic lands with the Snow supertype. The snow supertype matters for cards like Arcum's Astrolabe (which filters snow mana) and other snow-matters cards.

### Comprehensive Rules Grounding
- **CR 205.4g**: "Snow is a supertype. 'Snow' is not a card type, not a creature type, and not a subtype. Snow permanents have special characteristics as defined by other rules."
- **CR 108.4**: "Snow mana is mana produced by a snow source."
- **CR 202.2c**: "{S} is a snow mana symbol. It represents a cost that can be paid only by snow mana."
- **Example card**: Arcum's Astrolabe — "Snow artifact" — "Sacrifice Arcum's Astrolabe: Draw a card."

## Acceptance Criteria
- [ ] Snow supertype is recognized on permanents (`is_snow(perm) -> bool`)
- [ ] Snow mana is tracked on ManaPool with a `snow: bool` tag for each mana slot
- [ ] Mana produced by snow permanents is tagged as snow mana
- [ ] Mana from non-snow sources is NOT tagged as snow mana
- [ ] {S} in mana costs requires snow mana to pay
- [ ] Snow-covered basics (snow-covered Plains, Island, Swamp, Mountain, Forest) have supertype "snow"
- [ ] Snow permanents count for "snow matters" cards (e.g., "for each snow permanent you control")
- [ ] Cards with snow in their name but not the supertype (e.g., "Snow Devil") are NOT snow permanents
- [ ] Integration tests cover: snow mana production, {S} payment, snow permanent detection, non-snow mana rejection for {S}, snow-covered basics
- [ ] Full regression suite passes (2776+ tests)

## Dependencies
- Story: Mana Cost / Mana Value (CR 107.4, 202) — {S} mana symbol parsing
- Story: Color Identity (CR 903.4) — {S} does not add to color identity

## Priority: Medium

## Status: ❌ Not Implemented

### Gap Description
parse_mana_cost() handles {S} snow symbol and ManaPool has snow/snow_by_color fields, but there is no is_snow() helper, no snow mana tracking on production, no {S} cost payment enforcement, no snow permanent detection logic, and no snow-mana-matters gameplay. The snow fields exist in models but are unused by engine code.

## Estimated Effort: M

## Notes
- Snow is NOT a color identity contributor — {S} has no color identity impact
- Snow-covered basics have full basic land functionality PLUS the Snow supertype
- Snow permanents can still produce non-snow mana (regular {W} from snow-covered plains)
- The snow supertype appears only on permanents (not spells on the stack, though they produce snow permanents when they resolve)
- Key distinction: "Snow" in a card's name does NOT make it a snow permanent — only the supertype does
- Modern Horizons 1 & 2 heavily feature snow mechanics
- The engine's ManaPool model needs a `snow: bool` field or a `mana_type: str` field to distinguish snow mana

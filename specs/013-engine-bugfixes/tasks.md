# Tasks: Engine Bug Fixes

**Source**: Issues discovered during heuristic AI gameplay testing (post-012 release).
**Scope**: MTG rules engine correctness — combat damage, ability parsing.

---

## Bug Fixes

- [X] T001 Fix `assign_combat_damage` in `mtg_engine/engine/combat.py` — change `if assignments is None` to `if not assignments` so an **empty list** also triggers auto-assignment (CR 510.1); previously the game loop sent `assignments=[]` which bypassed auto-assignment and dealt zero damage, causing games to stall indefinitely at the combat damage step
- [X] T002 Fix ability parser in `mtg_engine/card_data/ability_parser.py` — add `_strip_reminder(text) -> str` helper that removes trailing inline reminder text `(…)` before keyword matching; apply it in both `_try_parse_keywords` and the single-keyword path in `_parse_segment`; fixes `UnparsedAbility` warnings for cards like `"Trample (This creature can deal excess combat damage…)"`, `"Flying (This creature can only be blocked…)"`, etc. — keywords with reminder text are now correctly parsed as `KeywordAbility`

---

## Root Causes

### T001 — Combat damage stall
`assign_combat_damage(gs, assignments=[])` hit the `else` branch (validate provided assignments) with an empty list, which validated successfully but assigned nothing. The game advanced past the damage step with no damage dealt, then looped.

**Fix**: `if not assignments:` treats both `None` and `[]` as "auto-assign".

### T002 — Keyword reminder text
Scryfall oracle text for many keywords includes inline reminder text on the same line, e.g.:
```
Trample (This creature can deal excess combat damage to the player or planeswalker it's attacking.)
```
The parser was checking the full string against the `KEYWORDS` frozenset, which only contains bare names. `_strip_reminder` removes the parenthetical suffix before matching.

This also affects deathtouch, lifelink, flying, vigilance, and any other keyword with Scryfall reminder text. Without the fix, these keywords are silently treated as `UnparsedAbility` and the engine ignores them (no trample damage, no flying restriction on blockers, etc.).

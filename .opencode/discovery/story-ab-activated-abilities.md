# Story: Activated Abilities (CR 602)

## User Story
As a game engine developer, I want the activated ability system to function correctly per the Comprehensive Rules, so that cards using activated abilities (written as "[cost]: [effect]") resolve properly in gameplay.

## Context
Activated abilities are abilities that a player can choose to activate at the appropriate time by paying a cost. They are always written in the format "[cost]: [effect.] [Activation instructions.]" per CR 602.1. The cost comes before the colon, and the effect comes after. Activated abilities can be activated any time the player has priority (sorcery-speed by default, but can be modified to instant-speed by abilities or other effects).

Key subtypes of activated abilities covered by this story include:
- **Normal activated abilities** — e.g., "{T}: Add {G}"
- **Planeswalker loyalty abilities** — handled separately by CR 606 (see Loyalty Abilities story)
- **Mana abilities** — handled separately by CR 605 (see Mana Abilities story)

The engine must support parsing the cost:effect format, determining when an ability can be activated (timing restrictions), paying the cost, and resolving the effect. The cost can include mana, tapping, sacrificing, life payment, discarding, removing counters, or any combination thereof. Some activated abilities are "always-on" (no activation restriction other than having priority) — these are distinct from static abilities.

### Comprehensive Rules Grounding
- **CR 602.1**: "An activated ability is written as '[cost]: [effect.] [Activation instructions.]'"
- **CR 602.5a**: "A creature's activated ability with the tap symbol or the untap symbol in its activation cost can't be activated unless the creature has been under its controller's control continuously since the beginning of their most recent turn. A creature can't be affected by this restriction unless it's been on the battlefield continuously since the beginning of their most recent turn." (summoning sickness restriction)
- **CR 602.5b**: "An activated ability can be activated any time a player has priority, except during the casting of a spell or during the activation of an ability, unless it's a mana ability or a special action."
- **Example card**: Llanowar Elves — "{T}: Add {G}."
- **Example card**: Sakura-Tribe Elder — "Sacrifice Sakura-Tribe Elder: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle."

## Acceptance Criteria
- [ ] `parse_activated_ability(text: str) -> ActivatedAbility | None` extracts cost string and effect string from colon-delimited format
- [ ] `can_activate(gs, perm_id, player_name) -> bool` checks timing restrictions (priority, summoning sickness for tap/untap symbol costs)
- [ ] `activate(gs, perm_id, player_name) -> GameState` pays the cost, applies the effect, returns new GameState via pure `model_copy(update=...)` transform
- [ ] Cost payment supports: mana cost deduction, tapping, sacrificing, life payment, discarding, counter removal
- [ ] Sorcery-speed activated abilities cannot be activated during an opponent's turn or during combat unless they have an instant-speed grant
- [ ] Summoning-sickness check: creatures with tap/untap symbol in cost cannot activate unless controlled since beginning of most recent turn
- [ ] Activated abilities on the stack can be responded to (unlike mana abilities)
- [ ] API integration: `POST /game/{id}/choice` resolves activated ability choices queued for human players
- [ ] AI auto-resolution: bot player evaluates whether to activate based on game state heuristics
- [ ] Full regression passes

## Dependencies
- None (foundational — all other ability types may reference this)

## Status: 🔄 Partial

Implemented: `_ACTIVATED_RE` regex parser at `ability_parser.py:131-134`. `POST /activate` endpoint with tap/mana cost payment and timing validation. Legal actions iterate permanents and extract activated abilities. `ability/cost.py` hierarchy for cost types. `ability/timing.py` (185 lines) with `TimingRestriction` and `can_activate()`.

**Gap**: The `POST /activate` endpoint only handles `{T}` and mana costs — it does NOT process sacrifice, discard, exile, or life costs through the `cost.py` hierarchy. The rich cost-engine classes exist but are NOT wired into the API endpoint.

## Priority: High

## Notes
- Activated abilities are a core ability type. The engine's `_apply_single_effect_text()` in `stack.py` already handles some effect text, but the activation framework (cost parsing, timing restrictions) needs to be built as a unified system.
- Distinguish from mana abilities (CR 605) which don't use the stack.
- Distinguish from triggered abilities (CR 603) which fire automatically.
- Forge reference: `ForgeAbility` class with `getActivatedAbility()` pattern.

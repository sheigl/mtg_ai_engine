# Story: Activating an Ability (CR 602)

## User Story
As a game engine developer, I want activated abilities to function correctly per the Comprehensive Rules, so that abilities written as "[cost]: [effect]" can be activated by players when they have priority and resolve properly through the stack.

## Context
Activated abilities follow a similar process to casting spells but with key differences. They do not involve moving a card to the stack (the ability goes on the stack, not the card), and they have distinct timing restrictions including summoning sickness for creatures with tap/untap symbols.

### Comprehensive Rules Grounding
- **CR 602.1**: "An activated ability is written as '[cost]: [effect.] [Activation instructions.]'"
- **CR 602.2**: "To activate an ability is to put it onto the stack and pay its costs, so that it will eventually resolve and have its effect."
- **CR 602.5a**: Summoning sickness restriction: "A creature's activated ability with the tap symbol or the untap symbol in its activation cost can't be activated unless the creature has been under its controller's control continuously since the beginning of their most recent turn."
- **CR 602.5b**: "An activated ability can be activated any time a player has priority, except during the casting of a spell or during the activation of an ability, unless it's a mana ability or a special action."
- **CR 602.5c**: Timing restrictions are normally sorcery-speed unless the ability grants flash or instant-speed activation.
- **Example card**: Llanowar Elves — "{T}: Add {G}."
- **Example card**: Sakura-Tribe Elder — "Sacrifice Sakura-Tribe Elder: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle."

## Acceptance Criteria
- [ ] `activate_ability(gs, perm_id, player_name)` initiates the activation process
- [ ] Cost:effect format is parsed and validated from oracle text
- [ ] Cost payment supports: mana, tapping, sacrificing, life payment, discarding, counter removal
- [ ] Summoning sickness check: creatures with {T} in cost must have been controlled since start of most recent turn
- [ ] Timing check: abilities are sorcery-speed by default; instant-speed activation requires flash or explicit grant
- [ ] Activated ability goes on the stack as a stack object (not the card itself)
- [ ] Resolving the ability applies the effect text
- [ ] Mana abilities bypass the stack and resolve immediately (CR 605)
- [ ] Loyalty abilities follow special rules (CR 606, see separate story)
- [ ] Integration test: activate Llanowar Elves, verify mana added to pool
- [ ] Integration test: summoning sickness prevents activation
- [ ] Integration test: sacrifice cost properly removes permanent
- [ ] Full regression suite passes

## Dependencies
- Story 1: Casting a Spell (similar cost payment process)
- Mana Pool (story-turn-mana-pool.md)
- Priority System (story-turn-priority-system.md)

## Priority: High
## Status: 🔄 Partial

> **Gap**: No dedicated `activate_ability()` engine function. Activated abilities handled inline via API endpoint with mana ability bypass, summoning sickness checks, and timing validation, but no separate pure-transform engine function per CR 602.

## Estimated Effort: L

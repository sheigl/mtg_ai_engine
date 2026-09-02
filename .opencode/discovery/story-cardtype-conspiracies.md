# Story: Conspiracy Rules (CR 705)

## User Story
As a game engine developer, I want Conspiracy rules to function correctly per the Comprehensive Rules, so that Conspiracy cards start the game in the command zone, modify the game's rules, and features like hidden agenda function correctly in the Conspiracy draft variant.

## Context
Conspiracies are a card type from the Conspiracy draft sets (2014, 2016). They start the game in the command zone and modify the game's rules while face down or face up. They are not cast and never enter the battlefield. The hidden agenda mechanic allows a conspiracy to secretly name a card type, and double agenda allows naming two.

### Comprehensive Rules Grounding
- **CR 705.1**: "A conspiracy is a card that starts the game in the command zone and modifies the game's rules."
- **CR 705.2**: "A conspiracy is not a permanent. It never enters the battlefield."
- **CR 705.3**: "A conspiracy starts the game face down in the command zone. It may be turned face up at any time (special action)."
- **CR 705.4**: "The effects of a conspiracy are active while it's face up in the command zone."
- **CR 705.5**: "Conspiracies are drafted during the draft portion of the game, then added to the command zone."
- **CR 705.6**: "Hidden agenda is a keyword. When you set a conspiracy in motion, you secretly choose a card name."
- **CR 705.7**: "Double agenda is a variant of hidden agenda where you choose two card names."
- **CR 705.8**: "Conspiracies can be targeted by effects that interact with the command zone."
- **Example card**: "Brago's Favor" — Conspiracy — "Hidden agenda (At the beginning of the game, secretly choose a card name. When you cast a spell with that name, draw a card.)"

## Acceptance Criteria
- [ ] Conspiracy cards start in the command zone (not in library/hand) (CR 705.1)
- [ ] Conspiracies are not permanents and never enter the battlefield (CR 705.2)
- [ ] Conspiracies start face down in the command zone (CR 705.3)
- [ ] Turning a conspiracy face up is a special action (doesn't use the stack)
- [ ] A conspiracy's effects only apply while it's face up (CR 705.4)
- [ ] Hidden agenda: at the start of the game, secretly choose a card name (CR 705.6)
- [ ] Double agenda: choose two card names instead of one (CR 705.7)
- [ ] The named card's effect (e.g., "when you cast this spell, draw a card") triggers correctly
- [ ] Conspiracies can be turned face up at any time (special action per CR 705.3)
- [ ] Conspiracies can be targeted by effects that affect the command zone (CR 705.8)
- [ ] Full regression suite passes

## Dependencies
- Story: Command Zone (CR 400.2) — command zone mechanics
- Story: Hidden Agenda — keyword mechanic for Conspiracies

## Status: ❌ Not Implemented

Not implemented: `CoreType.CONSPIRACY` enum exists at `card_type.py:9`. Zero engine implementation — no conspiracy draft rules or pre-game effects.

## Priority: Low

## Notes
- Conspiracies are fundamentally a draft variant — they are not used in constructed formats
- The conspiracy card type is primarily relevant for Conspiracy draft simulation (like story-app05-draft-sealed)
- `mtg_engine/models/card_type.py` has `CoreType.CONSPIRACY` in its enum
- Hidden agenda requires tracking a secretly-chosen card name per conspiracy
- Double agenda creates two chosen names per conspiracy
- The command zone tracking already exists in GameState (used by Commander) — conspiracies extend this
- Conspiracies typically modify the game's rules in ways that can't be disrupted (they're in the command zone)
- Cards like "Backup Plan" (an extra mulligan) are rule-modifying conspiracies with no hidden agenda
- Implementation requires game setup modifications for draft variants
- In Conspiracy draft, conspiracies are drafted separately from the main pack and added to the command zone

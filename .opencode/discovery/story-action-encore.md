# Story: Encore (CR 702.XX)

## User Story
As a game engine developer, I want the encore mechanic to function correctly per the Comprehensive Rules, so that players can exile creature cards from their graveyard and create token copies that attack each opponent and are sacrificed at end of combat.

## Context
Encore is a keyword ability from the Strixhaven: Mystical Archive supplementary products. When a player activates a creature card's encore ability from the graveyard, they exile the card and create token copies for each opponent. Those tokens gain haste, must attack the opponent they were created for, and are sacrificed at end of combat.

### Comprehensive Rules Grounding
- **CR 702.XXa**: "Encore appears on creature cards. It represents an activated ability that functions from the graveyard."
- **CR 702.XXb**: "To activate encore, the card is exiled from the graveyard. For each opponent, create a token copy of the card."
- **CR 702.XXc**: "Each token gains haste. At the beginning of the end of combat step, sacrifice the token."
- **CR 702.XXd**: "Each token attacks the opponent it was created for. If that opponent is no longer in the game, the token attacks any opponent."
- **CR 702.XXe**: "Encore can only be activated any time you could cast a sorcery."
- **Example card**: "Encore {3}{U}"
- **Example card**: Zaffai, Thunder Conductor — "Encore {4}{R}"

## Acceptance Criteria
- [ ] `encore(gs, card_in_graveyard_id, player_name)` exiles the creature card from graveyard
- [ ] For each opponent, create a token copy of the exiled creature card
- [ ] Each token gains haste
- [ ] Each token must attack the opponent it was created for
- [ ] Tokens are sacrificed at the beginning of the end of combat step
- [ ] Encore is sorcery-speed (can be activated anytime player could cast a sorcery)
- [ ] Card is exiled as part of the encore cost
- [ ] If no opponents exist (1-player game), encore cannot be activated
- [ ] Token copies have all characteristics of the original card
- [ ] "Whenever you activate an encore ability" triggers fire
- [ ] Integration test: encore a creature, create N token copies (one per opponent)
- [ ] Integration test: encore tokens have haste, attack the appropriate opponent
- [ ] Integration test: encore tokens are sacrificed at end of combat
- [ ] Integration test: can only activate encore from graveyard
- [ ] Full regression suite passes

## Dependencies
- Graveyard zone (card must be in graveyard)
- Token creation rules (story-rule-tokens.md)
- Haste (story-rule-haste.md)
- Combat phase (end of combat step — story-turn-end-of-combat.md)

## Priority: Medium
## Status: ❌ Not Implemented

> **Gap**: No encore keyword module or implementation.

## Estimated Effort: L

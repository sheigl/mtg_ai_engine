# Story: Optional Additional Costs (CR 118.10)

## User Story
As a game engine developer, I want the optional additional cost system to function correctly per the Comprehensive Rules, so that cards with optional kicker-like costs ("You may pay an additional {2} as you cast this spell") can be chosen by players during casting.

## Context
Optional additional costs are costs that a player MAY choose to pay as they cast a spell (CR 118.10). They are phrased with "You may" language — the player can decide to pay extra for an additional effect, or decline and just pay the base cost. These are a subset of additional costs (CR 118.9) with the key difference being they are OPTIONAL.

Key types of optional additional costs:
- **Keyword-based optional costs**: Kicker ("You may pay an additional {2}"), Buyback ("You may pay an additional {2}"), Escalate ("You may pay an additional {1} for each mode beyond the first")
- **Non-keyword optional costs**: Some cards have unique optional additional costs not tied to keywords

Important distinction:
- **Alternative costs** (CR 118.8): Replace the mana cost entirely — "rather than pay [card name]'s mana cost, you may..."
- **Mandatory additional costs** (CR 118.9): Must be paid — "As an additional cost to cast this spell, sacrifice a creature."
- **Optional additional costs** (CR 118.10): May be paid or skipped — "You may pay an additional {2} as you cast this spell."

### Comprehensive Rules Grounding
- **CR 118.10**: "Some cards have optional additional costs that you may choose to pay as you cast the spell."
- **CR 118.10a**: "Optional additional costs are phrased as 'You may [cost] as you cast this spell' or 'You may [cost] rather than pay [this spell's] mana cost.'"
- **CR 118.10b**: "If a card has multiple optional additional costs, you may choose to pay any combination of them."
- **CR 118.10c**: "Optional additional costs are distinct from alternative costs. An optional additional cost adds to the total cost; an alternative cost replaces the mana cost."
- **CR 118.10d**: "Some effects allow you to pay an optional additional cost without the spell having that ability. In that case, the effect specifies what the additional cost is."
- **Example card**: Rampant Growth — (no optional cost, but representative of kicker-like wording): "Kicker {2} (You may pay an additional {2} as you cast this spell.)"
- **Example card**: Molten Disaster — "Kicker {R} (You may pay an additional {R} as you cast this spell.)"

## Acceptance Criteria
- [ ] `parse_optional_cost(oracle_text: str) -> list[OptionalCost]` detects and parses optional additional cost patterns ("You may pay an additional {X} as you cast this spell")
- [ ] `get_optional_costs(gs, card_id, player_name) -> list[OptionalCost]` returns all optional costs available for a card
- [ ] Player chooses which optional costs to pay during step 601.2c of casting process
- [ ] Paying optional cost increments the total cost by the specified amount; declining does not affect casting
- [ ] Multiple optional costs on the same card can be paid in any combination (CR 118.10b)
- [ ] Optional cost payment triggers effects that look for paid optional costs (e.g., "If this spell was kicked, ...")
- [ ] AI auto-resolution: bot evaluates whether to pay optional costs based on game state, mana availability, and strategy
- [ ] Human path: queues `pending_optional_cost_choice` presenting which optional costs to pay
- [ ] Full regression passes

## Dependencies
- story-ab-spell-abilities.md (optional costs integrate into the casting process)
- story-ab-additional-costs.md (optional additional costs are a subset of additional costs)
- story-ab-alternative-costs.md (important to distinguish from alternative costs)

## Status: 🔄 Partial

Implemented per-keyword: Kicker (pending_kicker_choice), Buyback (buyback_paid), Replicate (replicate_count), Entwine (parse_entwine_cost), Dash (pending_dash_choice), Ninjutsu (pending_ninjutsu_choice), Madness (pending_madness_choice), Dredge (pending_dredge_choice), Surge (SurgeKeyword). Optional "you may" triggers (is_optional flag, /decline-trigger endpoint).

**Gap**: No unified optional-cost model. The legal actions layer does not present a unified way to select optional costs when casting. Each uses different mechanisms.

## Priority: High

## Notes
- This story covers the optional additional cost FRAMEWORK. Individual keyword-based optional costs (Kicker, Buyback, Escalate) have their own keyword story files.
- The main complexity is in the AI decision logic — when is it worth paying the extra cost? For Kicker, the answer depends on whether the kicked effect is advantageous in the current board state.
- This story is simpler (S effort) because it builds directly on the mandatory additional cost framework.
- Forge reference: `OptionalAdditionalCost` class / `getOptionalCosts()` on spells.
